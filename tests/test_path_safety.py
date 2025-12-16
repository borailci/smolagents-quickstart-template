
import os
import pytest
from pathlib import Path
from utils.path_utils import resolve_within_root, PathTraversalError

@pytest.fixture
def temp_roots(tmp_path):
    """Create a temporary directory structure for testing."""
    # Structure:
    # /root
    #   /safe_dir
    #     file.txt
    #   outside.txt
    
    root = tmp_path / "root"
    root.mkdir()
    
    safe_dir = root / "safe_dir"
    safe_dir.mkdir()
    
    (safe_dir / "file.txt").touch()
    (root / "outside.txt").touch()
    
    return root, safe_dir

def test_valid_path_resolution(temp_roots):
    """Test resolving a normal file within the root."""
    root, safe_dir = temp_roots
    resolved = resolve_within_root(root, "safe_dir/file.txt")
    assert resolved == safe_dir / "file.txt"

def test_resolve_root_itself(temp_roots):
    """Test that resolving the root itself is allowed."""
    root, _ = temp_roots
    resolved = resolve_within_root(root, ".")
    assert resolved == root

def test_path_traversal_simple_dot_dot(temp_roots):
    """Test that ../ attempts raise PathTraversalError."""
    root, _ = temp_roots
    # Try to go up from root
    with pytest.raises(PathTraversalError):
        resolve_within_root(root, "../outside_world")

def test_path_traversal_nested_dot_dot(temp_roots):
    """Test nested traversal attempts."""
    root, safe_dir = temp_roots
    # "safe_dir/../../" effectively tries to go above root
    with pytest.raises(PathTraversalError):
        resolve_within_root(root, "safe_dir/../../root_sibling")

def test_absolute_path_escape(temp_roots):
    """Test that providing an absolute path outside root fails."""
    root, _ = temp_roots
    # Depending on OS, this might look different, but usually /tmp or /etc
    # We use a completely separate tmp path
    outside_path = Path("/tmp/evil_file")
    
    # Resolving an absolute path that is NOT inside root should fail
    # Note: `resolve_within_root` implementation treats absolute inputs by appending/checking
    # or if the function allows absolute paths if they are inside.
    # Let's check the implementation behavior in utils/path_utils.py:
    # candidate = (base / requested_path).resolve() 
    # If requested_path is absolute, pathlib's / operator replaces the base! 
    # So valid implementation MUST handle this or the test will show the vulnerability.
    
    # Attempting to verify robust handling of absolute inputs:
    with pytest.raises(PathTraversalError):
        resolve_within_root(root, "/etc/passwd")

def test_symlink_attack(temp_roots):
    """Test behavior with symlinks pointing outside (if filesystem supports it)."""
    root, safe_dir = temp_roots
    target = root.parent / "sensitive.txt"
    target.touch()
    
    link_path = safe_dir / "link_to_outside"
    try:
        os.symlink(target, link_path)
    except OSError:
        pytest.skip("Symlinks not supported on this OS/filesystem")

    # If we resolve the link, strictly it points outside. 
    # Whether we allow this depends on policy. 
    # Standard secure implementation should resolve the link and check the final path.
    with pytest.raises(PathTraversalError):
        resolve_within_root(root, "safe_dir/link_to_outside")
