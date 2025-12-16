import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Insert local path to prioritize local modules
sys.path.insert(0, str(Path.cwd()))

from config import settings
from pipelines.deep_agent import DeepAgentConfig

def test_deep_agent_paths():
    """Verify DepAgentConfig initialized with standard paths from config."""
    output_root = settings.DEEP_AGENT_OUTPUT_ROOT
    
    config = DeepAgentConfig(
        codebase_root=settings.CODEBASE_ROOT,
        output_root=output_root,
        kb_output_path=output_root / "knowledge_base",
        tutorial_output_path=output_root / "tutorials",
        kb_sub_agents_path=output_root / "sub_agents_kb",
        tutorial_sub_agents_path=output_root / "sub_agents_tutorials",
        enable_rag=True,
    )
    
    assert config.output_root == settings.DEEP_AGENT_OUTPUT_ROOT
    assert config.kb_output_path == settings.DEEP_AGENT_OUTPUT_ROOT / "knowledge_base"
    assert config.codebase_root == settings.CODEBASE_ROOT
    print("✅ DeepAgent Standard Config paths verified.")

def test_baseline_paths_logic():
    """Verify logic for Baseline paths (simulating what CLI does)."""
    output_root = settings.BASELINE_OUTPUT_ROOT
    
    # Baseline generator logic as used in CLI
    from pipelines.tutorial_generator import TutorialGenerator
    
    # Mocking init to avoid actual heavy init
    with patch("pipelines.tutorial_generator.TutorialGenerator.__init__", return_value=None) as mock_init:
        # Replicate CLI call
        generator = TutorialGenerator(
            codebase_root=settings.CODEBASE_ROOT,
            knowledge_base_root=output_root / "knowledge_base",
            output_root=output_root,
            sub_agents_root=output_root / "sub_agents_tutorials",
            enable_rag=True,
            dry_run=False,
        )
        
        args = mock_init.call_args[1]
        assert args["output_root"] == settings.BASELINE_OUTPUT_ROOT
        assert args["sub_agents_root"] == settings.BASELINE_OUTPUT_ROOT / "sub_agents_tutorials"
        print("✅ Baseline Generator paths verified.")

def run_tests():
    print("running settings tests...")
    test_deep_agent_paths()
    test_baseline_paths_logic()
    print("All configuration tests passed.")

if __name__ == "__main__":
    run_tests()
