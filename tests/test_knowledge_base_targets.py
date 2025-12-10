from __future__ import annotations

from pathlib import Path

import pytest

from pipelines.knowledge_base_builder import (
    DEFAULT_TARGET_IDENTIFIERS,
    TARGET_WHITELIST_ENV,
    KnowledgeBaseBuilder,
)


def _setup_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    codebase_root = tmp_path / "repo"
    codebase_root.mkdir()

    # Create default files/directories expected by the curated list.
    (codebase_root / "README.md").write_text("Project overview", encoding="utf-8")
    # Support both src/ and app/ directory structures in defaults
    for relative in ("src/api", "src/config", "src/models", "src/utils", "app/api", "app/models", "tests", "scripts"):
        (codebase_root / relative).mkdir(parents=True)

    output_root = tmp_path / "knowledge_base"
    sub_agents_root = tmp_path / "agents"
    return codebase_root, output_root, sub_agents_root


def _build_builder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> KnowledgeBaseBuilder:
    codebase_root, output_root, sub_agents_root = _setup_repo(tmp_path)
    # Pass paths explicitly to avoid stale settings singleton issues
    return KnowledgeBaseBuilder(
        codebase_root=codebase_root,
        output_root=output_root,
        sub_agents_root=sub_agents_root,
    )


def test_discover_targets_uses_curated_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _build_builder(tmp_path, monkeypatch)
    targets = builder._fallback_target_selection()
    
    discovered = {target.path.as_posix() for target in targets}
    
    # src/api is in DEFAULT_TARGET_IDENTIFIERS and created in _setup_repo
    assert "src/api" in discovered
    assert "README.md" in discovered


def test_discovery_finds_extra_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codebase_root, output_root, sub_agents_root = _setup_repo(tmp_path)
    (codebase_root / "docs").mkdir()
    
    # Explicitly pass paths and higher max_targets to ensure 'docs' isn't capped out
    builder = KnowledgeBaseBuilder(
        codebase_root=codebase_root,
        output_root=output_root,
        sub_agents_root=sub_agents_root,
        max_targets=50
    )
    targets = builder._fallback_target_selection()
    discovered = {target.path.as_posix() for target in targets}
    
    # Docs should be discovered because it is a top level dir in iterdir() logic
    assert "docs" in discovered
    # src/api should be discovered because it is in defaults
    assert "src/api" in discovered


def test_exploratory_pass_writes_scouting_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _build_builder(tmp_path, monkeypatch)

    report_path, context_summary = builder._run_exploratory_pass()

    assert report_path is not None
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert "# Exploratory Scouting Report" in content
    # src/utils is created in _setup_repo, so "utils" should appear in tree
    assert "utils" in content
    assert "README.md" in content
    assert context_summary
