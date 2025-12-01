"""Tools for querying knowledge base markdown artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from smolagents import Tool, tool

from utils.path_utils import resolve_within_root, ensure_directory

# Configurable limits for safety
_MAX_READ_LINES = 500
_MAX_TREE_DEPTH = 3
_MAX_TREE_ITEMS = 100
_SEARCH_SNIPPET_WINDOW = 200
_MAX_SEARCH_FILE_SIZE = 200_000  # 200KB limit for search scanning

def _read_text_file_truncated(path: Path) -> str:
    """Reads file content safely with line limits."""
    try:
        lines = []
        with path.open("r", encoding="utf-8") as handle:
            for i, line in enumerate(handle):
                if i >= _MAX_READ_LINES:
                    lines.append(f"\n... [Truncated after {_MAX_READ_LINES} lines] ...")
                    break
                lines.append(line)
        return "".join(lines)
    except UnicodeDecodeError:
        raise ValueError(f"File '{path.name}' is not text/markdown decodable.")


def build_knowledge_base_reader_tools(*, knowledge_base_root: str) -> List[Tool]:
    """Construct read-only tools scoped to the knowledge base directory."""

    kb_path = Path(knowledge_base_root).expanduser().resolve()
    
    # Ensure the root actually exists to prevent immediate errors
    if not kb_path.exists():
        ensure_directory(kb_path)

    @tool
    def list_knowledge_base(dir_path: str = ".") -> List[str]:
        """List entries within the knowledge base.

        Args:
            dir_path (str): Relative directory path (from the knowledge base root) to inspect.
        """
        resolved = resolve_within_root(kb_path, dir_path)
        if not resolved.is_dir():
            return [f"Error: '{dir_path}' is not a directory."]
            
        # Filter out hidden files and common noise
        return sorted(
            entry.name for entry in resolved.iterdir() 
            if not entry.name.startswith(".") and entry.name != "__pycache__"
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
        
        # Basic extension check to guide the agent
        if resolved.suffix.lower() not in {".md", ".txt", ".json"}:
            return f"Warning: '{file_path}' does not appear to be a documentation file. Content:\n" + _read_text_file_truncated(resolved)
            
        return _read_text_file_truncated(resolved)

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
        limit = max(1, max_results)

        # Walk through MD files only
        for file_path in sorted(kb_path.rglob("*.md")):
            # Skip large files for performance
            try:
                if file_path.stat().st_size > _MAX_SEARCH_FILE_SIZE:
                    continue
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Case-insensitive search
            index = content.lower().find(lowered_query)
            if index != -1:
                start = max(0, index - _SEARCH_SNIPPET_WINDOW)
                end = min(len(content), index + _SEARCH_SNIPPET_WINDOW)
                
                # Keep newlines but trim surrounding whitespace
                snippet = content[start:end].strip()
                rel_path = file_path.relative_to(kb_path)
                
                results.append(f"File: {rel_path}\nMatch: ...{snippet}...")
                
                if len(results) >= limit:
                    break

        if not results:
            return ["No matches found."]
            
        return results

    @tool
    def knowledge_base_tree(max_depth: int = _MAX_TREE_DEPTH) -> str:
        """Return a tree view of the knowledge base structure.

        Args:
            max_depth (int): Maximum depth to traverse. Default is 3.
        """
        lines = ["."]
        
        def _build_tree(directory: Path, prefix: str, depth: int):
            if depth > max_depth or len(lines) > _MAX_TREE_ITEMS:
                return

            entries = sorted(
                child for child in directory.iterdir() 
                if not child.name.startswith(".") and child.name != "__pycache__"
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

        _build_tree(kb_path, "", 1)
        
        if len(lines) > _MAX_TREE_ITEMS:
            lines.append("... (Tree truncated) ...")
            
        return "```markdown\n" + "\n".join(lines) + "\n```"

    return [
        list_knowledge_base,
        read_knowledge_base_file,
        search_knowledge_base,
        knowledge_base_tree,
    ]