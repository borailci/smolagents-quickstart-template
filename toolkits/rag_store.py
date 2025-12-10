"""Chroma-backed vector store for retrieval-augmented generation."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Set, cast

from loguru import logger

try:
    import chromadb
    from chromadb import PersistentClient
    from chromadb import errors as chroma_errors
    from chromadb.api import ClientAPI
    from chromadb.api.models.Collection import Collection
    from chromadb.api.types import Metadata, Where
except ImportError as exc:
    raise ImportError(
        "chromadb is required. Install it or check your dependencies."
    ) from exc

try:
    from litellm import RateLimitError
    from litellm import embedding as litellm_embedding
    # Import google specific exception if possible, or rely on generic Exception for now
    # from google.api_core.exceptions import ResourceExhausted
except ImportError as exc:
    raise ImportError(
        "litellm is required for embeddings. Install it via `pip install litellm`."
    ) from exc

# --- NEW: Import centralized config ---
from config import settings
from utils.constants import IGNORED_DIRS, ALLOWED_SUFFIXES, MAX_FILE_SIZE_BYTES

# Text Splitting Config
_CHUNK_SIZE = 1000  # Characters
_CHUNK_OVERLAP = 200


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source: str
    path: str
    line: int
    content: str


class SimpleChromaRAGStore:
    """Wrapper around ChromaDB with efficient batching and smart filtering."""

    def __init__(
        self,
        *,
        codebase_root: Path,
        knowledge_base_root: Path,
        persist_directory: Path,
        collection_name: str = "tutorial_rag",
        embedding_model: str = settings.EMBEDDING_MODEL_ID,
        embed_batch_size: int = settings.RAG_EMBED_BATCH_SIZE,
        request_pause_seconds: float = settings.RAG_EMBED_REQUEST_PAUSE_SECONDS,
        embed_max_retries: int | None = None, # Deprecated/handled by tenacity config, but kept for init sig compat
        embed_retry_backoff_seconds: float | None = None,
        embedding_fn: Optional[
            Callable[[Sequence[str]], Sequence[Sequence[float]]]
        ] = None,
    ) -> None:
        self.codebase_root = codebase_root
        self.knowledge_base_root = knowledge_base_root
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # Enforce minimums
        self.embed_batch_size = max(1, embed_batch_size)
        self.request_pause_seconds = max(0.0, request_pause_seconds)
        self._embedding_fn = embedding_fn

        self.persist_directory.mkdir(parents=True, exist_ok=True)
        # Using the standard client interface
        self.client: ClientAPI = PersistentClient(path=str(self.persist_directory))
        self.collection: Optional[Collection] = None

    def query(
        self,
        query: str,
        top_k: int = 5,
        include_codebase: bool = True,
        include_knowledge_base: bool = True,
    ) -> List[str]:
        """Semantically searches the knowledge base."""
        if not self.collection:
            logger.warning("RAG query called but collection is not initialized.")
            return []

        # 1. Embed query
        query_embeddings = self._embed_texts([query])
        if not query_embeddings:
            return []

        # 2. Build filters
        sources = []
        if include_codebase:
            sources.append("codebase")
        if include_knowledge_base:
            sources.append("knowledge_base")
        
        if not sources:
            return []

        where_filter: Where | None = None
        if len(sources) == 1:
            where_filter = {"source": sources[0]}
        else:
            where_filter = {"source": {"$in": sources}}

        # 3. Query Chroma
        try:
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error(f"Chroma query failed: {exc}")
            return []

        # 4. Format results
        output = []
        if results["documents"] and results["metadatas"]:
            # Chroma returns list of lists (one per query)
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            
            for doc, meta in zip(docs, metas):
                path = meta.get("path", "unknown")
                line = meta.get("line", "?")
                source_label = meta.get("source", "unknown")
                output.append(f"[{source_label.upper()}] {path}:{line}\n{doc}")

        return output

    def ensure_index(
        self,
        *,
        include_codebase: bool = True,
        include_knowledge_base: bool = True,
        force_rebuild: bool = False,
    ) -> None:
        """Ensure a collection exists and matches the current repository state using incremental updates."""
        
        # 1. Compute fingerprint (still useful for high-level check, though strictly we could skip)
        desired_fingerprint = self._compute_fingerprint(
            include_codebase=include_codebase,
            include_knowledge_base=include_knowledge_base,
        )

        existing: Optional[Collection] = None
        try:
            existing = self.client.get_collection(self.collection_name)
            self.collection = existing
            logger.info("Successfully loaded existing collection.")
        except chroma_errors.NotFoundError:
            logger.info("Collection matched by name not found.")
        except Exception as exc:
            logger.warning(f"Could not load existing collection: {exc}")

        logger.info(f"Rebuild check: existing={bool(existing)}, force={force_rebuild}")

        # 2. If nothing exists, build fresh
        if not existing or force_rebuild:
            if existing:
                self.client.delete_collection(self.collection_name)
            
            logger.info(f"Building RAG index '{self.collection_name}' from scratch...")
            self.collection = self._build_collection(
                include_codebase=include_codebase,
                include_knowledge_base=include_knowledge_base,
                fingerprint=desired_fingerprint,
            )
            return

        # 3. Incremental Update
        meta = existing.metadata or {}
        stored_fingerprint = meta.get("fingerprint")
        
        if stored_fingerprint == desired_fingerprint:
            logger.info(f"RAG store '{self.collection_name}' is up to date (fingerprint match).")
            return

        logger.info(
             f"Fingerprint mismatch ({stored_fingerprint} vs {desired_fingerprint}). Performing incremental update..."
        )
        self._update_collection(
            include_codebase=include_codebase,
            include_knowledge_base=include_knowledge_base,
            fingerprint=desired_fingerprint,
        )

    def _update_collection(
        self,
        *,
        include_codebase: bool,
        include_knowledge_base: bool,
        fingerprint: str,
    ) -> None:
        """Incrementally updates the collection by diffing chunk IDs."""
        if not self.collection:
            return

        # A. Collect all current chunks from files
        current_chunks = self._collect_chunks(
            include_codebase=include_codebase,
            include_knowledge_base=include_knowledge_base,
        )
        current_ids = {c.chunk_id for c in current_chunks}
        chunk_map = {c.chunk_id: c for c in current_chunks}

        # B. Get all existing IDs from Chroma
        try:
            # We only need IDs to diff
            existing_data = self.collection.get(include=[])
            existing_ids = set(existing_data.get("ids", []))
        except Exception as exc:
            logger.error(f"Failed to fetch existing IDs for diffing: {exc}")
            raise

        # C. Calculate Diff
        to_add_ids = current_ids - existing_ids
        to_remove_ids = existing_ids - current_ids

        logger.info(f"Incremental Update: Adding {len(to_add_ids)}, Removing {len(to_remove_ids)} chunks.")

        # D. Remove stale chunks
        if to_remove_ids:
            try:
                self.collection.delete(ids=list(to_remove_ids))
                logger.info(f"Removed {len(to_remove_ids)} stale chunks.")
            except Exception as exc:
                logger.error(f"Failed to delete stale chunks: {exc}")

        # E. Add new chunks (in batches)
        if to_add_ids:
            chunks_to_add = [chunk_map[cid] for cid in to_add_ids]
            self._batch_add_chunks(chunks_to_add)

        # F. Update Metadata (Fingerprint)
        try:
            self.collection.modify(metadata={
                "fingerprint": fingerprint,
                "embedding_model": self.embedding_model,
            })
        except Exception as exc:
            logger.warning(f"Failed to update collection metadata: {exc}")

    def _build_collection(
        self,
        *,
        include_codebase: bool,
        include_knowledge_base: bool,
        fingerprint: str,
    ) -> Collection:
        chunks = self._collect_chunks(
            include_codebase=include_codebase,
            include_knowledge_base=include_knowledge_base,
        )

        collection = self.client.create_collection(
            name=self.collection_name,
            metadata={
                "fingerprint": "partial",  # Mark as partial until finished to allow resume
                "embedding_model": self.embedding_model,
            },
        )

        if chunks:
            self.collection = collection  # temporary set for helper to work if needed
            self._batch_add_chunks(chunks, collection)
        
        # Mark as complete
        try:
            collection.modify(metadata={
                "fingerprint": fingerprint,
                "embedding_model": self.embedding_model,
            })
        except Exception as exc:
            logger.warning(f"Failed to finalize collection metadata: {exc}")
        
        return collection

    def _batch_add_chunks(self, chunks: List[ChunkRecord], collection: Optional[Collection] = None):
        """Helper to batch embed and add chunks to a collection."""
        target_col = collection or self.collection
        if not target_col:
            raise ValueError("No collection available for adding chunks.")

        total_chunks = len(chunks)
        # Use config batch size (likely 10)
        batch_size = self.embed_batch_size
        logger.info(
            f"Embedding {total_chunks} chunks in batches of {batch_size}..."
        )

        for start in range(0, total_chunks, batch_size):
            end = start + batch_size
            batch = chunks[start:end]

            texts = [c.content for c in batch]
            ids = [c.chunk_id for c in batch]
            metadatas = [
                {"source": c.source, "path": c.path, "line": str(c.line)} for c in batch
            ]

            try:
                vectors = self._embed_texts(texts)
                
                target_col.add(
                    documents=texts,
                    metadatas=cast(List[Metadata], metadatas),
                    ids=ids,
                    embeddings=vectors,
                )
            except Exception as exc:
                logger.error(f"Failed to embed batch starting at index {start}: {exc}")

            # Always throttle to respect rate limits
            if self.request_pause_seconds > 0:
                logger.debug(f"Throttling batch for {self.request_pause_seconds}s...")
                time.sleep(self.request_pause_seconds)

    def _embed_texts(self, texts: Sequence[str]) -> List[Sequence[float]]:
        """Computes embeddings for a batch of texts with robust retries."""
        if self._embedding_fn:
            return list(self._embedding_fn(texts))

        # Manual retry loop with fixed 5s sleep for rate limits
        max_retries = settings.RAG_EMBED_MAX_RETRIES
        attempt = 0
        
        while True:
            attempt += 1
            try:
                response = litellm_embedding(
                    model=self.embedding_model,
                    input=texts,
                    api_key=settings.LITELLM_API_KEY,
                )
                data = response.get("data", [])
                data.sort(key=lambda x: x["index"])
                return [item["embedding"] for item in data]
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = "rate" in error_str or "429" in error_str or "exhausted" in error_str
                
                if is_rate_limit:
                    logger.warning(f"Rate limit hit during embedding (attempt {attempt}). Sleeping 5.0s...")
                    time.sleep(5.0)
                    # For rate limits, we often want infinite retries or very high limits.
                    # If using max_retries, ensure it's high enough. 
                    # User requested "Use this rate limit... fixed sleep (5.0s)".
                    # We will continue indefinitely for rate limits if that's the implication, 
                    # but typically we still respect a high max count or just loop.
                    # Given "manual loop but with fixed sleep", let's loop forever on rate limit 
                    # or at least respect the configured max retries but strictly use 5s.
                    if attempt >= max_retries:
                         logger.error(f"Max retries ({max_retries}) exceeded for rate limit.")
                         raise
                    continue
                else:
                    # Non-rate limit error
                    logger.error(f"Embedding failed: {e}")
                    raise

    def _collect_chunks(
        self, *, include_codebase: bool, include_knowledge_base: bool
    ) -> List[ChunkRecord]:
        chunks: List[ChunkRecord] = []

        if include_knowledge_base and self.knowledge_base_root.exists():
            chunks.extend(
                self._process_directory(self.knowledge_base_root, "knowledge_base")
            )

        if include_codebase and self.codebase_root.exists():
            chunks.extend(self._process_directory(self.codebase_root, "codebase"))

        return chunks

    def _process_directory(self, root: Path, source: str) -> List[ChunkRecord]:
        chunks: List[ChunkRecord] = []

        # Use rglob but filter manually to avoid traversing .git or node_modules
        for path in sorted(root.rglob("*")):
            if not self._is_valid_file(path, root):
                continue

            try:
                content = path.read_text(encoding="utf-8")
                chunks.extend(
                    self._chunk_content_by_lines(
                        content, source, str(path.relative_to(root))
                    )
                )
            except (UnicodeDecodeError, OSError):
                continue

        return chunks

    def _is_valid_file(self, path: Path, root: Path) -> bool:
        """Centralized logic for file validity (used by collector AND fingerprinter)."""
        # Check if directory is ignored
        if any(part in IGNORED_DIRS for part in path.parts):
            return False

        # Must be a file
        if not path.is_file():
            return False

        # Hidden files
        if path.name.startswith("."):
            return False

        # Size limit
        try:
            if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                return False
        except FileNotFoundError:
            return False

        # Suffix check
        return path.suffix.lower() in ALLOWED_SUFFIXES

    def _chunk_content_by_lines(
        self, content: str, source: str, relative_path: str
    ) -> List[ChunkRecord]:
        """Splits text respecting newlines to avoid breaking code syntax."""
        lines = content.splitlines()
        records: List[ChunkRecord] = []

        current_chunk: List[str] = []
        current_length = 0
        start_line = 1
        current_line_idx = 0

        while current_line_idx < len(lines):
            line = lines[current_line_idx]
            line_len = len(line) + 1  # +1 for newline

            # If adding this line exceeds chunk size and we have content, save current chunk
            if current_length + line_len > _CHUNK_SIZE and current_chunk:
                chunk_text = "\\n".join(current_chunk)
                records.append(
                    ChunkRecord(
                        chunk_id=self._build_chunk_id(
                            source, relative_path, start_line, chunk_text
                        ),
                        source=source,
                        path=relative_path,
                        line=start_line,
                        content=chunk_text,
                    )
                )

                # Overlap logic: keep last N lines that fit within overlap budget
                overlap_buffer = []
                overlap_len = 0
                for prev_line in reversed(current_chunk):
                    if overlap_len + len(prev_line) > _CHUNK_OVERLAP:
                        break
                    overlap_buffer.insert(0, prev_line)
                    overlap_len += len(prev_line) + 1

                current_chunk = overlap_buffer
                current_length = overlap_len
                # Approximate start line for next chunk (not perfect but sufficient)
                start_line = (current_line_idx + 1) - len(current_chunk)

            current_chunk.append(line)
            current_length += line_len
            current_line_idx += 1

        # Add remaining
        if current_chunk:
            chunk_text = "\\n".join(current_chunk)
            records.append(
                ChunkRecord(
                    chunk_id=self._build_chunk_id(
                        source, relative_path, start_line, chunk_text
                    ),
                    source=source,
                    path=relative_path,
                    line=start_line,
                    content=chunk_text,
                )
            )

        return records

    @staticmethod
    def _build_chunk_id(source: str, path: str, line: int, chunk: str) -> str:
        # Hashing content ensures identical chunks don't duplicate
        digest = hashlib.sha256(
            f"{source}:{path}:{line}:{chunk}".encode("utf-8")
        ).hexdigest()[
            :16
        ]  # Shorten hash for readability
        return f"{source}-{digest}"

    def _compute_fingerprint(
        self, *, include_codebase: bool, include_knowledge_base: bool
    ) -> str:
        """Computes a hash of the file states to detect changes."""
        hasher = hashlib.sha256()
        hasher.update(self.embedding_model.encode("utf-8"))
        hasher.update(str(_CHUNK_SIZE).encode("utf-8"))

        roots_to_check = []
        if include_knowledge_base:
            roots_to_check.append(self.knowledge_base_root)
        if include_codebase:
            roots_to_check.append(self.codebase_root)

        for root in roots_to_check:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                # STRICTLY use the same validity check as collection
                if not self._is_valid_file(path, root):
                    continue

                stat = path.stat()
                hasher.update(str(path.relative_to(root)).encode("utf-8"))
                hasher.update(str(int(stat.st_mtime)).encode("utf-8"))
                hasher.update(str(stat.st_size).encode("utf-8"))

        return hasher.hexdigest()
