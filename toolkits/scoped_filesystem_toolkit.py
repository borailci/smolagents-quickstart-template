"""Scoped filesystem tools for sub-agents with strict path validation and context limits."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Set

from smolagents import Tool, tool

from utils.path_utils import ensure_directory, resolve_within_root
from utils.constants import IGNORED_DIRS, BLOCKED_EXTENSIONS

__all__ = ["build_scoped_tools"]

# Configurable limits to prevent context overflow
MAX_READ_LINES = 500
MAX_TREE_DEPTH = 3
MAX_TREE_ITEMS = 200


def _read_text_file_truncated(path: Path, max_lines: int = MAX_READ_LINES) -> str:
    """Reads file content with truncation to protect LLM context."""
    try:
        content_lines = []
        with path.open("r", encoding="utf-8") as handle:
            for i, line in enumerate(handle):
                if i >= max_lines:
                    content_lines.append(
                        f"\n... [Truncated after {max_lines} lines] ..."
                    )
                    break
                content_lines.append(line)
        return "".join(content_lines)
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"File '{path.name}' is not UTF-8 decodable. It may be binary."
        ) from exc


def _sanitize_mermaid_label(label: str) -> str:
    """Escapes characters that break Mermaid syntax."""
    # Replace brackets and quotes with safe alternatives
    return label.replace("[", "(").replace("]", ")").replace('"', "'")


def build_scoped_tools(
    codebase_root: str,
    workspace_root: str,
    usage_callback: Callable[[str], None] | None = None,
    *,
    allow_directory_listing: bool = False,
    allow_tree: bool = False,
    allow_mermaid: bool = False,
    allow_writes: bool = True,
    allow_kb_read: bool = False,
    knowledge_base_root: str | None = None,
) -> List[Tool]:
    """Create Smolagents tools bound to the provided codebase and workspace roots."""

    codebase_root_path = Path(codebase_root).expanduser().resolve()
    workspace_root_path = ensure_directory(workspace_root)
    kb_root_path = Path(knowledge_base_root).resolve() if knowledge_base_root else None

    def _record_tool_usage(tool_name: str) -> None:
        if usage_callback:
            usage_callback(tool_name)

    @tool
    def read_codebase_file(file_path: str) -> str:
        """Read a UTF-8 text file inside the target codebase (Truncated at 500 lines).

        Args:
            file_path: Relative path inside the codebase directory.
        """
        _record_tool_usage("read_codebase_file")
        resolved = resolve_within_root(codebase_root_path, file_path)

        if not resolved.exists():
            raise FileNotFoundError(f"File '{file_path}' not found.")
        if not resolved.is_file():
            raise IsADirectoryError(f"'{file_path}' is a directory, not a file.")

        if resolved.suffix.lower() in BLOCKED_EXTENSIONS:
            raise ValueError(f"File type '{resolved.suffix}' is not supported.")

        return _read_text_file_truncated(resolved)

    @tool
    def list_codebase_directory(dir_path: str = ".") -> List[str]:
        """List entries within a directory. Raises error if path is a file.

        Args:
            dir_path: Relative directory path to inspect. Defaults to current directory.
        """
        _record_tool_usage("list_codebase_directory")
        resolved = resolve_within_root(codebase_root_path, dir_path)

        if resolved.is_file():
            raise NotADirectoryError(
                f"Path '{dir_path}' is a file, use read_codebase_file instead."
            )
        if not resolved.is_dir():
            raise FileNotFoundError(f"Directory '{dir_path}' not found.")

        entries = []
        for entry in resolved.iterdir():
            if not entry.name.startswith(".") and entry.name not in IGNORED_DIRS:
                entries.append(entry.name)
        return sorted(entries)

    @tool
    def write_workspace_file(file_path: str, content: str, append: bool = False) -> str:
        """Write content to a file in the sub-agent workspace.

        Args:
            file_path: Relative path inside the workspace where content is written.
            content: Text to write into the file.
            append: When True, append instead of overwriting.
        """
        _record_tool_usage("write_workspace_file")
        
        # Validation: Reject empty or placeholder content
        stripped = content.strip()
        if not stripped:
            raise ValueError(
                "Cannot write empty content. You MUST generate real documentation first."
            )
        if stripped.lower() in ("_no response_", "no response", "_no response"):
            raise ValueError(
                "Placeholder content rejected. Write actual documentation."
            )
        if len(stripped) < 50 and not append:
            raise ValueError(
                f"Content too short ({len(stripped)} chars). Need at least 50 characters."
            )
        
        resolved = resolve_within_root(workspace_root_path, file_path)
        ensure_directory(resolved.parent)
        mode = "a" if append else "w"
        with resolved.open(mode, encoding="utf-8") as handle:
            handle.write(content)
        return f"Successfully wrote to {file_path}"

    @tool
    def get_codebase_tree(max_depth: int = MAX_TREE_DEPTH) -> str:
        """Return a tree structure of the codebase.

        Args:
            max_depth: Depth to traverse. Default is 3.
        """
        _record_tool_usage("get_codebase_tree")
        # Limit recursion to prevent context overflow
        lines: List[str] = ["."]

        def _build_tree(directory: Path, prefix: str, current_depth: int):
            if current_depth > max_depth or len(lines) > MAX_TREE_ITEMS:
                return

            # Filter and sort
            entries = sorted(
                child
                for child in directory.iterdir()
                if not child.name.startswith(".") and child.name not in IGNORED_DIRS
            )

            for index, entry in enumerate(entries):
                connector = "└── " if index == len(entries) - 1 else "├── "
                child_prefix = "    " if index == len(entries) - 1 else "│   "

                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    if current_depth < max_depth:
                        _build_tree(entry, prefix + child_prefix, current_depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")

        _build_tree(codebase_root_path, "", 1)

        if len(lines) > MAX_TREE_ITEMS:
            lines.append("... (Tree truncated due to size) ...")

        return "```markdown\n" + "\n".join(lines) + "\n```"

    @tool
    def get_directory_mermaid(dir_path: str = ".", max_depth: int = 3) -> str:
        """Return a Mermaid diagram for visual structure analysis.

        Args:
            dir_path: Relative directory path whose structure should be visualised.
            max_depth: Recursion depth for traversing children. Defaults to 3.
        """
        _record_tool_usage("get_directory_mermaid")
        resolved = resolve_within_root(codebase_root_path, dir_path)
        if not resolved.exists():
            return "Directory not found."

        mapping: dict[Path, str] = {}
        lines: List[str] = ["graph TD"]

        def assign_id(path: Path) -> str:
            if path not in mapping:
                mapping[path] = f"n{len(mapping)}"
            return mapping[path]

        def walk(path: Path, depth: int):
            node_id = assign_id(path)
            clean_label = _sanitize_mermaid_label(path.name)
            label = clean_label + ("/" if path.is_dir() else "")

            lines.append(f'    {node_id}["{label}"]')

            if path.is_dir() and depth < max_depth:
                children = sorted(
                    c
                    for c in path.iterdir()
                    if not c.name.startswith(".") and c.name not in IGNORED_DIRS
                )
                for child in children:
                    child_id = assign_id(child)
                    lines.append(f"    {node_id} --> {child_id}")
                    walk(child, depth + 1)

        walk(resolved, 0)
        return "```mermaid\n" + "\n".join(lines) + "\n```"

    @tool
    def list_knowledge_base() -> str:
        """List available knowledge base files."""
        _record_tool_usage("list_knowledge_base")
        if not kb_root_path or not kb_root_path.exists():
            return "Knowledge Base not found or not configured."
        return "\n".join(f.name for f in kb_root_path.glob("*.md"))

    @tool
    def read_knowledge_base_file(filename: str) -> str:
        """Read a file from the knowledge base.
        
        Args:
            filename: Name of the file (e.g., 'executive_summary.md')
        """
        _record_tool_usage("read_knowledge_base_file")
        if not kb_root_path:
             return "Knowledge Base not configured."
        
        target = kb_root_path / filename
        if not target.exists():
            return "File not found in Knowledge Base."
        
        return target.read_text(encoding="utf-8")

    tools: List[Tool] = [read_codebase_file]
    if allow_directory_listing:
        tools.append(list_codebase_directory)
    if allow_writes:
        tools.append(write_workspace_file)
    if allow_tree:
        tools.append(get_codebase_tree)
    if allow_mermaid:
        tools.append(get_directory_mermaid)
    if allow_kb_read:
        tools.append(list_knowledge_base)
        tools.append(read_knowledge_base_file)

    return tools
