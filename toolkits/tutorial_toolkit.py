"""Tools for tutorial generation leveraging the knowledge base and optional RAG."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger
from smolagents import Tool, tool

from toolkits.rag_store import SimpleChromaRAGStore
from utils.path_utils import ensure_directory, resolve_within_root

_MAX_READ_LINES = 500  # Limit KB reads to protect context
_DEFAULT_RAG_MAX_SNIPPETS = 5

_IGNORED_DIRS = {
    "__pycache__",
    "node_modules",
    "venv",
    ".git",
    ".idea",
    ".vscode",
    "dist",
    "build",
}


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
    enable_code_search: bool = False,
    enable_rag: bool = False,
    rag_max_snippets: int = _DEFAULT_RAG_MAX_SNIPPETS,
    rag_force_rebuild: bool = False,  # Added explicit control
) -> List[Tool]:
    codebase_path = Path(codebase_root).expanduser().resolve()
    kb_path = Path(knowledge_base_root).expanduser().resolve()
    output_path = ensure_directory(tutorial_output_root)

    if enable_code_search:
        logger.warning(
            "Tutorial generator no longer exposes direct code search; "
            "ignoring enable_code_search flag."
        )

    rag_store: Optional[SimpleChromaRAGStore] = None
    if enable_rag:
        rag_storage_root = ensure_directory(
            (output_path.parent if output_path.parent != output_path else output_path)
            / "rag_vector_store"
        )
        try:
            rag_store = SimpleChromaRAGStore(
                codebase_root=codebase_path,
                knowledge_base_root=kb_path,
                persist_directory=rag_storage_root,
            )
            # CRITICAL FIX: Do not force rebuild by default.
            # This prevents 5-10 minute delays on agent startup.
            rag_store.ensure_index(
                include_codebase=True,
                include_knowledge_base=True,
                force_rebuild=rag_force_rebuild,
            )
        except Exception as exc:
            logger.warning("Failed to initialize RAG vector store: {}", exc)
            rag_store = None

    max_snippets = max(1, rag_max_snippets)

    def _is_safe_entry(entry: Path) -> bool:
        return not entry.name.startswith(".") and entry.name not in _IGNORED_DIRS

    @tool
    def list_knowledge_base(dir_path: str = ".") -> List[str]:
        """List markdown files in the knowledge base.

        Args:
            dir_path: Relative directory path within the knowledge base to inspect.
        """
        resolved = resolve_within_root(kb_path, dir_path)
        if not resolved.is_dir():
            return []
        return sorted(
            entry.name for entry in resolved.iterdir() if _is_safe_entry(entry)
        )

    @tool
    def read_knowledge_base_file(file_path: str) -> str:
        """Read a markdown file from the knowledge base.

        Args:
            file_path: Relative path to the markdown file inside the knowledge base directory.
        """
        resolved = resolve_within_root(kb_path, file_path)
        return _read_text_file_truncated(resolved)

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
        return str(resolved)

    tools: List[Tool] = [
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

            # Primary method: Vector Search
            if rag_store:
                try:
                    return rag_store.query(
                        normalized_query,
                        top_k=limit,
                        include_codebase=True,
                        include_knowledge_base=True,
                    )[:limit]
                except Exception as exc:
                    logger.error(f"RAG query failed: {exc}")
                    return [
                        {
                            "error": "RAG search failed. Fall back to the knowledge base files provided.",
                        }
                    ]

            return [
                {
                    "error": "RAG is not enabled. Use list_knowledge_base/read_knowledge_base_file instead.",
                }
            ]

        tools.append(retrieve_relevant_context)

    return tools
