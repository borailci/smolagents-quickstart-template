"""Scoped filesystem tools for sub-agents with strict path validation and context limits.

Uses class-based Tool definitions to avoid smolagents @tool decorator + nested function issues.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from smolagents import Tool


# Inlined from utils.path_utils and utils.constants
IGNORED_DIRS = {
    "__pycache__", ".git", ".idea", ".vscode", "node_modules", "venv", ".venv",
    "site-packages", "dist", "build", ".DS_Store", "docs", "tests", "examples",
    "scripts", ".gradio", ".pytest_cache"
}
BLOCKED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin", ".pkl",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".jpg", ".jpeg", ".png", ".gif",
    ".webp", ".ico", ".svg", ".mp4", ".mp3", ".wav", ".pdf", ".docx",
    ".lock"
}

def ensure_directory(path: str | Path) -> Path:
    p = Path(path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p

def resolve_within_root(root: Path, path: str | Path) -> Path:
    """Resolve path and ensure it's within root."""
    # Normalize paths
    root = root.resolve()
    try:
        # Handle absolute paths that might be inside root
         p = Path(path)
         if p.is_absolute():
             resolved = p.resolve()
         else:
             resolved = (root / path).resolve()
             
         if not str(resolved).startswith(str(root)):
             raise ValueError(f"Path traversal detected: {path} is outside {root}")
         return resolved
    except Exception as e:
        # Fallback for weird path issues
        raise ValueError(f"Invalid path {path}: {e}")

from config import settings

__all__ = ["build_scoped_tools", "ensure_directory", "resolve_within_root", "IGNORED_DIRS"]

# Use centralized config for limits
MAX_READ_LINES = settings.MAX_READ_LINES
MAX_TREE_DEPTH = settings.MAX_TREE_DEPTH
MAX_TREE_ITEMS = settings.MAX_TREE_ITEMS


def _read_text_file_truncated(path: Path, start_line: int = 1, max_lines: int = MAX_READ_LINES) -> str:
    """Reads file content with truncation to protect LLM context."""
    try:
        content_lines = []
        start_index = max(0, start_line - 1)
        end_index = start_index + max_lines

        with path.open("r", encoding="utf-8") as handle:
            for i, line in enumerate(handle):
                if i < start_index:
                    continue
                if i >= end_index:
                    content_lines.append(
                        f"\n... [Truncated. Read lines {start_line}-{end_index} (limit: {max_lines}). Use start_line={end_index+1} to read more] ..."
                    )
                    break
                content_lines.append(line)
        
        if not content_lines:
           if start_line > 1:
               return f"End of file reached. File has fewer than {start_line} lines."
           return ""

        return "".join(content_lines)
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"File '{path.name}' is not UTF-8 decodable. It may be binary."
        ) from exc


def _sanitize_mermaid_label(label: str) -> str:
    """Escapes characters that break Mermaid syntax."""
    return label.replace("[", "(").replace("]", ")").replace('"', "'")


# ============================================================================
# Class-based Tool definitions (avoids inspect.getsource() issues with @tool)
# ============================================================================

class ReadCodebaseFileTool(Tool):
    """Read file from codebase with pagination support."""
    
    name = "read_codebase_file"
    description = """Read file from codebase (max 350 lines per call).
If file is truncated, call again with start_line=N to continue reading."""
    
    inputs = {
        "file_path": {"type": "string", "description": "Relative path to file."},
        "start_line": {"type": "integer", "description": "Start reading from this line (1-indexed). Default: 1.", "nullable": True},
    }
    output_type = "string"
    
    def __init__(self, codebase_root: Path, workspace_root: Path = None, usage_callback: Optional[Callable] = None):
        super().__init__()
        self.codebase_root = codebase_root
        self.workspace_root = workspace_root
        self.usage_callback = usage_callback
    
    def forward(self, file_path: str, start_line: int = 1) -> str:
        # 1. Try resolving in codebase
        resolved = resolve_within_root(self.codebase_root, file_path)
        
        # 2. If not found, try workspace (if provided)
        if not resolved.exists() and self.workspace_root:
            try:
                workspace_resolved = resolve_within_root(self.workspace_root, file_path)
                if workspace_resolved.exists():
                    resolved = workspace_resolved
            except Exception:
                pass # Ignore errors in workspace resolution fallback

        if not resolved.exists():
            raise FileNotFoundError(f"File '{file_path}' not found in codebase or workspace.")
        if not resolved.is_file():
            raise IsADirectoryError(f"'{file_path}' is a directory, not a file.")

        if resolved.suffix.lower() in BLOCKED_EXTENSIONS:
            raise ValueError(f"File type '{resolved.suffix}' is not supported.")

        result = _read_text_file_truncated(resolved, start_line=start_line or 1)
        if self.usage_callback:
            self.usage_callback("read_codebase_file")
        return result


class ListCodebaseDirectoryTool(Tool):
    """List files and folders in a directory."""
    
    name = "list_codebase_directory"
    description = "List files/folders in a directory."
    
    inputs = {
        "dir_path": {"type": "string", "description": "Directory path (default: root).", "nullable": True},
    }
    output_type = "string"
    
    def __init__(self, codebase_root: Path, usage_callback: Optional[Callable] = None):
        super().__init__()
        self.codebase_root = codebase_root
        self.usage_callback = usage_callback
    
    def forward(self, dir_path: str = ".") -> str:
        # Handle None explicitly
        if dir_path is None:
            dir_path = "."
            
        resolved = resolve_within_root(self.codebase_root, dir_path)

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
        
        if self.usage_callback:
            self.usage_callback("list_codebase_directory")
        return "\n".join(sorted(entries))


