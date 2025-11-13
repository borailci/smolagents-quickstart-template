"""Chroma-backed vector store for retrieval-augmented generation."""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, cast

from loguru import logger

try:
    import chromadb
    from chromadb import PersistentClient
    from chromadb import errors as chroma_errors
    from chromadb.api import ClientAPI
    from chromadb.api.models.Collection import Collection
    from chromadb.api.types import Metadata, Where
except ImportError as exc:  # pragma: no cover - enforced by runtime checks
    raise ImportError(
        "chromadb is required for the RAG vector store but is not installed. "
        "Make sure the project dependencies are synced."
    ) from exc

try:  # pragma: no cover - dependency is provided via smolagents extras
    from litellm import embedding as litellm_embedding
except ImportError as exc:
    raise ImportError(
        "litellm is required to compute embeddings. Ensure smolagents is installed with the litellm extra."
    ) from exc


_DEFAULT_EMBEDDING_MODEL = os.getenv(
    "LITELLM_EMBEDDING_MODEL_ID", "text-embedding-3-small"
)
_DEFAULT_EMBEDDING_API_KEY = os.getenv("LITELLM_EMBEDDING_API_KEY") or os.getenv(
    "LITELLM_API_KEY"
)
_CHUNK_SIZE = 900
_CHUNK_OVERLAP = 200
_MAX_FILE_SIZE_BYTES = 220_000
_ALLOWED_CODE_SUFFIXES: tuple[str, ...] = (
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
)

_PROVIDER_HINT_PREFIXES: Set[str] = {
    "google",
    "gemini",
    "vertex_ai",
    "openrouter",
    "huggingface",
    "anthropic",
    "azure",
    "cohere",
    "mistral",
}

_PROVIDER_ALIAS_MAP: Dict[str, str] = {
    "google": "gemini",
    "vertex_ai": "vertex_ai",
    "openrouter": "openrouter",
    "huggingface": "huggingface",
    "anthropic": "anthropic",
    "azure": "azure",
    "cohere": "cohere",
    "mistral": "mistral",
    "gemini": "gemini",
}


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source: str
    path: str
    line: int
    content: str


