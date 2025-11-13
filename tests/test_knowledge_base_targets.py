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
    for relative in ("src/api", "src/config", "src/models", "src/utils", "tests"):
        (codebase_root / relative).mkdir(parents=True)

    output_root = tmp_path / "knowledge_base"
    sub_agents_root = tmp_path / "agents"
    return codebase_root, output_root, sub_agents_root


def _build_builder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> KnowledgeBaseBuilder:
    codebase_root, output_root, sub_agents_root = _setup_repo(tmp_path)
    monkeypatch.setenv("CODEBASE_ROOT_PATH", str(codebase_root))
    monkeypatch.setenv("KNOWLEDGE_BASE_OUTPUT_PATH", str(output_root))
    monkeypatch.setenv("SUB_AGENTS_ROOT_PATH", str(sub_agents_root))
    monkeypatch.delenv(TARGET_WHITELIST_ENV, raising=False)
    monkeypatch.delenv("KNOWLEDGE_BASE_MAX_CONCURRENT_AGENTS", raising=False)
    return KnowledgeBaseBuilder()


def test_discover_targets_uses_curated_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _build_builder(tmp_path, monkeypatch)
    targets = builder._discover_targets()
    discovered = [target.path.as_posix() for target in targets]
    assert discovered == list(DEFAULT_TARGET_IDENTIFIERS)


def test_discover_targets_honours_whitelist_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codebase_root, output_root, sub_agents_root = _setup_repo(tmp_path)
    (codebase_root / "docs").mkdir()

    monkeypatch.setenv("CODEBASE_ROOT_PATH", str(codebase_root))
    monkeypatch.setenv("KNOWLEDGE_BASE_OUTPUT_PATH", str(output_root))
    monkeypatch.setenv("SUB_AGENTS_ROOT_PATH", str(sub_agents_root))
    monkeypatch.setenv(TARGET_WHITELIST_ENV, "src/api, docs")

    builder = KnowledgeBaseBuilder()
    targets = builder._discover_targets()
    discovered = [target.path.as_posix() for target in targets]
    assert discovered == ["src/api", "docs"]


def test_exploratory_pass_writes_scouting_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = _build_builder(tmp_path, monkeypatch)

    report_path = builder._run_exploratory_pass()

    assert report_path is not None
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert "# Exploratory Scouting Report" in content
    assert "utils/" in content
    assert "README.md" in content
