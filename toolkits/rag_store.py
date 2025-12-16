"""Local embedding RAG store using ChromaDB and sentence-transformers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, cast

from loguru import logger

try:
    import chromadb
    from chromadb import PersistentClient
    from chromadb import errors as chroma_errors
    from chromadb.api import ClientAPI
    from chromadb.api.models.Collection import Collection
    from chromadb.api.types import Metadata, Where
except ImportError as exc:
    raise ImportError("chromadb is required. Install via `uv add chromadb`.") from exc

from utils.constants import IGNORED_DIRS, ALLOWED_SUFFIXES, MAX_FILE_SIZE_BYTES, IGNORED_FILES, BLOCKED_EXTENSIONS


__all__ = ["SimpleChromaRAGStore", "ChunkRecord"]

# Configuration
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200
EMBED_BATCH_SIZE = 100


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source: str
    path: str
    line: int
    content: str


class SimpleChromaRAGStore:
    """ChromaDB-backed vector store with local sentence-transformers embedding."""

    def __init__(
        self,
        *,
        codebase_root: Path,
        knowledge_base_root: Path,
        persist_directory: Path,
        collection_name: str = "tutorial_rag",
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        embed_batch_size: int = EMBED_BATCH_SIZE,
        embedding_fn: Optional[Callable[[Sequence[str]], Sequence[Sequence[float]]]] = None,
    ) -> None:
        self.codebase_root = codebase_root
        self.knowledge_base_root = knowledge_base_root
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.embed_batch_size = max(1, embed_batch_size)
        self._embedding_fn = embedding_fn

        # Load local embedding model
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {embedding_model}...")
            self.local_model = SentenceTransformer(embedding_model)
            logger.info(f"Model loaded on device: {self.local_model.device}")
        except ImportError:
            raise ImportError("sentence-transformers required. Install via `uv add sentence-transformers`.")

        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client: ClientAPI = PersistentClient(path=str(self.persist_directory))
        self.collection: Optional[Collection] = None

    def ensure_index(
        self,
        *,
        include_codebase: bool = True,
        include_knowledge_base: bool = True,
        force_rebuild: bool = False,
    ) -> None:
        """Ensure a collection exists and matches the current repository state."""

        # 1. Compute fingerprint of current files
        desired_fingerprint = self._compute_fingerprint(
            include_codebase=include_codebase,
            include_knowledge_base=include_knowledge_base,
        )

        existing: Optional[Collection] = None
        try:
            existing = self.client.get_collection(self.collection_name)
        except chroma_errors.NotFoundError:
            pass
        except Exception as exc:
            logger.warning(f"Could not load existing collection: {exc}")

        # 2. Check if rebuild is needed
        should_rebuild = force_rebuild
        if existing:
            meta = existing.metadata or {}
            stored_fingerprint = meta.get("fingerprint")
            if stored_fingerprint != desired_fingerprint:
                logger.info(
                    f"Fingerprint mismatch ({stored_fingerprint} vs {desired_fingerprint}). Rebuilding..."
                )
                should_rebuild = True
            else:
                logger.info(f"RAG store '{self.collection_name}' is up to date.")
                self.collection = existing

        # 3. Rebuild or Create
        if should_rebuild or existing is None:
            if existing:
                self.client.delete_collection(self.collection_name)

            logger.info(f"Building RAG index '{self.collection_name}'...")
            self.collection = self._build_collection(
                include_codebase=include_codebase,
                include_knowledge_base=include_knowledge_base,
                fingerprint=desired_fingerprint,
            )

    def query(
        self,
        query: str,
        *,
        top_k: int = 5,
        include_codebase: bool = True,
        include_knowledge_base: bool = True,
    ) -> List[Dict[str, str]]:
        if not query.strip() or not self.collection:
            return []

        # Construct Where clause
        where_clause: Optional[Dict[str, str]] = None
        if include_codebase and not include_knowledge_base:
            where_clause = {"source": "codebase"}
        elif include_knowledge_base and not include_codebase:
            where_clause = {"source": "knowledge_base"}
        elif not include_codebase and not include_knowledge_base:
            return []

        try:
            # Embed query (batch of 1)
            query_vectors = self._embed_texts([query])

            result = self.collection.query(
                query_embeddings=query_vectors,
                n_results=top_k,
                where=cast(Optional[Where], where_clause),
            )
        except Exception as exc:
            logger.warning(f"RAG query failed: {exc}")
            return []

        # Parse results
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]

        snippets: List[Dict[str, str]] = []
        for doc, meta in zip(documents, metadatas):
            if not doc:
                continue

            # Safe access to metadata
            meta_dict = meta if isinstance(meta, dict) else {}

            snippets.append(
                {
                    "source": str(meta_dict.get("source", "unknown")),
                    "path": str(meta_dict.get("path", "")),
                    "line": str(meta_dict.get("line", 1)),
                    "snippet": doc.strip(),
                }
            )

        return snippets

    # ------------------------------------------------------------------
    # Internal Builders
    # ------------------------------------------------------------------

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
                "fingerprint": fingerprint,
                "embedding_model": self.embedding_model_name,
            },
        )

        if not chunks:
            return collection

        # Batch Processing
        total_chunks = len(chunks)
        # For local model, we can probably do larger batches, but 100 is safe default
        logger.info(
            f"Embedding {total_chunks} chunks in batches of {self.embed_batch_size}..."
        )

        for start in range(0, total_chunks, self.embed_batch_size):
            end = start + self.embed_batch_size
            batch = chunks[start:end]

            texts = [c.content for c in batch]
            ids = [c.chunk_id for c in batch]
            metadatas = [
                {"source": c.source, "path": c.path, "line": str(c.line)} for c in batch
            ]

            try:
                vectors = self._embed_texts(texts)

                collection.add(
                    documents=texts,
                    metadatas=cast(List[Metadata], metadatas),
                    ids=ids,
                    embeddings=vectors,
                )
            except Exception as exc:
                logger.error(f"Failed to embed batch starting at index {start}: {exc}")

            # No sleep for local model

        return collection

    def _embed_texts(self, texts: Sequence[str]) -> List[Sequence[float]]:
        """Computes embeddings for a batch of texts using local model."""
        if self._embedding_fn:
            return list(self._embedding_fn(texts))
        
        # Local inference
        embeddings = self.local_model.encode(texts)
        # Convert numpy array to list of lists
        return embeddings.tolist()

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
            
        # Use centralized constants instead of hardcoded values
        if path.suffix.lower() in BLOCKED_EXTENSIONS:
            return False
            
        # Specific files to ignore (except README.md which has high value)
        if path.name in IGNORED_FILES and path.name != "README.md":
            return False
            
        # Ignored directories check (uses centralized IGNORED_DIRS)
        if any(part in IGNORED_DIRS for part in path.parts):
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
            if current_length + line_len > CHUNK_SIZE and current_chunk:
                chunk_text = "\n".join(current_chunk)
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
                    if overlap_len + len(prev_line) > CHUNK_OVERLAP:
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
            chunk_text = "\n".join(current_chunk)
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
        hasher.update(self.embedding_model_name.encode("utf-8"))
        hasher.update(str(CHUNK_SIZE).encode("utf-8"))

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

