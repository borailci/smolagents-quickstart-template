"""Utilities for safely resolving file system paths within scoped roots."""

from __future__ import annotations

import os
from pathlib import Path


class PathTraversalError(ValueError):
    """Raised when a requested path escapes the allowed root."""


def resolve_within_root(
    base_path: str | os.PathLike[str], requested_path: str | os.PathLike[str]
) -> Path:
    """Resolve a requested path relative to a base path while preventing traversal.

    Args:
        base_path: Root directory that bounds access.
        requested_path: Relative or absolute path provided by an agent.

    Returns:
        Canonical absolute Path guaranteed to stay within base_path.

    Raises:
        PathTraversalError: If the resolved path is outside of base_path.
    """

    base = Path(base_path).expanduser().resolve()
    candidate = (base / requested_path).resolve()

    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise PathTraversalError(f"Path traversal detected: {requested_path}") from exc

    return candidate


def ensure_directory(path: str | os.PathLike[str]) -> Path:
    """Ensure that a directory exists and return it as a Path."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