class WriteWorkspaceFileTool(Tool):
    """Write content or create workspace file."""
    
    name = "write_workspace_file"
    description = """Write content to workspace file. IMPORTANT: You must FIRST read source files using read_codebase_file() to gather information, then generate your content, and ONLY THEN call this tool with the actual content. Content must be at least 50 chars. Empty content will be rejected."""
    
    inputs = {
        "file_path": {"type": "string", "description": "Target file path."},
        "content": {"type": "string", "description": "Text to write. MUST NOT BE EMPTY. Generate your full content first, then pass it here."},
        "append": {"type": "boolean", "description": "Append instead of overwrite.", "nullable": True},
    }
    output_type = "string"
    
    def __init__(self, workspace_root: Path, usage_callback: Optional[Callable] = None):
        super().__init__()
        self.workspace_root = workspace_root
        self.usage_callback = usage_callback
    
    def forward(self, file_path: str, content: str, append: bool = False) -> str:
        if not content or not content.strip():
            raise ValueError(
                "Content cannot be empty or only whitespace. "
                "You must generate the file content (the plan or the summary) "
                "in your thought process FIRST, and then call this tool with the complete text."
            )
            
        if self.usage_callback:
            self.usage_callback("write_workspace_file")
        
        resolved = resolve_within_root(self.workspace_root, file_path)
        ensure_directory(resolved.parent)
        mode = "a" if append else "w"
        with resolved.open(mode, encoding="utf-8") as handle:
            handle.write(content)
        return f"Successfully wrote to {file_path}"


class GetCodebaseTreeTool(Tool):
    """Get directory tree structure."""
    
    name = "get_codebase_tree"
    description = "Get directory tree structure."
    
    inputs = {
        "max_depth": {"type": "integer", "description": "Max traversal depth (default: 5).", "nullable": True},
    }
    output_type = "string"
    
    def __init__(self, codebase_root: Path, usage_callback: Optional[Callable] = None):
        super().__init__()
        self.codebase_root = codebase_root
        self.usage_callback = usage_callback
    
    def forward(self, max_depth: int = MAX_TREE_DEPTH) -> str:
        if self.usage_callback:
            self.usage_callback("get_codebase_tree")
            
        max_depth = max_depth or MAX_TREE_DEPTH
        lines: List[str] = ["."]

        def _build_tree(directory: Path, prefix: str, current_depth: int):
            if current_depth > max_depth or len(lines) > MAX_TREE_ITEMS:
                return

            entries = sorted(
                child
                for child in directory.iterdir()
                if not child.name.startswith(".") 
                and child.name not in IGNORED_DIRS
                and (child.is_dir() or child.suffix.lower() not in BLOCKED_EXTENSIONS)
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

        _build_tree(self.codebase_root, "", 1)

        if len(lines) > MAX_TREE_ITEMS:
            lines.append("... (Tree truncated due to size) ...")

        return "```markdown\n" + "\n".join(lines) + "\n```"


class GetDirectoryMermaidTool(Tool):
    """Generate Mermaid diagram of directory structure."""
    
    name = "get_directory_mermaid"
    description = "Generate Mermaid diagram of directory structure."
    
    inputs = {
        "dir_path": {"type": "string", "description": "Directory to visualize.", "nullable": True},
        "max_depth": {"type": "integer", "description": "Traversal depth.", "nullable": True},
    }
    output_type = "string"
    
    def __init__(self, codebase_root: Path, usage_callback: Optional[Callable] = None):
        super().__init__()
        self.codebase_root = codebase_root
        self.usage_callback = usage_callback
    
    def forward(self, dir_path: str = ".", max_depth: int = 3) -> str:
        if self.usage_callback:
            self.usage_callback("get_directory_mermaid")
            
        dir_path = dir_path or "."
        max_depth = max_depth or 3
        
        resolved = resolve_within_root(self.codebase_root, dir_path)
        if not resolved.exists():
            return "Directory not found."

        mapping: Dict[Path, str] = {}
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


# ListKnowledgeBaseTool and ReadKnowledgeBaseFileTool removed - use ReadCodebaseFileTool with KB path instead




# ============================================================================
# Factory function
# ============================================================================

def build_scoped_tools(
    codebase_root: str,
    workspace_root: str,
    usage_callback: Callable[[str], None] | None = None,
    *,
    allow_directory_listing: bool = False,
    allow_tree: bool = False,
    allow_mermaid: bool = False,
    allow_writes: bool = True,
) -> List[Tool]:
    """Create Smolagents tools bound to the provided codebase and workspace roots."""

    codebase_root_path = Path(codebase_root).expanduser().resolve()
    workspace_root_path = ensure_directory(workspace_root)

    tools: List[Tool] = [
        ReadCodebaseFileTool(codebase_root_path, workspace_root_path, usage_callback)
    ]
    
    if allow_directory_listing:
        tools.append(ListCodebaseDirectoryTool(codebase_root_path, usage_callback))
    if allow_writes:
        tools.append(WriteWorkspaceFileTool(workspace_root_path, usage_callback))
    if allow_tree:
        tools.append(GetCodebaseTreeTool(codebase_root_path, usage_callback))
    if allow_mermaid:
        tools.append(GetDirectoryMermaidTool(codebase_root_path, usage_callback))

    return tools

