from __future__ import annotations

from pathlib import Path

import pytest

from pipelines.tutorial_generator import TutorialGenerator, TutorialOutlineItem


def _setup_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[TutorialGenerator, TutorialOutlineItem]:
    codebase_root = tmp_path / "repo"
    knowledge_base_root = tmp_path / "kb"
    output_root = tmp_path / "out"

    (codebase_root / "src").mkdir(parents=True)
    (codebase_root / "src" / "app.py").write_text(
        """def main():\n    pass\n# TODO: investigate rag search\n""",
        encoding="utf-8",
    )

    knowledge_base_root.mkdir(parents=True)
    (knowledge_base_root / "overview.md").write_text(
        "# Overview\n\nThis repository supports optional RAG helpers.",
        encoding="utf-8",
    )

    monkeypatch.setenv("LITELLM_MODEL_ID", "dummy-model")
    monkeypatch.setenv("LITELLM_API_KEY", "dummy-key")

    outline_item = TutorialOutlineItem(
        filename="01_test.md",
        title="Test Tutorial",
        description="Demonstrate optional helpers.",
    )

    generator = TutorialGenerator(
        codebase_root=codebase_root,
        knowledge_base_root=knowledge_base_root,
        output_root=output_root,
        outline=(outline_item,),
        enable_rag=True,
        rag_max_snippets=2,
    )

    return generator, outline_item


def test_prepare_state_includes_optional_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    generator, _ = _setup_env(tmp_path, monkeypatch)

    prepared = generator._prepare_tutorial_state({})
    tool_names = {tool.name for tool in prepared["tools"]}

    # When RAG is enabled, retrieve_relevant_context should be available
    assert "retrieve_relevant_context" in tool_names
    # Core tools should always be present
    assert "read_file" in tool_names
    assert "list_knowledge_base" in tool_names
    assert "read_knowledge_base_file" in tool_names


def test_optional_guidance_in_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    generator, outline_item = _setup_env(tmp_path, monkeypatch)

    task = generator._build_tutorial_task(
        outline_item,
        kb_summary="KB",
        style_guidance="Style",
        outline_brief="Brief",
        codebase_context="Context",
    )

    # Check that KB context is properly injected into task
    assert "Knowledge Base Context" in task
    assert "USE THIS FIRST" in task
    # Check that outline item details are included
    assert outline_item.title in task
    assert outline_item.filename in task


def test_disabled_helpers_omit_guidance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codebase_root = tmp_path / "repo"
    knowledge_base_root = tmp_path / "kb"
    output_root = tmp_path / "out"

    codebase_root.mkdir(parents=True)
    knowledge_base_root.mkdir(parents=True)
    (knowledge_base_root / "overview.md").write_text(
        "Placeholder",
        encoding="utf-8",
    )

    monkeypatch.setenv("LITELLM_MODEL_ID", "dummy-model")
    monkeypatch.setenv("LITELLM_API_KEY", "dummy-key")

    outline_item = TutorialOutlineItem(
        filename="01_test.md",
        title="Test",
        description="Desc",
    )

    generator = TutorialGenerator(
        codebase_root=codebase_root,
        knowledge_base_root=knowledge_base_root,
        output_root=output_root,
        outline=(outline_item,),
        enable_rag=False,
    )

    task = generator._build_tutorial_task(
        outline_item,
        kb_summary="KB",
        style_guidance="Style",
        outline_brief="Brief",
        codebase_context="Context",
    )

    assert "grep_codebase" not in task
    assert "retrieve_relevant_context" not in task
