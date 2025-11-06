"""Tools for tutorial generation leveraging the knowledge base and codebase."""

from __future__ import annotations

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


def build_tutorial_tools(
    *,
    codebase_root: str,
    knowledge_base_root: str,
    tutorial_output_root: str,
) -> List[Tool]:
    codebase_path = Path(codebase_root).expanduser().resolve()
    kb_path = Path(knowledge_base_root).expanduser().resolve()
    output_path = ensure_directory(tutorial_output_root)

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

    return tools
