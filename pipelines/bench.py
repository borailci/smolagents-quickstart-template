"""Benchmark runner for baseline vs deep+KB tutorial pipelines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List

from loguru import logger

from pipelines.knowledge_base_builder import KnowledgeBaseBuilder
from pipelines.tutorial_generator import TutorialGenerator, TutorialRunMetrics
from utils.path_utils import ensure_directory

DEFAULT_BENCH_ROOT = Path("data/bench").expanduser().resolve()


@dataclass
class BenchRunResult:
    codebase: Path
    variant: str
    tutorial_outputs: List[Path]
    metrics: TutorialRunMetrics
    error: str | None = None
    knowledge_base_outputs: List[Path] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "codebase": str(self.codebase),
            "variant": self.variant,
            "tutorial_outputs": [str(p) for p in self.tutorial_outputs],
            "metrics": self.metrics.to_dict(),
            "error": self.error,
            "knowledge_base_outputs": (
                [str(p) for p in self.knowledge_base_outputs]
                if self.knowledge_base_outputs
                else None
            ),
        }


def _run_tutorial_variant(
    *,
    codebase_root: Path,
    knowledge_base_root: Path,
    tutorial_output_root: Path,
    enable_rag: bool,
    label: str,
) -> BenchRunResult:
    generator = TutorialGenerator(
        codebase_root=codebase_root,
        knowledge_base_root=knowledge_base_root,
        output_root=tutorial_output_root,
        enable_rag=enable_rag,
    )

    outputs: List[Path] = []
    error: str | None = None
    try:
        outputs = generator.generate()
    except Exception as exc:  # pragma: no cover - surfaced to caller/logs
        error = str(exc)
        logger.error("%s run failed for %s: %s", label, codebase_root, exc)

    return BenchRunResult(
        codebase=codebase_root,
        variant=label,
        tutorial_outputs=outputs,
        metrics=generator.metrics,
        error=error,
    )


def run_benchmarks(
    codebases: Iterable[Path],
    *,
    output_root: Path | None = None,
    enable_rag: bool = False,
    force_rebuild_kb: bool = False,
    skip_baseline: bool = False,
    skip_deep: bool = False,
) -> Path:
    root = ensure_directory(output_root or DEFAULT_BENCH_ROOT)
    results: list[BenchRunResult] = []

    for codebase in codebases:
        cb_root = codebase.expanduser().resolve()
        if not cb_root.exists():
            logger.error("Codebase %s does not exist, skipping", cb_root)
            continue

        bucket = ensure_directory(root / cb_root.name)

        if not skip_baseline:
            baseline_root = ensure_directory(bucket / "baseline")
            kb_stub = ensure_directory(baseline_root / "knowledge_base")
            tutorial_out = ensure_directory(baseline_root / "tutorials")
            results.append(
                _run_tutorial_variant(
                    codebase_root=cb_root,
                    knowledge_base_root=kb_stub,
                    tutorial_output_root=tutorial_out,
                    enable_rag=enable_rag,
                    label="baseline",
                )
            )

        if not skip_deep:
            deep_root = ensure_directory(bucket / "deep")
            kb_root = ensure_directory(deep_root / "knowledge_base")
            sub_agents_root = ensure_directory(deep_root / "sub_agents_workspace")
            tutorial_out = ensure_directory(deep_root / "tutorials")

            kb_outputs: List[Path] = []
            try:
                kb_outputs = KnowledgeBaseBuilder(
                    codebase_root=cb_root,
                    output_root=kb_root,
                    sub_agents_root=sub_agents_root,
                    force_rebuild=force_rebuild_kb,
                ).generate()
            except Exception as exc:  # pragma: no cover - surfaced to logs
                logger.error("KB build failed for %s: %s", cb_root, exc)

            deep_result = _run_tutorial_variant(
                codebase_root=cb_root,
                knowledge_base_root=kb_root,
                tutorial_output_root=tutorial_out,
                enable_rag=enable_rag,
                label="deep_with_kb",
            )
            deep_result.knowledge_base_outputs = kb_outputs
            results.append(deep_result)

    summary = {
        "root": str(root),
        "results": [item.to_dict() for item in results],
    }

    summary_path = root / "bench_results.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Bench summary written to %s", summary_path)
    return summary_path
