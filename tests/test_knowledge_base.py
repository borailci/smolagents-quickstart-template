
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY
import pytest

# Insert local path to prioritize local modules
sys.path.insert(0, str(Path.cwd()))

from pipelines.knowledge_base_builder import KnowledgeBaseBuilder
from pipelines.types import DocumentationTarget, AgentWorkspaceResult

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr("config.settings.CODEBASE_ROOT", Path("/tmp/codebase"))
    monkeypatch.setattr("config.settings.KNOWLEDGE_BASE_OUTPUT", Path("/tmp/kb_output"))
    monkeypatch.setattr("config.settings.SUB_AGENTS_ROOT", Path("/tmp/sub_agents"))
    monkeypatch.setattr("config.settings.TUTORIAL_OUTPUT", Path("/tmp/tutorial_output"))
    monkeypatch.setenv("LITELLM_MODEL_ID", "dummy")
    monkeypatch.setenv("LITELLM_API_KEY", "dummy")

@pytest.fixture
def mock_checkpoint_runner():
    with patch("pipelines.knowledge_base_builder.CheckpointedPipelineRunner") as MockRunner:
        runner_instance = MockRunner.return_value
        # Default checkpoint state
        runner_instance.checkpoint.phase = "initialized"
        runner_instance.checkpoint.kb_completed_targets = []
        yield runner_instance

@pytest.fixture
def kb_builder(mock_settings, mock_checkpoint_runner):
    return KnowledgeBaseBuilder(
        codebase_root=Path("/tmp/codebase"),
        output_root=Path("/tmp/kb_output"),
        dry_run=False
    )

def test_generate_with_supervisor_resumes_completed(kb_builder, mock_checkpoint_runner):
    """Test that it returns early if phase is already kb_completed."""
    mock_checkpoint_runner.checkpoint.phase = "kb_completed"
    
    # Mock glob to return some fake files
    with patch.object(Path, "glob", return_value=[Path("file1.md")]):
        result = kb_builder.generate_with_supervisor()
    
    assert len(result) == 1
    with patch.object(kb_builder, "_create_supervisor_agent") as mock_create:
        result = kb_builder.generate_with_supervisor()
        assert not mock_create.called

def test_generate_with_supervisor_runs_happy_path(kb_builder, mock_checkpoint_runner):
    """Test normal execution flow."""
    
    # Mock supervisor agent
    mock_agent = MagicMock()
    mock_agent.run.return_value = "Task Completed"
    
    with patch.object(kb_builder, "_create_supervisor_agent", return_value=mock_agent):
        with patch.object(kb_builder, "_collect_from_sub_agents") as mock_collect:
            with patch.object(kb_builder, "_run_summary_agent", return_value=Path("summary.md")) as mock_summary:
                
                # Mock file system ops
                with patch.object(Path, "mkdir"):
                    # Mock glob to return files so summary runs
                    with patch.object(Path, "glob", side_effect=[[], [Path("kv.md")]]): # First glob (resume check), Second glob (collection)
                         # Actually generate_with_supervisor calls glob multiple times.
                         # 1. Check existing (before spawn)
                         # 2. Check completed (resume logic)
                         # 3. Collect from sub agents (if needed) -> glob again
                         # Let's just make it return a file eventually
                         
                         # Simpler: Mock glob to always return [Path("file.md")] 
                         # But wait, if it returns files early, it triggers RESUME logic.
                         # We want HAPPY path (it runs supervisor).
                        
                         # If checking completed targets returns [], it runs.
                         
                         # Best approach: Mock glob to return empty first, then files later.
                         # But glob is called on output_root.
                                              # Simpler robust test: If files exist at any point, summary should run.
                         # We return files immediately (or after resume check doesn't matter too much for happy path summary check)
                         # But if we return files immediately, resume logic might skip supervisor or update prompt.
                         # Let's return empty, then files.
                         
                         with patch.object(Path, "glob", side_effect=[[], [Path("kb.md")], [Path("kb.md")]]):
                            kb_builder.generate_with_supervisor()
    
    # Check checkpoint phase update
    mock_checkpoint_runner.set_phase.assert_any_call("kb_generation")
    
    # Check supervisor run
    mock_agent.run.assert_called_once()
    
    # Check summary ran
    mock_summary.assert_called_once()
    
    # Final phase update
    mock_checkpoint_runner.set_phase.assert_any_call("kb_completed")

def test_generate_with_supervisor_retries_on_rate_limit(kb_builder, mock_checkpoint_runner):
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

def test_force_rebuild_resets_checkpoint(mock_settings):
    """Test that force_rebuild re-initializes checkpoint."""
    
    with patch("pipelines.knowledge_base_builder.CheckpointedPipelineRunner") as MockRunner:
        mock_reset = MagicMock()
        MockRunner.return_value.reset = mock_reset
        
        builder = KnowledgeBaseBuilder(force_rebuild=True)
        
        # We need to spy on the constructor call during generate_with_supervisor
        # because it re-instantiates CheckpointedPipelineRunner if forced
        
        with patch.object(builder, "_reset_directory"):
            with patch.object(builder, "_clear_rag_vector_store"):
                with patch.object(Path, "mkdir"):
                     # Mock _create_supervisor to avoid deeper calls
                    with patch.object(builder, "_create_supervisor_agent", return_value=MagicMock()):
                        with patch.object(builder, "_collect_from_sub_agents"):
                             with patch.object(builder, "_run_summary_agent"):
                                builder.generate_with_supervisor()
        
        # Expect CheckpointedPipelineRunner to be called again with force_rebuild=True
        # Access the class mock to check instantiation calls
        assert MockRunner.call_count >= 2 # Once in __init__, once in generate
        
        # Verify the LAST call had force_rebuild=True
        _, kwargs = MockRunner.call_args_list[-1]
        assert kwargs.get("force_rebuild") is True