class SimpleChromaRAGStore:
    """Minimal wrapper around a Chroma persistent collection."""

    def __init__(
        self,
        *,
        codebase_root: Path,
        knowledge_base_root: Path,
        persist_directory: Path,
        collection_name: str = "tutorial_rag",
        embedding_model: str = _DEFAULT_EMBEDDING_MODEL,
        embed_batch_size: int = 8,
        request_pause_seconds: float = 0.0,
        embedding_fn: Optional[
            Callable[[Sequence[str]], Sequence[Sequence[float]]]
        ] = None,
    ) -> None:
        self.codebase_root = codebase_root
        self.knowledge_base_root = knowledge_base_root
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.embed_batch_size = max(1, embed_batch_size)
        self.request_pause_seconds = max(0.0, request_pause_seconds)
        self._embedding_fn = embedding_fn

        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client: ClientAPI = PersistentClient(path=str(self.persist_directory))
        self.collection: Optional[Collection] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ensure_index(
        self,
        *,
        include_codebase: bool = True,
        include_knowledge_base: bool = True,
        force_rebuild: bool = False,
    ) -> None:
        """Ensure a collection exists and matches the current repository state."""

        desired_fingerprint = self._compute_fingerprint(
            include_codebase=include_codebase,
            include_knowledge_base=include_knowledge_base,
        )

        existing: Optional[Collection]
        try:
            existing = self.client.get_collection(self.collection_name)
        except chroma_errors.NotFoundError:
            existing = None
        except Exception as exc:  # pragma: no cover - log and fall back to rebuild
            logger.warning(
                "Failed to load existing RAG collection '{}': {}",
                self.collection_name,
                exc,
            )
            existing = None

        if existing is not None:
            meta = existing.metadata or {}
            if force_rebuild or meta.get("fingerprint") != desired_fingerprint:
                logger.info(
                    "Rebuilding RAG vector store '{}' (fingerprint mismatch)",
                    self.collection_name,
                )
                self.client.delete_collection(self.collection_name)
                self.collection = self._build_collection(
                    include_codebase=include_codebase,
                    include_knowledge_base=include_knowledge_base,
                    fingerprint=desired_fingerprint,
                )
            else:
                self.collection = existing
        else:
            logger.info(
                "Creating new RAG vector store '{}'",
                self.collection_name,
            )
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
        if not query.strip():
            return []
        if self.collection is None:
            logger.warning(
                "RAG collection is not initialised; returning no context snippets."
            )
            return []

        where_clause: Optional[Dict[str, str]] = None
        if include_codebase and not include_knowledge_base:
            where_clause = {"source": "codebase"}
        elif include_knowledge_base and not include_codebase:
            where_clause = {"source": "knowledge_base"}
        elif not include_codebase and not include_knowledge_base:
            return []

        try:
            query_vectors = self._embed_texts([query])
            result = self.collection.query(
                query_embeddings=query_vectors,
                n_results=top_k,
                where=cast(Optional[Where], where_clause),
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - query failures are logged and suppressed
            logger.warning("RAG query failed: {}", exc)
            return []

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]

        snippets: List[Dict[str, str]] = []
        for doc, meta in zip(documents, metadatas):
            if not doc:
                continue
            source_value: Any = (
                meta.get("source", "unknown") if isinstance(meta, dict) else "unknown"
            )
            path_value: Any = meta.get("path", "") if isinstance(meta, dict) else ""
            line_value: Any = meta.get("line", 1) if isinstance(meta, dict) else 1
            source = str(source_value)
            path = str(path_value)
            line = str(line_value)
            snippets.append(
                {
                    "source": source,
                    "path": path,
                    "line": line,
                    "snippet": doc.strip(),
                }
            )
        return snippets

    # ------------------------------------------------------------------
    # Internal helpers
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
        try:
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "fingerprint": fingerprint,
                    "embedding_model": self.embedding_model,
                    "chunk_size": str(_CHUNK_SIZE),
                    "chunk_overlap": str(_CHUNK_OVERLAP),
                },
            )
        except chroma_errors.InternalError as exc:
            message = str(exc)
            if "already exists" in message.lower():
                logger.info(
                    "Existing collection '{}' detected during creation; replacing it",
                    self.collection_name,
                )
                self.client.delete_collection(self.collection_name)
                collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={
                        "fingerprint": fingerprint,
                        "embedding_model": self.embedding_model,
                        "chunk_size": str(_CHUNK_SIZE),
                        "chunk_overlap": str(_CHUNK_OVERLAP),
                    },
                )
            else:
                raise

        if not chunks:
            logger.warning(
                "No chunks collected for RAG store; the collection will remain empty."
            )
            return collection

        documents = [chunk.content for chunk in chunks]
        metadatas: List[Dict[str, str]] = [
            {
                "source": chunk.source,
                "path": chunk.path,
                "line": str(chunk.line),
            }
            for chunk in chunks
        ]
        ids = [chunk.chunk_id for chunk in chunks]

        embeddings: List[Sequence[float]] = []
        for start in range(0, len(documents), self.embed_batch_size):
            batch = documents[start : start + self.embed_batch_size]
            vectors = self._embed_texts(batch)
            embeddings.extend(vectors)
            if self.request_pause_seconds:
                time.sleep(self.request_pause_seconds)

        collection.add(
            documents=documents,
            metadatas=cast(List[Metadata], metadatas),
            ids=ids,
            embeddings=embeddings,
        )
        return collection

    def _embed_texts(self, texts: Sequence[str]) -> List[Sequence[float]]:
        if self._embedding_fn is not None:
            vectors = list(self._embedding_fn(texts))
            if len(vectors) != len(texts):
                raise ValueError(
                    "Custom embedding function returned unexpected vector count."
                )
            return vectors

        vectors: List[Sequence[float]] = []
        for text in texts:
            trimmed = text[:4000]
            embedding_params = self._build_embedding_params(trimmed)
            response = litellm_embedding(**embedding_params)
            data = response.get("data")  # type: ignore[assignment]
            if not data:
                raise RuntimeError("Embedding API returned no data.")
            embedding_vector = data[0]["embedding"]
            vectors.append(embedding_vector)
        return vectors

    def _build_embedding_params(self, text: str) -> Dict[str, Any]:
        model_id = self.embedding_model
        provider: Optional[str] = None
        normalized_model = model_id

        if "/" in model_id:
            prefix, remainder = model_id.split("/", 1)
            if prefix in _PROVIDER_HINT_PREFIXES and remainder:
                provider = _PROVIDER_ALIAS_MAP.get(prefix, prefix)
                normalized_model = remainder

        params: Dict[str, Any] = {
            "model": normalized_model,
            "input": text,
        }
        if provider:
            params["custom_llm_provider"] = provider
        if _DEFAULT_EMBEDDING_API_KEY:
            params["api_key"] = _DEFAULT_EMBEDDING_API_KEY
        return params

    def _collect_chunks(
        self,
        *,
        include_codebase: bool,
        include_knowledge_base: bool,
    ) -> List[ChunkRecord]:
        chunks: List[ChunkRecord] = []
        if include_knowledge_base and self.knowledge_base_root.exists():
            chunks.extend(
                self._chunk_directory(
                    root=self.knowledge_base_root,
                    source="knowledge_base",
                    pattern="*.md",
                )
            )
        if include_codebase and self.codebase_root.exists():
            chunks.extend(
                self._chunk_directory(root=self.codebase_root, source="codebase")
            )
        return chunks

    def _chunk_directory(
        self,
        *,
        root: Path,
        source: str,
        pattern: Optional[str] = None,
    ) -> List[ChunkRecord]:
        entries: Iterable[Path]
        if pattern:
            entries = root.rglob(pattern)
        else:
            entries = root.rglob("*")

        chunks: List[ChunkRecord] = []
        for path in sorted(entries):
            if path.is_dir() or path.name.startswith("."):
                continue
            if source == "codebase":
                if path.suffix and path.suffix.lower() not in _ALLOWED_CODE_SUFFIXES:
                    continue
            try:
                if path.stat().st_size > _MAX_FILE_SIZE_BYTES:
                    continue
            except FileNotFoundError:
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            relative_path = str(path.relative_to(root))
            chunks.extend(
                self._chunk_file(
                    content=content, source=source, relative_path=relative_path
                )
            )
        return chunks

    def _chunk_file(
        self,
        *,
        content: str,
        source: str,
        relative_path: str,
    ) -> List[ChunkRecord]:
        records: List[ChunkRecord] = []
        cleaned = content.strip()
        if not cleaned:
            return records

        start = 0
        length = len(cleaned)
        while start < length:
            end = min(length, start + _CHUNK_SIZE)
            chunk = cleaned[start:end].strip()
            if chunk:
                line_number = cleaned.count("\n", 0, start) + 1
                chunk_id = self._build_chunk_id(
                    source, relative_path, line_number, chunk
                )
                records.append(
                    ChunkRecord(
                        chunk_id=chunk_id,
                        source=source,
                        path=relative_path,
                        line=line_number,
                        content=chunk,
                    )
                )
            if end == length:
                break
            start = max(end - _CHUNK_OVERLAP, start + 1)
        return records

    @staticmethod
    def _build_chunk_id(source: str, path: str, line: int, chunk: str) -> str:
        digest = hashlib.sha256(
            f"{source}:{path}:{line}:{chunk[:80]}".encode("utf-8")
        ).hexdigest()
        return f"{source}-{digest}"

    def _compute_fingerprint(
        self,
        *,
        include_codebase: bool,
        include_knowledge_base: bool,
    ) -> str:
        hasher = hashlib.sha256()
        hasher.update(self.embedding_model.encode("utf-8"))
        hasher.update(str(_CHUNK_SIZE).encode("utf-8"))
        hasher.update(str(_CHUNK_OVERLAP).encode("utf-8"))

        def _update_for_directory(root: Path) -> None:
            for path in sorted(root.rglob("*")):
                if path.is_dir() or path.name.startswith("."):
                    continue
                try:
                    stat = path.stat()
                except FileNotFoundError:
                    continue
                hasher.update(str(path.relative_to(root)).encode("utf-8"))
                hasher.update(str(int(stat.st_mtime)).encode("utf-8"))
                hasher.update(str(stat.st_size).encode("utf-8"))

        if include_knowledge_base and self.knowledge_base_root.exists():
            _update_for_directory(self.knowledge_base_root)
        if include_codebase and self.codebase_root.exists():
            _update_for_directory(self.codebase_root)

        return hasher.hexdigest()


__all__ = ["SimpleChromaRAGStore"]
