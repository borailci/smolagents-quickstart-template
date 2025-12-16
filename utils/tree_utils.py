"""Shared directory tree utilities to avoid duplication across toolkits."""

from __future__ import annotations

from pathlib import Path
from typing import List, Set

from utils.constants import IGNORED_DIRS

__all__ = ["build_directory_tree", "is_safe_entry", "DEFAULT_MAX_DEPTH", "DEFAULT_MAX_ITEMS"]

DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_ITEMS = 200


def is_safe_entry(entry: Path, ignored_dirs: Set[str] | None = None) -> bool:
    """Check if a directory entry should be included in listings."""
    if ignored_dirs is None:
        ignored_dirs = IGNORED_DIRS
    return not entry.name.startswith(".") and entry.name not in ignored_dirs


def build_directory_tree(
    root: Path,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_items: int = DEFAULT_MAX_ITEMS,
    prefix: str = "",
    current_depth: int = 0,
    _lines: List[str] | None = None,
) -> List[str]:
    """
    Build a tree representation of a directory.
    
    Args:
        root: Directory to build tree for.
        max_depth: Maximum depth to traverse.
        max_items: Maximum items to include.
        prefix: Current prefix for tree formatting.
        current_depth: Current depth (internal use).
        _lines: Accumulated lines (internal use).
    
    Returns:
        List of formatted tree lines.
    """
    if _lines is None:
        _lines = [f"{root.name}/"]
    
    if current_depth >= max_depth or len(_lines) >= max_items:
        return _lines
    
    try:
        entries = sorted(
            e for e in root.iterdir() if is_safe_entry(e)
        )
    except PermissionError:
        _lines.append(f"{prefix}[permission denied]")
        return _lines
    
    for i, entry in enumerate(entries):
        if len(_lines) >= max_items:
            _lines.append(f"{prefix}... (truncated)")
            break
            
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        child_prefix = "    " if is_last else "│   "
        
        if entry.is_dir():
            _lines.append(f"{prefix}{connector}{entry.name}/")
            if current_depth + 1 < max_depth:
                build_directory_tree(
                    entry,
                    max_depth=max_depth,
                    max_items=max_items,
                    prefix=prefix + child_prefix,
                    current_depth=current_depth + 1,
                    _lines=_lines,
                )
        else:
            _lines.append(f"{prefix}{connector}{entry.name}")
    
    return _lines


def format_tree_as_string(lines: List[str]) -> str:
    """Format tree lines as a markdown code block."""
    return "```\n" + "\n".join(lines) + "\n```"
