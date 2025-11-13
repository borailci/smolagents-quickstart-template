"""Tools for tutorial generation leveraging the knowledge base and codebase."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger
from smolagents import Tool, tool

from toolkits.rag_store import SimpleChromaRAGStore
from utils.path_utils import ensure_directory, resolve_within_root

_MAX_SEARCH_FILE_SIZE_BYTES = 200_000
_DEFAULT_RAG_MAX_SNIPPETS = 5
_SNIPPET_PADDING_CHARS = 240
_CODE_SEARCH_SKIP_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".exe",
    ".class",
    ".zip",
    ".tar",
    ".gz",
}
_CODE_SEARCH_ALLOWED_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".swift",
    ".kt",
    "",
}


def _read_text_file(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return handle.read()
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"File '{path}' is not UTF-8 decodable. Skip binary or compiled artifacts."
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
) -> List[Tool]:
    codebase_path = Path(codebase_root).expanduser().resolve()
    kb_path = Path(knowledge_base_root).expanduser().resolve()
    output_path = ensure_directory(tutorial_output_root)

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
            rag_store.ensure_index(
                include_codebase=True,
                include_knowledge_base=True,
                force_rebuild=True,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to initialise RAG vector store: {}", exc)
            rag_store = None

    max_snippets = max(1, rag_max_snippets)

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
            entry.name for entry in resolved.iterdir() if not entry.name.startswith(".")
        )

    @tool
    def read_knowledge_base_file(file_path: str) -> str:
        """Read a markdown file from the knowledge base.

        Args:
            file_path: Relative path to the markdown file inside the knowledge base directory.
        """

        resolved = resolve_within_root(kb_path, file_path)
        return _read_text_file(resolved)

    @tool
    def read_codebase_file(file_path: str) -> str:
        """Read a source file from the codebase.

        Args:
            file_path: Relative path of the source file to read from the codebase root.
        """

        resolved = resolve_within_root(codebase_path, file_path)
        if "__pycache__" in resolved.parts:
            raise ValueError(
                "Compiled directories such as __pycache__ are not readable."
            )
        if not resolved.is_file():
            raise FileNotFoundError(
                f"File '{file_path}' not found inside the codebase."
            )
        blocked_suffixes = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe"}
        if resolved.suffix.lower() in blocked_suffixes:
            raise ValueError(
                f"Binary or compiled file '{file_path}' is not supported; choose a text source."
            )
        return _read_text_file(resolved)

    @tool
    def list_codebase_directory(dir_path: str = ".") -> List[str]:
        """List entries in the codebase under the provided directory.

        Args:
            dir_path: Relative directory path whose contents should be listed.
        """

        resolved = resolve_within_root(codebase_path, dir_path)
        if not resolved.is_dir():
            return []
        return sorted(
            entry.name for entry in resolved.iterdir() if not entry.name.startswith(".")
        )

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

    @tool
    def get_codebase_tree() -> str:
        """Return a tree view of the accessible codebase."""

        def tree(directory: Path, prefix: str = "") -> List[str]:
            entries = sorted(
                child for child in directory.iterdir() if not child.name.startswith(".")
            )
            lines: List[str] = []
            for index, entry in enumerate(entries):
                connector = "└── " if index == len(entries) - 1 else "├── "
                child_prefix = "    " if index == len(entries) - 1 else "│   "
                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    lines.extend(tree(entry, prefix + child_prefix))
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")
            return lines

        lines = ["."] + tree(codebase_path)
        return "```markdown\n" + "\n".join(lines) + "\n```"

    tools: List[Tool] = [
        list_knowledge_base,
        read_knowledge_base_file,
        read_codebase_file,
        list_codebase_directory,
        write_tutorial_file,
        get_codebase_tree,
    ]

    if enable_code_search:

        @tool
        def grep_codebase(
            pattern: str,
            dir_path: str = ".",
            ignore_case: bool = True,
            max_matches: int = 20,
        ) -> List[str]:
            """Search codebase files for lines matching a regular expression.

            Args:
                pattern: Regular expression to search for within files.
                dir_path: Relative directory or file path to scope the search (defaults to the repo root).
                ignore_case: Perform case-insensitive matching when True.
                max_matches: Maximum number of line hits to return.
            """

            if not pattern:
                return []

            try:
                resolved = resolve_within_root(codebase_path, dir_path)
            except ValueError:
                return []

            flags = re.IGNORECASE if ignore_case else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as exc:  # pragma: no cover - invalid user regex
                return [f"Invalid regular expression: {exc}"]

            matches: List[str] = []

            def _search_file(file_path: Path) -> None:
                if file_path.suffix.lower() in _CODE_SEARCH_SKIP_SUFFIXES:
                    return
                if (
                    file_path.suffix
                    and file_path.suffix.lower() not in _CODE_SEARCH_ALLOWED_SUFFIXES
                ):
                    return
                try:
                    if file_path.stat().st_size > _MAX_SEARCH_FILE_SIZE_BYTES:
                        return
                except FileNotFoundError:
                    return

                try:
                    content = file_path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    return

                for line_number, line in enumerate(content.splitlines(), start=1):
                    if regex.search(line):
                        relative = file_path.relative_to(codebase_path)
                        snippet = line.strip()
                        matches.append(f"{relative}:{line_number}: {snippet}")
                        if len(matches) >= max_matches:
                            return

            if resolved.is_file():
                _search_file(resolved)
            else:
                for candidate in sorted(
                    p
                    for p in resolved.rglob("*")
                    if p.is_file() and not p.name.startswith(".")
                ):
                    _search_file(candidate)
                    if len(matches) >= max_matches:
                        break

            return matches

        tools.append(grep_codebase)

    if enable_rag:

        @tool
        def retrieve_relevant_context(
            query: str,
            max_snippets: int = max_snippets,
            include_codebase: bool = True,
            include_knowledge_base: bool = True,
        ) -> List[Dict[str, str]]:
            """Return contextual snippets related to the query from docs and source.

            Args:
                query: Free-text query to match against files.
                max_snippets: Maximum number of snippets to return in total.
                include_codebase: Search source files when True.
                include_knowledge_base: Search knowledge base markdown when True.
            """

            normalized_query = query.strip()
            if not normalized_query:
                return []

            limit = max(1, max_snippets)
            if rag_store is not None:
                try:
                    rag_results = rag_store.query(
                        normalized_query,
                        top_k=limit,
                        include_codebase=include_codebase,
                        include_knowledge_base=include_knowledge_base,
                    )
                    if rag_results:
                        return rag_results[:limit]
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning(
                        "RAG query failed; falling back to substring search: {}", exc
                    )

            lowered_query = normalized_query.lower()

            def _fallback_search() -> List[Dict[str, str]]:
                snippets: List[Dict[str, str]] = []

                def _append_snippet(
                    *,
                    source: str,
                    root: Path,
                    file_path: Path,
                    content: str,
                ) -> None:
                    lowered_content = content.lower()
                    index = lowered_content.find(lowered_query)
                    if index == -1:
                        return
                    start = max(0, index - _SNIPPET_PADDING_CHARS)
                    end = min(len(content), index + _SNIPPET_PADDING_CHARS)
                    snippet_text = content[start:end].strip()

                    line_number = content.count("\n", 0, start) + 1
                    entry = {
                        "source": source,
                        "path": str(file_path.relative_to(root)),
                        "line": str(line_number),
                        "snippet": snippet_text,
                    }
                    snippets.append(entry)

                if include_knowledge_base:
                    for kb_file in sorted(kb_path.rglob("*.md")):
                        try:
                            if kb_file.stat().st_size > _MAX_SEARCH_FILE_SIZE_BYTES:
                                continue
                        except FileNotFoundError:
                            continue
                        try:
                            content = kb_file.read_text(encoding="utf-8")
                        except (UnicodeDecodeError, OSError):
                            continue
                        _append_snippet(
                            source="knowledge_base",
                            root=kb_path,
                            file_path=kb_file,
                            content=content,
                        )
                        if len(snippets) >= limit:
                            return snippets[:limit]

                if include_codebase:
                    for candidate in sorted(
                        path
                        for path in codebase_path.rglob("*")
                        if path.is_file() and not path.name.startswith(".")
                    ):
                        if candidate.suffix.lower() in _CODE_SEARCH_SKIP_SUFFIXES:
                            continue
                        if (
                            candidate.suffix
                            and candidate.suffix.lower()
                            not in _CODE_SEARCH_ALLOWED_SUFFIXES
                        ):
                            continue
                        try:
                            if candidate.stat().st_size > _MAX_SEARCH_FILE_SIZE_BYTES:
                                continue
                        except FileNotFoundError:
                            continue
                        try:
                            content = candidate.read_text(encoding="utf-8")
                        except (UnicodeDecodeError, OSError):
                            continue
                        _append_snippet(
                            source="codebase",
                            root=codebase_path,
                            file_path=candidate,
                            content=content,
                        )
                        if len(snippets) >= limit:
                            return snippets[:limit]

                return snippets[:limit]

            return _fallback_search()

        tools.append(retrieve_relevant_context)

    return tools
