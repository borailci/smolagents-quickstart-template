
import pytest
from pathlib import Path
import tempfile
import shutil
from toolkits.scoped_filesystem_toolkit import resolve_within_root, ensure_directory, build_scoped_tools

class TestScopedSecurity:
    @pytest.fixture
    def workspace(self):
        """Creates a temporary workspace structure."""
        tmp_dir = Path(tempfile.mkdtemp())
        
        # Structure:
        # /tmp/root
        #   /codebase (Read-only)
        #   /agent_ws (Read-write)
        #   /forbidden (No access)
        
        codebase = tmp_dir / "codebase"
        agent_ws = tmp_dir / "agent_ws"
        forbidden = tmp_dir / "forbidden"
        
        codebase.mkdir()
        agent_ws.mkdir()
        forbidden.mkdir()
        
        (codebase / "source.py").write_text("print('source')")
        (forbidden / "secret.txt").write_text("secret")
        
        yield {
            "root": tmp_dir,
            "codebase": codebase,
            "agent_ws": agent_ws,
            "forbidden": forbidden
        }
        
        shutil.rmtree(tmp_dir)

    def test_resolve_within_root_valid(self, workspace):
        """Test resolving valid paths within root."""
        root = workspace["codebase"]
        path = resolve_within_root(root, "source.py")
        assert path.resolve() == (root / "source.py").resolve()

    def test_resolve_within_root_traversal(self, workspace):
        """Test blocking path traversal attacks."""
        root = workspace["codebase"]
        
        # Attack: Try to access forbidden folder via ../
        with pytest.raises(ValueError, match="Path traversal detected"):
            resolve_within_root(root, "../forbidden/secret.txt")

    def test_scoped_tools_read_access(self, workspace):
        """Test read_codebase_file tool permissions."""
        tools = build_scoped_tools(
            workspace_root=str(workspace["agent_ws"]),
            codebase_root=str(workspace["codebase"])
        )
        read_tool = next(t for t in tools if t.name == "read_codebase_file")
        
        # Valid read
        content = read_tool("source.py")
        assert "print('source')" in content
        
        # Traversal read (should fail)
        try:
            read_tool("../forbidden/secret.txt")
            assert False, "Should have raised ValueError"
        except Exception as e:
            assert "Path traversal detected" in str(e)

    def test_scoped_tools_write_isolation(self, workspace):
        """Test write_workspace_file tool permissions."""
        tools = build_scoped_tools(
            workspace_root=str(workspace["agent_ws"]),
            codebase_root=str(workspace["codebase"])
        )

        write_tool = next(t for t in tools if t.name == "write_workspace_file")
        # Valid write
        write_tool("output.md", "# Valid content that is definitely longer than 50 characters to pass the check.")
        assert (workspace["agent_ws"] / "output.md").exists()
        
        # Write to codebase (should fail - only workspace is writable)
        try:
            write_tool("../codebase/evil.py", "import os # strict length check requires this to be longer to test path isolation properly.")
            assert False, "Should have raised ValueError"
        except Exception as e:
            assert "Path traversal detected" in str(e) or "is outside" in str(e)
