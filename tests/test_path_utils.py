from pathlib import Path

import pytest

from utils.path_utils import PathTraversalError, ensure_directory, resolve_within_root


def test_resolve_within_root_allows_nested_paths(tmp_path: Path) -> None:
    target = tmp_path / "workspace"
    ensure_directory(target)

    nested = resolve_within_root(target, "subdir/file.txt")

    assert nested == target / "subdir" / "file.txt"


def test_resolve_within_root_blocks_traversal(tmp_path: Path) -> None:
    target = tmp_path / "workspace"
    ensure_directory(target)

    with pytest.raises(PathTraversalError):
        resolve_within_root(target, "../escape.txt")


def test_ensure_directory_creates_path(tmp_path: Path) -> None:
    directory = tmp_path / "nested" / "leaf"

    created = ensure_directory(directory)

    assert created.exists()
    assert created.is_dir()
