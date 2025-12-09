"""Tools for tutorial generation leveraging the knowledge base, codebase access, and optional RAG."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

from loguru import logger
from smolagents import Tool, tool

from toolkits.baseline_toolkit import build_baseline_tools
from toolkits.rag_store import SimpleChromaRAGStore
from utils.path_utils import ensure_directory, resolve_within_root
from utils.constants import IGNORED_DIRS

__all__ = ["build_tutorial_tools"]

_MAX_READ_LINES = 500  # Limit KB reads to protect context
_DEFAULT_RAG_MAX_SNIPPETS = 5


def _read_text_file_truncated(path: Path) -> str:
    """Reads file content with line limits."""

    try:
        lines = []
        with path.open("r", encoding="utf-8") as handle:
            for i, line in enumerate(handle):
                if i >= _MAX_READ_LINES:
                    lines.append(f"\n... [Truncated after {_MAX_READ_LINES} lines] ...")
                    break
                lines.append(line)
        return "".join(lines)
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"File '{path.name}' is binary or not UTF-8 decodable."
        ) from exc


def _write_text_file(path: Path, content: str, append: bool = False) -> None:
    ensure_directory(path.parent)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as handle:
        handle.write(content)


def build_tutorial_tools(
    *,
    codebase_root: str,
    knowledge_base_root: str,
    tutorial_output_root: str,
    enable_rag: bool = False,
    rag_max_snippets: int = _DEFAULT_RAG_MAX_SNIPPETS,
    rag_force_rebuild: bool = False,
    rag_codebase_cache_path: str | None = None,
    usage_callback: Callable[[str, str | None], None] | None = None,
) -> List[Tool]:
    codebase_path = Path(codebase_root).expanduser().resolve()
    kb_path = Path(knowledge_base_root).expanduser().resolve()
    output_path = ensure_directory(tutorial_output_root)

    def _record_tool_usage(tool_name: str, content: str | None = None) -> None:
        if usage_callback:
            try:
                usage_callback(tool_name, content)
            except Exception:
                pass

    base_tools = build_baseline_tools(
        codebase_root=str(codebase_path),
        tutorial_output_root=str(output_path),
        knowledge_base_root=str(kb_path),
        rag_force_rebuild=rag_force_rebuild,
        usage_callback=usage_callback,
    )

    rag_store_kb: Optional[SimpleChromaRAGStore] = None
    rag_store_codebase: Optional[SimpleChromaRAGStore] = None

    if enable_rag:
        # 1. Setup KB Store (Always local and specific to this run)
        rag_storage_root_kb = ensure_directory(
            (output_path.parent if output_path.parent != output_path else output_path)
            / "rag_store_kb"
        )
        try:
            rag_store_kb = SimpleChromaRAGStore(
                codebase_root=codebase_path,
                knowledge_base_root=kb_path,
                persist_directory=rag_storage_root_kb,
                collection_name="kb_rag"
            )
            rag_store_kb.ensure_index(
                include_codebase=False,
                include_knowledge_base=True,
                force_rebuild=rag_force_rebuild,
            )
        except Exception as exc:
            logger.warning("Failed to initialize KB RAG store: {}", exc)
            rag_store_kb = None

        # 2. Setup Codebase Store (Either cached or local-combined)
        if rag_codebase_cache_path and Path(rag_codebase_cache_path).exists():
            # Use shared cache for codebase
            logger.info(f"Using pre-computed Codebase RAG cache at {rag_codebase_cache_path}")
            try:
                rag_store_codebase = SimpleChromaRAGStore(
                    codebase_root=codebase_path,
                    knowledge_base_root=kb_path,
                    persist_directory=Path(rag_codebase_cache_path),
                    collection_name="codebase_rag_cache" # Must match what generated it
                )
                # We assume the cache is ready, but calling ensure_index(include_kb=False)
                # verifies the codebase fingerprint matches.
                rag_store_codebase.ensure_index(
                    include_codebase=True,
                    include_knowledge_base=False,
                    force_rebuild=False # Never rebuild the cache here
                )
            except Exception as exc:
                logger.warning("Failed to load Codebase RAG cache: {}", exc)
                rag_store_codebase = None
        else:
            # Traditional behavior: Build codebase index locally
            # We reuse the KB store directory for efficiency if we are building scratch?
            # actually better to keep separate if we want to mimic the architecture,
            # but for backward compatibility/simplicity, if no cache, we can just Put
            # codebase into the SAME store as KB if we wanted.
            # BUT, to keep logic consistent, let's just make a second store or
            # use one store for BOTH if no cache is present.

            # Revert to single store mode if no cache provided
            # This means rag_store_kb above was wasteful if we are going to do a combined one?
            # actually, let's keep it simple:
            # If no cache: use rag_store_kb as the MAIN store for BOTH.
            if rag_store_kb:
                 # Re-run ensure_index to ALSO include codebase
                 rag_store_kb.ensure_index(
                     include_codebase=True,
                     include_knowledge_base=True,
                     force_rebuild=rag_force_rebuild
                 )
                 # rag_store_codebase remains None, we use rag_store_kb for everything

    max_snippets = max(1, rag_max_snippets)

    def _is_safe_entry(entry: Path) -> bool:
        return not entry.name.startswith(".") and entry.name not in IGNORED_DIRS

    @tool
    def list_knowledge_base(dir_path: str = ".") -> List[str]:
        """List markdown files in the knowledge base.

        Args:
            dir_path: Relative directory path within the knowledge base to inspect.
        """
        resolved = resolve_within_root(kb_path, dir_path)
        if not resolved.is_dir():
            return []
        entries = sorted(
            entry.name for entry in resolved.iterdir() if _is_safe_entry(entry)
        )
        _record_tool_usage("list_knowledge_base", "\n".join(entries))
        return entries

    @tool
    def read_knowledge_base_file(file_path: str) -> str:
        """Read a markdown file from the knowledge base.

        Args:
            file_path: Relative path to the markdown file inside the knowledge base directory.
        """
        resolved = resolve_within_root(kb_path, file_path)
        output = _read_text_file_truncated(resolved)
        _record_tool_usage("read_knowledge_base_file", output)
        return output

    @tool
    def write_tutorial_file(file_path: str, content: str, append: bool = False) -> str:
        """Write tutorial content to the tutorials output directory.

        Args:
            file_path: Relative path for the tutorial markdown file to create.
            content: Markdown content to write into the file.
            append: When True, append instead of overwriting.
        """
        resolved = resolve_within_root(output_path, file_path)
        _write_text_file(resolved, content, append=append)
        _record_tool_usage("write_tutorial_file", None)
        return str(resolved)

    tools: List[Tool] = list(base_tools) + [
        list_knowledge_base,
        read_knowledge_base_file,
        write_tutorial_file,
    ]

    if enable_rag:

        @tool
        def retrieve_relevant_context(
            query: str,
            max_snippets: int = max_snippets,
        ) -> List[Dict[str, str]]:
            """Retrieve semantic snippets (codebase or KB) via RAG.

            Args:
                query: Free-text query to match against files.
                max_snippets: Maximum number of snippets to return in total.
            """
            normalized_query = query.strip()
            if not normalized_query:
                return []

            limit = max(1, max_snippets)
            results = []

            # 1. Query Codebase Store (from Cache or if separate)
            if rag_store_codebase:
                try:
                    results.extend(rag_store_codebase.query(
                         normalized_query,
                         top_k=limit,
                         include_codebase=True,
                         include_knowledge_base=False
                    ))
                except Exception as e:
                    logger.error(f"Codebase RAG query failed: {e}")

            # 2. Query KB Store (or Combined Store)
            if rag_store_kb:
                try:
                    # If we have a separate codebase store, only ask this one for KB
                    # If we DON'T have a separate codebase store, this one has BOTH.
                    inc_cb = (rag_store_codebase is None)
                    
                    results.extend(rag_store_kb.query(
                        normalized_query,
                        top_k=limit,
                        include_codebase=inc_cb,
                        include_knowledge_base=True
                    ))
                except Exception as e:
                    logger.error(f"KB RAG query failed: {e}")

            # Deduplicate and sort results?
            # For now, just truncating the list
            final_results = results[:limit]
            
            if final_results:
                _record_tool_usage("retrieve_relevant_context", str(final_results))
                return final_results

            return [
                {
                    "error": "No relevant snippets found via RAG.",
                }
            ]

        tools.append(retrieve_relevant_context)

    return tools
