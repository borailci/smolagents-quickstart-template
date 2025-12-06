"""Command-line helpers for pipeline workflows (knowledge base, tutorials)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from loguru import logger

from pipelines.bench import run_benchmarks
from pipelines.knowledge_base_builder import KnowledgeBaseBuilder
from pipelines.tutorial_generator import TutorialGenerator


def _format_paths(paths: Iterable[Path]) -> str:
    entries = [str(path) for path in paths]
    if not entries:
        return "(no files generated)"
    return "\n".join(f"- {entry}" for entry in entries)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Utilities for generating knowledge bases and tutorials.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    kb_parser = subparsers.add_parser(
        "knowledge-base",
        aliases=["build-kb", "kb"],
        help="Generate the knowledge base using defaults and environment settings.",
    )
    kb_parser.set_defaults(command="knowledge-base")
    kb_parser.add_argument(
        "--codebase",
        type=Path,
        default=None,
        help="Override CODEBASE_ROOT_PATH for this run.",
    )
    kb_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override KNOWLEDGE_BASE_OUTPUT_PATH for this run.",
    )
    kb_parser.add_argument(
        "--sub-agents-root",
        type=Path,
        default=None,
        help="Workspace for sub-agents (defaults to data/agent_workspace/sub_agents_workspace).",
    )
    kb_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan targets without spawning analyzer agents.",
    )
    kb_parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Ignore cache and regenerate all targets.",
    )
    kb_parser.add_argument(
        "--step-delay",
        type=float,
        default=None,
        help="Seconds to sleep between sub-agent steps (default 0).",
    )
    kb_parser.add_argument(
        "--max-targets",
        type=int,
        default=None,
        help="Hard cap on planner-selected targets (defaults to MAX_PLANNER_TARGETS).",
    )

    tutorial_parser = subparsers.add_parser(
        "tutorials",
        aliases=["build-tutorials", "tutorial"],
        help="Generate tutorials using the existing knowledge base.",
    )
    tutorial_parser.set_defaults(command="tutorials")
    tutorial_parser.add_argument(
        "--rag",
        dest="rag",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Enable retrieval helper tools for gathering supporting snippets.",
    )

    bench_parser = subparsers.add_parser(
        "bench",
        help="Run baseline vs deep-with-KB tutorial generation and collect metrics.",
    )
    bench_parser.set_defaults(command="bench")
    bench_parser.add_argument(
        "--codebase",
        type=Path,
        action="append",
        required=True,
        help="Path to a codebase to benchmark. Provide multiple --codebase flags for multiple repos.",
    )
    bench_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output root for bench artifacts (defaults to data/bench).",
    )
    bench_parser.add_argument(
        "--rag",
        dest="rag",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Enable RAG for tutorial generation during benchmarking.",
    )
    bench_parser.add_argument(
        "--force-rebuild-kb",
        action="store_true",
        help="Force knowledge base regeneration for deep runs.",
    )
    bench_parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Skip the baseline agent run (only run deep+KB).",
    )
    bench_parser.add_argument(
        "--skip-deep",
        action="store_true",
        help="Skip the deep+KB run (only run baseline).",
    )

    return parser.parse_args()


def generate_knowledge_base(
    *,
    codebase: str | Path | None = None,
    output: str | Path | None = None,
    sub_agents_root: str | Path | None = None,
    dry_run: bool = False,
    force_rebuild: bool = False,
    step_delay_seconds: float | None = None,
    max_targets: int | None = None,
) -> list[Path]:
    builder = KnowledgeBaseBuilder(
        codebase_root=codebase,
        output_root=output,
        sub_agents_root=sub_agents_root,
        dry_run=dry_run,
        force_rebuild=force_rebuild,
        step_delay_seconds=step_delay_seconds,
        max_targets=max_targets,
    )
    return builder.generate()


def generate_tutorials(
    *,
    codebase: str | Path | None = None,
    knowledge_base: str | Path | None = None,
    output: str | Path | None = None,
    enable_code_search: bool | None = None,
    enable_rag: bool | None = None,
    rag_max_snippets: int | None = None,
    step_delay_seconds: float | None = None,
    dry_run: bool = False,
) -> list[Path]:
    generator = TutorialGenerator(
        codebase_root=codebase,
        knowledge_base_root=knowledge_base,
        output_root=output,
        enable_code_search=enable_code_search,
        enable_rag=enable_rag,
        rag_max_snippets=rag_max_snippets,
        step_delay_seconds=step_delay_seconds,
        dry_run=dry_run,
    )
    return generator.generate()


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO")


def main() -> None:
    args = parse_args()
    setup_logging()

    if args.command == "knowledge-base":
        outputs = generate_knowledge_base(
            codebase=args.codebase,
            output=args.output,
            sub_agents_root=args.sub_agents_root,
            dry_run=args.dry_run,
            force_rebuild=args.force_rebuild,
            step_delay_seconds=args.step_delay,
            max_targets=args.max_targets,
        )
        logger.info("Knowledge base written to:\n{}", _format_paths(outputs))
    elif args.command == "tutorials":
        generator = TutorialGenerator(enable_rag=args.rag)
        outputs = generator.generate()
        logger.info("Tutorials written to:\n{}", _format_paths(outputs))
    elif args.command == "bench":
        summary_path = run_benchmarks(
            args.codebase,
            output_root=args.output,
            enable_rag=args.rag,
            force_rebuild_kb=args.force_rebuild_kb,
            skip_baseline=args.skip_baseline,
            skip_deep=args.skip_deep,
        )
        logger.info("Bench summary: {}", summary_path)
    else:
        raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
