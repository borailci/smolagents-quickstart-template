"""Scoped filesystem tools for sub-agents with strict path validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from smolagents import Tool, tool

from utils.path_utils import ensure_directory, resolve_within_root


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


def build_scoped_tools(codebase_root: str, workspace_root: str) -> List[Tool]:
    """Create Smolagents tools bound to the provided codebase and workspace roots."""

    codebase_root_path = Path(codebase_root).expanduser().resolve()
    workspace_root_path = ensure_directory(workspace_root)

    @tool
    def read_codebase_file(file_path: str) -> str:
        """Read a UTF-8 text file inside the target codebase.

        Args:
            file_path: Relative path inside the codebase directory.
        """

        resolved = resolve_within_root(codebase_root_path, file_path)
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
        """List entries within a directory of the codebase.

        Args:
            dir_path: Relative directory path to inspect. Defaults to current directory.
        """

        resolved = resolve_within_root(codebase_root_path, dir_path)
        if not resolved.is_dir():
            return []
        return sorted(
            entry.name for entry in resolved.iterdir() if not entry.name.startswith(".")
        )

    @tool
    def write_workspace_file(file_path: str, content: str, append: bool = False) -> str:
        """Write content to a file in the sub-agent workspace.

        Args:
            file_path: Relative path inside the workspace where content is written.
            content: Text to write into the file.
            append: When True, append instead of overwriting.
        """

        resolved = resolve_within_root(workspace_root_path, file_path)
        _write_text_file(resolved, content, append=append)
        return str(resolved)

    @tool
    def get_codebase_tree() -> str:
        """Return a markdown-formatted tree of the accessible codebase."""

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

        lines = ["."] + tree(codebase_root_path)
        return "```markdown\n" + "\n".join(lines) + "\n```"

    return [
        read_codebase_file,
        list_codebase_directory,
        write_workspace_file,
        get_codebase_tree,
    ]
