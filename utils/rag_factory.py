"""Factory for RAG stores with caching support."""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger

from toolkits.rag_store import SimpleChromaRAGStore
from utils.path_utils import ensure_directory


@dataclass
class RAGStores:
    """Container for active RAG stores."""
    codebase: Optional[SimpleChromaRAGStore] = None
    knowledge_base: Optional[SimpleChromaRAGStore] = None

    def query(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """Query both stores and merge results."""
        results = []

        if self.codebase:
            try:
                results.extend(self.codebase.query(
                    query, top_k=limit,
                    include_codebase=True, include_knowledge_base=False
                ))
            except Exception as e:
                logger.error(f"Codebase RAG query failed: {e}")

        if self.knowledge_base:
            try:
                inc_cb = self.codebase is None  # Include codebase if no separate store
                results.extend(self.knowledge_base.query(
                    query, top_k=limit,
                    include_codebase=inc_cb, include_knowledge_base=True
                ))
            except Exception as e:
                logger.error(f"KB RAG query failed: {e}")

        return results[:limit]


def get_rag_stores(
    codebase_root: Path,
    knowledge_base_root: Path,
    output_path: Path,
    enable_rag: bool = False,
    force_rebuild: bool = False,
    rag_codebase_cache_path: Path | str | None = None,
) -> RAGStores:
    """Initialize RAG stores.

    Args:
        codebase_root: Path to codebase.
        knowledge_base_root: Path to KB markdown files.
        output_path: RAG persistence directory.
        enable_rag: Enable RAG features.
        force_rebuild: Force index rebuild.
        rag_codebase_cache_path: Pre-computed cache path (optional).
    """
    stores = RAGStores()
    
    if not enable_rag:
        return stores

    # 1. Setup KB Store (Always local and specific to this run)
    rag_storage_root_kb = ensure_directory(
        (output_path.parent if output_path.parent != output_path else output_path)
        / "rag_store_kb"
    )
    
    try:
        stores.knowledge_base = SimpleChromaRAGStore(
            codebase_root=codebase_root,
            knowledge_base_root=knowledge_base_root,
            persist_directory=rag_storage_root_kb,
            collection_name="kb_rag"
        )
        stores.knowledge_base.ensure_index(
            include_codebase=False,
            include_knowledge_base=True,
            force_rebuild=force_rebuild,
        )
    except Exception as exc:
        logger.warning("Failed to initialize KB RAG store: {}", exc)
        stores.knowledge_base = None

    # 2. Setup Codebase Store (Either cached or local-combined fallback)
    # Check env var as fallback to argument
    cache_path = rag_codebase_cache_path or os.environ.get("RAG_CODEBASE_CACHE_DIR")
    
    if cache_path and Path(cache_path).exists():
        # Use shared cache for codebase
        logger.info(f"Using pre-computed Codebase RAG cache at {cache_path}")
        try:
            stores.codebase = SimpleChromaRAGStore(
                codebase_root=codebase_root,
                knowledge_base_root=knowledge_base_root,
                persist_directory=Path(cache_path),
                collection_name="codebase_rag_cache" # Must match what generated it
            )
            # Read-only verification
            stores.codebase.ensure_index(
                include_codebase=True,
                include_knowledge_base=False,
                force_rebuild=False 
            )
        except Exception as exc:
            logger.warning("Failed to load Codebase RAG cache: {}", exc)
            stores.codebase = None
    else:
        # No cache available.
        # Fallback: We configure the KB store to ALSO include the codebase.
        # This keeps things simple (one store) when no cache is present.
        if stores.knowledge_base:
             try:
                 stores.knowledge_base.ensure_index(
                     include_codebase=True,
                     include_knowledge_base=True,
                     force_rebuild=force_rebuild
                 )
             except Exception as exc:
                logger.warning("Failed to extend KB RAG store to include codebase: {}", exc)

    return stores
