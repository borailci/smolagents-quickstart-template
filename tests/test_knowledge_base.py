
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY
import pytest

# Insert local path to prioritize local modules
sys.path.insert(0, str(Path.cwd()))

from pipelines.knowledge_base_builder import KnowledgeBaseBuilder



@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr("config.settings.CODEBASE_ROOT", Path("/tmp/codebase"))
    monkeypatch.setattr("config.settings.KNOWLEDGE_BASE_OUTPUT", Path("/tmp/kb_output"))
    monkeypatch.setattr("config.settings.SUB_AGENTS_ROOT", Path("/tmp/sub_agents"))
    monkeypatch.setattr("config.settings.TUTORIAL_OUTPUT", Path("/tmp/tutorial_output"))
    monkeypatch.setenv("LITELLM_MODEL_ID", "dummy")
    monkeypatch.setenv("LITELLM_API_KEY", "dummy")

@pytest.fixture
def kb_builder(mock_settings):
    return KnowledgeBaseBuilder(
        codebase_root=Path("/tmp/codebase"),
        output_root=Path("/tmp/kb_output"),
        dry_run=False
    )

def test_generate_with_supervisor_runs_happy_path(kb_builder):
    """Test normal execution flow."""
    
    # Mock supervisor agent
    mock_agent = MagicMock()
    mock_agent.run.return_value = "Task Completed"
    
    with patch.object(kb_builder, "_create_supervisor_agent", return_value=mock_agent):
        with patch.object(kb_builder, "_collect_from_sub_agents") as mock_collect:
            with patch.object(kb_builder, "_run_summary_agent", return_value=Path("summary.md")) as mock_summary:
                
                # Mock file system ops
                with patch.object(Path, "mkdir"):
                    # Mock glob to return files
                    with patch.object(Path, "glob", side_effect=[[], [Path("kb.md")], [Path("kb.md")]]):
                        kb_builder.generate_with_supervisor()
    
    # Check supervisor run
    mock_agent.run.assert_called_once()
    
    # Check summary ran
    mock_summary.assert_called_once()

def test_generate_with_supervisor_retries_on_rate_limit(kb_builder):
    """Test retry logic on rate limit exception."""
    
    mock_agent = MagicMock()
    # Fail once with rate limit, then succeed
    mock_agent.run.side_effect = [
        RuntimeError("429 Resource exhausted"),
        "Success"
    ]
    
    with patch.object(kb_builder, "_create_supervisor_agent", return_value=mock_agent):
        with patch.object(kb_builder, "_collect_from_sub_agents"):
            with patch.object(kb_builder, "_run_summary_agent"):
                with patch.object(Path, "mkdir"):
                    with patch("time.sleep") as mock_sleep: # Don't actually sleep
                        kb_builder.generate_with_supervisor()
    
    assert mock_agent.run.call_count == 2
    mock_sleep.assert_called_once()
 

def test_force_rebuild_clears_directories(mock_settings):
    """Test that force_rebuild checks for directory reset."""
    
    # We construct the builder with force_rebuild=True
    builder = KnowledgeBaseBuilder(force_rebuild=True, dry_run=False)
    
    with patch.object(builder, "_reset_directory") as mock_reset:
        with patch.object(builder, "_clear_rag_vector_store"):
            with patch.object(Path, "mkdir"):
                 with patch.object(builder, "_create_supervisor_agent", return_value=MagicMock()):
                    with patch.object(builder, "_collect_from_sub_agents"):
                         with patch.object(builder, "_run_summary_agent"):
                            builder.generate_with_supervisor()
    
    # Verify _reset_directory was called for sub_agents_root and output_root
    assert mock_reset.call_count == 2

