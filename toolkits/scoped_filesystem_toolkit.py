"""Scoped filesystem tools for sub-agents with strict path validation and context limits.

Uses class-based Tool definitions to avoid smolagents @tool decorator + nested function issues.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from smolagents import Tool

from utils.path_utils import ensure_directory, resolve_within_root
from utils.constants import IGNORED_DIRS, BLOCKED_EXTENSIONS

__all__ = ["build_scoped_tools"]

# Configurable limits to prevent context overflow
MAX_READ_LINES = 350
MAX_TREE_DEPTH = 5
MAX_TREE_ITEMS = 200


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
    """Write content to workspace file."""
    
    name = "write_workspace_file"
    description = "Write content to workspace file. Min 50 chars required."
    
    inputs = {
        "file_path": {"type": "string", "description": "Target file path."},
        "content": {"type": "string", "description": "Text to write."},
        "append": {"type": "boolean", "description": "Append instead of overwrite.", "nullable": True},
    }
    output_type = "string"
    
    def __init__(self, workspace_root: Path, usage_callback: Optional[Callable] = None):
        super().__init__()
        self.workspace_root = workspace_root
        self.usage_callback = usage_callback
    
    def forward(self, file_path: str, content: str, append: bool = False) -> str:
        if self.usage_callback:
            self.usage_callback("write_workspace_file")
        
        stripped = content.strip()
        
        if not stripped:
            raise ValueError(
                "EMPTY CONTENT REJECTED. You must first read source files and generate actual documentation. "
                "Use read_codebase_file() to gather information, then write real content."
            )
        
        fallback_patterns = (
            "_no response_", 
            "no response", 
            "_no response was received",
            "no response was received from the model",
        )
        
        # Only check for fallback patterns if content is short or it's an exact match line
        if len(stripped) < 200 or any(stripped.lower() == p for p in fallback_patterns):
            if any(pattern in stripped.lower() for pattern in fallback_patterns):
                raise ValueError(
                    "MODEL FALLBACK DETECTED. The previous generation failed. "
                    "Try again: read source files first, then generate content."
                )
        
        if len(stripped) < 50 and not append:
            raise ValueError(
                f"CONTENT TOO SHORT ({len(stripped)} chars, need 50+). "
                "Write comprehensive documentation with code examples."
            )
        
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
        "max_depth": {"type": "integer", "description": "Max traversal depth (default: 3).", "nullable": True},
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


class ListKnowledgeBaseTool(Tool):
    """List available knowledge base files."""
    
    name = "list_knowledge_base"
    description = "List available knowledge base files."
    
    inputs = {}
    output_type = "string"
    
    def __init__(self, kb_root: Optional[Path], usage_callback: Optional[Callable] = None):
        super().__init__()
        self.kb_root = kb_root
        self.usage_callback = usage_callback
    
    def forward(self) -> str:
        if self.usage_callback:
            self.usage_callback("list_knowledge_base")
        if not self.kb_root or not self.kb_root.exists():
            return "Knowledge Base not found or not configured."
        return "\n".join(f.name for f in self.kb_root.glob("*.md"))


class ReadKnowledgeBaseFileTool(Tool):
    """Read KB file by name."""
    
    name = "read_knowledge_base_file"
    description = "Read KB file by name."
    
    inputs = {
        "filename": {"type": "string", "description": "KB file name (e.g., 'api.md')."},
    }
    output_type = "string"
    
    def __init__(self, kb_root: Optional[Path], usage_callback: Optional[Callable] = None):
        super().__init__()
        self.kb_root = kb_root
        self.usage_callback = usage_callback
    
    def forward(self, filename: str) -> str:
        if self.usage_callback:
            self.usage_callback("read_knowledge_base_file")
        if not self.kb_root:
             return "Knowledge Base not configured."
        
        target = self.kb_root / filename
        if not target.exists():
            return "File not found in Knowledge Base."
        
        return target.read_text(encoding="utf-8")


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
    allow_kb_read: bool = False,
    knowledge_base_root: str | None = None,
) -> List[Tool]:
    """Create Smolagents tools bound to the provided codebase and workspace roots."""

    codebase_root_path = Path(codebase_root).expanduser().resolve()
    workspace_root_path = ensure_directory(workspace_root)
    kb_root_path = Path(knowledge_base_root).resolve() if knowledge_base_root else None

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
    if allow_kb_read:
        tools.append(ListKnowledgeBaseTool(kb_root_path, usage_callback))
        tools.append(ReadKnowledgeBaseFileTool(kb_root_path, usage_callback))

    return tools
