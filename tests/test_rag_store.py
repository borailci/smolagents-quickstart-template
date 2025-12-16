from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from toolkits.rag_store import SimpleChromaRAGStore


def _stub_embedding(texts: Iterable[str]) -> Sequence[Sequence[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        lowered = text.lower()
        api_score = float(lowered.count("api"))
        project_score = float(lowered.count("project"))
        length_score = float(len(text))
        vectors.append([api_score, project_score, length_score])
    return vectors


def test_rag_store_returns_semantic_snippets(tmp_path: Path) -> None:
    code_root = tmp_path / "code"
    kb_root = tmp_path / "kb"
    persist_dir = tmp_path / "rag"
    code_root.mkdir()
    kb_root.mkdir()

    (code_root / "api.py").write_text(
        '''
from fastapi import APIRouter

router = APIRouter()

@router.post("/projects")
def create_project():
    """Create a project via API endpoint"""
    return {"status": "ok"}
'''.strip(),
        encoding="utf-8",
    )

    (kb_root / "projects.md").write_text(
        """
# Projects Overview

Project creation flows through the HTTP API and validates input before storing it.
""".strip(),
        encoding="utf-8",
    )

    store = SimpleChromaRAGStore(
        codebase_root=code_root,
        knowledge_base_root=kb_root,
        persist_directory=persist_dir,
        embedding_fn=_stub_embedding,
    )
    store.ensure_index(force_rebuild=True)

    results = store.query(
        "How are projects created through the API?",
        top_k=3,
        include_codebase=True,
        include_knowledge_base=True,
    )

    assert results, "RAG query should return at least one snippet"
    assert results, "RAG query should return at least one snippet"
    # Result is a list of strings now, e.g. "[KNOWLEDGE_BASE] projects.md:1\n# Projects Overview..."
    # We verify presence of expected content
    combined_results = "\\n".join(results)
    assert "projects.md" in combined_results
    assert "# Projects Overview" in combined_results
    assert "[KNOWLEDGE_BASE]" in combined_results
    assert "[CODEBASE]" in combined_results
