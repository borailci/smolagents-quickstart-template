"""Shared constants for filesystem filtering across toolkits."""

from __future__ import annotations

from typing import FrozenSet

__all__ = ["IGNORED_DIRS", "ALLOWED_SUFFIXES", "BLOCKED_EXTENSIONS", "MAX_FILE_SIZE_BYTES", "IGNORED_FILES"]


# Directories to skip during file traversal
IGNORED_DIRS: FrozenSet[str] = frozenset({
    "__pycache__",
    "node_modules",
    "venv",
    "env",
    ".venv",
    ".git",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "target",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "eggs",
    "*.egg-info",
})

# File extensions allowed for text processing
ALLOWED_SUFFIXES: FrozenSet[str] = frozenset({
    # Python
    ".py",
    ".pyi",
    # Web
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".vue",
    ".svelte",
    # Config/Data
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
    ".env.example",
    # Documentation
    ".md",
    ".txt",
    ".rst",
    # Shell
    ".sh",
    ".bash",
    ".zsh",
    # Database
    ".sql",
    # Other languages
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
})

# Binary extensions to block from reading
BLOCKED_EXTENSIONS: FrozenSet[str] = frozenset({
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".exe",
    ".bin",
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
})

# Maximum file size for processing (100KB)
MAX_FILE_SIZE_BYTES: int = 100_000

# Specific files to ignore during indexing
IGNORED_FILES: FrozenSet[str] = frozenset({
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    "uv.lock",
    "LICENSE",
    "LICENSE.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
})
