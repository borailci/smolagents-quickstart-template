"""Tools for querying knowledge base markdown artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import List

from smolagents import Tool, tool

from utils.path_utils import resolve_within_root


def _read_text_file(path: Path) -> str:
    with path.open("r", encoding="utf-8") as handle:
        return handle.read()


def build_knowledge_base_reader_tools(*, knowledge_base_root: str) -> List[Tool]:
    """Construct read-only tools scoped to the knowledge base directory."""

    kb_path = Path(knowledge_base_root).expanduser().resolve()

    @tool
    def list_knowledge_base(dir_path: str = ".") -> List[str]:
        """List entries within the knowledge base.

        Args:
            dir_path (str): Relative directory path (from the knowledge base root) to inspect.
        """

        resolved = resolve_within_root(kb_path, dir_path)
        if not resolved.is_dir():
            return []
        return sorted(
            entry.name for entry in resolved.iterdir() if not entry.name.startswith(".")
        )

    @tool
    def read_knowledge_base_file(file_path: str) -> str:
        """Read a markdown artifact from the knowledge base.

        Args:
            file_path (str): Relative path to the markdown file inside the knowledge base root.
        """

        resolved = resolve_within_root(kb_path, file_path)
        if not resolved.is_file():
            raise FileNotFoundError(f"Knowledge base file '{file_path}' was not found.")
        return _read_text_file(resolved)

    @tool
    def search_knowledge_base(query: str, max_results: int = 5) -> List[str]:
        """Return snippets from knowledge base files that mention the query.

        Args:
            query (str): Free-text query to look for (case-insensitive).
            max_results (int): Maximum number of snippets to return.
        """

        if not query.strip():
            return []

        results: List[str] = []
        lowered_query = query.lower()

        for file_path in sorted(kb_path.rglob("*.md")):
            content = file_path.read_text(encoding="utf-8")
            if lowered_query in content.lower():
                first_index = content.lower().find(lowered_query)
                start = max(0, first_index - 120)
                end = min(len(content), first_index + 120)
                snippet = content[start:end].replace("\n", " ")
                results.append(f"{file_path.relative_to(kb_path)}: {snippet}...")
                if len(results) >= max_results:
                    break

        return results

    @tool
    def knowledge_base_tree() -> str:
        """Return a tree view of the knowledge base structure."""

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

        lines = ["."] + tree(kb_path)
        return "```markdown\n" + "\n".join(lines) + "\n```"

    return [
        list_knowledge_base,
        read_knowledge_base_file,
        search_knowledge_base,
        knowledge_base_tree,
    ]
