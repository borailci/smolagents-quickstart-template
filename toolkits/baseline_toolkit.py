"""Baseline file/code exploration tools for tutorial agents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

from loguru import logger
from smolagents import Tool, tool

from toolkits.rag_store import SimpleChromaRAGStore
from utils.path_utils import ensure_directory, resolve_within_root

__all__ = ["build_baseline_tools"]

_MAX_READ_LINES = 600
_MAX_TREE_DEPTH = 3
_MAX_TREE_ITEMS = 200
_MAX_SEARCH_FILE_SIZE = 200_000
_IGNORED_DIRS = {
    "__pycache__",
    "node_modules",
    "venv",
    ".git",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "target",
}


def _read_text_file_truncated(
    path: Path, start_line: int = 1, end_line: Optional[int] = None
) -> str:
    start = max(1, start_line)
    stop = end_line if end_line and end_line >= start else start + _MAX_READ_LINES - 1

    lines: List[str] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle, start=1):
                if idx < start:
                    continue
                if idx > stop:
                    lines.append(
                        f"\n... [Truncated after {_MAX_READ_LINES} lines or end_line limit] ..."
                    )
                    break
                lines.append(line)
    except UnicodeDecodeError as exc:
        raise ValueError(f"File '{path.name}' is not UTF-8 decodable.") from exc
    return "".join(lines)


def build_baseline_tools(
    *,
    codebase_root: str,
    tutorial_output_root: str,
    knowledge_base_root: str,
    rag_force_rebuild: bool = False,
    usage_callback: Callable[[str, str | None], None] | None = None,
) -> List[Tool]:
    codebase_path = Path(codebase_root).expanduser().resolve()
    output_path = ensure_directory(tutorial_output_root)
    kb_path = Path(knowledge_base_root).expanduser().resolve()

    def _record_tool_usage(tool_name: str, content: str | None = None) -> None:
        if usage_callback:
            try:
                usage_callback(tool_name, content)
            except Exception:
                # Metrics callbacks should never break tool execution.
                pass

    rag_store: Optional[SimpleChromaRAGStore] = None
    try:
        rag_storage_root = ensure_directory(output_path.parent / "rag_vector_store")
        rag_store = SimpleChromaRAGStore(
            codebase_root=codebase_path,
            knowledge_base_root=kb_path,
            persist_directory=rag_storage_root,
        )
        rag_store.ensure_index(
            include_codebase=True,
            include_knowledge_base=True,
            force_rebuild=rag_force_rebuild,
        )
    except Exception as exc:
        logger.warning("RAG store unavailable: {}", exc)
        rag_store = None

    def _is_safe_entry(entry: Path) -> bool:
        return not entry.name.startswith(".") and entry.name not in _IGNORED_DIRS

    @tool
    def read_file(
        path: str, start_line: int = 1, end_line: Optional[int] = None
    ) -> str:
        """Read a codebase file.

        Args:
            path: Relative path under the codebase root.
            start_line: 1-based line number to start reading from.
            end_line: Optional inclusive line number to stop; defaults to a capped window.
        """

        resolved = resolve_within_root(codebase_path, path)
        if not resolved.is_file():
            raise FileNotFoundError(f"'{path}' does not exist.")
        output = _read_text_file_truncated(
            resolved, start_line=start_line, end_line=end_line
        )
        _record_tool_usage("read_file", output)
        return output

    @tool
    def read_file_bulk(paths: List[str]) -> List[str]:
        """Read multiple files (truncated) for quick sampling.

        Args:
            paths: List of relative file paths under the codebase root.
        """

        outputs: List[str] = []
        for item in paths:
            try:
                resolved = resolve_within_root(codebase_path, item)
                if not resolved.is_file():
                    outputs.append(f"{item}: [missing]")
                    continue
                outputs.append(f"=== {item} ===\n{_read_text_file_truncated(resolved)}")
            except Exception as exc:
                outputs.append(f"{item}: [error] {exc}")
        _record_tool_usage("read_file_bulk", "\n".join(outputs))
        return outputs

    @tool
    def file_search(
        pattern: str, max_results: int = 20, regex: bool = False
    ) -> List[str]:
        """Search for a pattern in text files under the codebase root.

        Args:
            pattern: Plaintext or regex string to search for.
            max_results: Maximum number of matching files to return.
            regex: Whether to treat pattern as a regular expression.
        """

        if not pattern:
            return []
        matches: List[str] = []
        compiled: Optional[re.Pattern[str]] = None
        if regex:
            try:
                compiled = re.compile(pattern)
            except re.error as exc:
                return [f"Invalid regex: {exc}"]
        for path in sorted(codebase_path.rglob("*")):
            if path.is_dir():
                if not _is_safe_entry(path):
                    continue
                continue
            if path.stat().st_size > _MAX_SEARCH_FILE_SIZE:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            match_found = False
            if compiled:
                if compiled.search(text):
                    match_found = True
            else:
                if pattern.lower() in text.lower():
                    match_found = True
            if match_found:
                matches.append(str(path.relative_to(codebase_path)))
                if len(matches) >= max(1, max_results):
                    break
        output = matches or ["No matches found."]
        _record_tool_usage("file_search", "\n".join(output))
        return output

    @tool
    def get_tree(max_depth: int = _MAX_TREE_DEPTH) -> str:
        """Return a tree view of the codebase.

        Args:
            max_depth: Maximum depth to traverse when building the tree.
        """

        lines = ["."]

        def _build_tree(directory: Path, prefix: str, depth: int) -> None:
            if depth > max_depth or len(lines) > _MAX_TREE_ITEMS:
                return
            entries = sorted(
                child for child in directory.iterdir() if _is_safe_entry(child)
            )
            for index, entry in enumerate(entries):
                connector = "└── " if index == len(entries) - 1 else "├── "
                child_prefix = "    " if index == len(entries) - 1 else "│   "
                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    if depth < max_depth:
                        _build_tree(entry, prefix + child_prefix, depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")

        _build_tree(codebase_path, "", 1)
        if len(lines) > _MAX_TREE_ITEMS:
            lines.append("... (Tree truncated) ...")
        tree_text = "```markdown\n" + "\n".join(lines) + "\n```"
        _record_tool_usage("get_tree", tree_text)
        return tree_text

    @tool
    def semantic_search(
        query: str,
        max_snippets: int = 5,
        include_codebase: bool = True,
        include_knowledge_base: bool = False,
    ) -> List[Dict[str, str]]:
        """Semantic search via the shared RAG store.

        Args:
            query: Natural language query to embed and search.
            max_snippets: Maximum snippets to return.
            include_codebase: Whether to search codebase chunks.
            include_knowledge_base: Whether to search knowledge base chunks.
        """

        if not query.strip():
            return []
        limit = max(1, max_snippets)
        if not rag_store:
            return [{"error": "RAG store unavailable."}]
        try:
            output = rag_store.query(
                query,
                top_k=limit,
                include_codebase=include_codebase,
                include_knowledge_base=include_knowledge_base,
            )[:limit]
            _record_tool_usage("semantic_search", str(output))
            return output
        except Exception as exc:
            logger.error("RAG query failed: {}", exc)
            return [{"error": f"RAG query failed: {exc}"}]

    @tool
    def write_file(path: str, content: str, append: bool = False) -> str:
        """Write to the tutorials output directory (append supported).

        Args:
            path: Relative output path under the tutorials directory.
            content: Content to write.
            append: Whether to append instead of overwrite.
        """

        resolved = resolve_within_root(output_path, path)
        ensure_directory(resolved.parent)
        mode = "a" if append else "w"
        with resolved.open(mode, encoding="utf-8") as handle:
            handle.write(content)
        _record_tool_usage("write_file", None)
        return str(resolved)

    return [
        read_file,
        read_file_bulk,
        file_search,
        get_tree,
        semantic_search,
        write_file,
    ]
