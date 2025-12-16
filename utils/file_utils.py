"""Shared file reading utilities to avoid duplication across toolkits."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

__all__ = ["read_text_file_truncated", "DEFAULT_MAX_LINES"]

DEFAULT_MAX_LINES = 500


def read_text_file_truncated(
    path: Path,
    *,
    start_line: int = 1,
    end_line: Optional[int] = None,
    max_lines: int = DEFAULT_MAX_LINES,
) -> str:
    """
    Read a text file with line-based truncation.
    
    Args:
        path: Path to the file.
        start_line: 1-indexed line to start reading from.
        end_line: Optional 1-indexed line to stop at (inclusive).
        max_lines: Maximum lines to read if end_line not specified.
    
    Returns:
        File content as string, potentially truncated.
    
    Raises:
        ValueError: If file is not UTF-8 decodable.
        FileNotFoundError: If file doesn't exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"File '{path}' does not exist.")
    
    if not path.is_file():
        raise ValueError(f"Path '{path}' is not a file.")
    
    start = max(1, start_line)
    stop = end_line if end_line and end_line >= start else start + max_lines - 1
    
    lines: List[str] = []
    truncated = False
    
    try:
        with path.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle, start=1):
                if idx < start:
                    continue
                if idx > stop:
                    truncated = True
                    break
                lines.append(line)
    except UnicodeDecodeError as exc:
        raise ValueError(f"File '{path.name}' is not UTF-8 decodable.") from exc
    
    result = "".join(lines)
    if truncated:
        result += f"\n... [Truncated after {len(lines)} lines] ..."
    
    return result
