
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY
import pytest

sys.path.insert(0, str(Path.cwd()))

from pipelines.tutorial_generator import TutorialGenerator


@pytest.fixture
def mock_dirs(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    code = tmp_path / "code"
    code.mkdir()
    sub_agents = tmp_path / "sub_agents"
    sub_agents.mkdir()
    return code, kb, out, sub_agents

def test_init_sets_paths_correctly(mock_dirs):
    code, kb, out, sub = mock_dirs
    gen = TutorialGenerator(
        codebase_root=code,
        knowledge_base_root=kb,
        output_root=out,
        sub_agents_root=sub
    )
    assert gen.codebase_root == code
    assert gen.knowledge_base_root == kb
    assert gen.output_root == out
    assert gen.sub_agents_root == sub

def test_generate_baseline_uses_baseline_supervisor(mock_dirs):
    code, kb, out, sub = mock_dirs
    gen = TutorialGenerator(
        codebase_root=code,
        knowledge_base_root=kb,
        output_root=out,
        sub_agents_root=sub
    )
    
    # Mock the internal creator method
    mock_agent = MagicMock()
    mock_agent.run.return_value = "Baseline Task Done"
    
    with patch.object(gen, "_create_baseline_supervisor_agent", return_value=mock_agent) as mock_create:
            gen.generate_baseline_with_supervisor()
            
            mock_create.assert_called_once()
            mock_agent.run.assert_called_once()

def test_create_supervisor_tools_injection(mock_dirs):
    """Verify that build_tutorial_supervisor_tools is called with correct args."""
    code, kb, out, sub = mock_dirs
    gen = TutorialGenerator(
        codebase_root=code,
        knowledge_base_root=kb,
        output_root=out,
        sub_agents_root=sub
    )
    
    with patch("pipelines.tutorial_generator.build_tutorial_supervisor_tools") as mock_build_tools:
        with patch("utils.llm_factory.create_model"):
             with patch("smolagents.ToolCallingAgent"):
                gen._create_supervisor_agent()
                
                mock_build_tools.assert_called_once_with(
                    codebase_root=code,
                    sub_agents_root=sub,
                    output_root=out,
                    knowledge_base_root=kb,
                    metrics=None
                )
