"""Command-line helpers for pipeline workflows (knowledge base, tutorials)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from loguru import logger

from pipelines.knowledge_base_builder import KnowledgeBaseBuilder
from pipelines.tutorial_generator import TutorialGenerator
from toolkits.sub_agent_toolkit import run_sub_agent_tasks


def _format_paths(paths: Iterable[Path]) -> str:
    entries = [str(path) for path in paths]
    if not entries:
        return "(no files generated)"
    return "\n".join(f"- {entry}" for entry in entries)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Utilities for generating knowledge bases and tutorials.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all logging output.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging for troubleshooting.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    kb_parser = subparsers.add_parser(
        "knowledge-base",
        aliases=["build-kb", "kb"],
        help="Generate the knowledge base using sub-agents.",
    )
    kb_parser.set_defaults(command="knowledge-base")
    kb_parser.add_argument(
        "codebase",
        nargs="?",
        default=None,
        help="Path to the codebase root. Uses CODEBASE_ROOT_PATH if omitted.",
    )
    kb_parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="Directory where the knowledge base markdown files will be written.",
    )
    kb_parser.add_argument(
        "--sub-agents-root",
        dest="sub_agents_root",
        default=None,
        help="Workspace root where sub-agent artifacts are stored.",
    )
    kb_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the process without running expensive agents.",
    )
    kb_parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force regeneration of all targets, ignoring checkpoints.",
    )
    kb_parser.add_argument(
        "--step-delay-seconds",
        dest="step_delay_seconds",
        type=float,
        default=None,
        help="Insert an extra pause between sub-agent steps (e.g., 1.5) to reduce rate pressure.",
    )
    kb_parser.add_argument(
        "--max-targets",
        dest="max_targets",
        type=int,
        default=None,
        help="Cap the number of planner-selected targets (sub-agents) to run this session.",
    )

    tutorial_parser = subparsers.add_parser(
        "tutorials",
        aliases=["build-tutorials", "tutorial"],
        help="Generate tutorials using the existing knowledge base.",
    )
    tutorial_parser.set_defaults(command="tutorials")
    tutorial_parser.add_argument(
        "--codebase",
        dest="codebase",
        default=None,
        help="Path to the codebase root. Uses CODEBASE_ROOT_PATH if omitted.",
    )
    tutorial_parser.add_argument(
        "--knowledge-base",
        dest="knowledge_base",
        default=None,
        help="Directory containing the generated knowledge base files.",
    )
    tutorial_parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="Directory where tutorial markdown files will be written.",
    )
    tutorial_parser.add_argument(
        "--code-search",
        dest="code_search",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Enable grep-based code search tools for the tutorial agent.",
    )
    tutorial_parser.add_argument(
        "--rag",
        dest="rag",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Enable retrieval helper tools for gathering supporting snippets.",
    )
    tutorial_parser.add_argument(
        "--rag-max-snippets",
        dest="rag_max_snippets",
        type=int,
        default=None,
        help="Override the maximum number of snippets returned by the retrieval helper.",
    )
    tutorial_parser.add_argument(
        "--step-delay-seconds",
        dest="step_delay_seconds",
        type=float,
        default=None,
        help="Insert an additional pause between each agent step (e.g., 1.5) to ease rate limits.",
    )
    tutorial_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the process without running expensive agents.",
    )

    subagent_parser = subparsers.add_parser(
        "spawn-subagents",
        aliases=["spawn-sub-agents", "sub-agent"],
        help="Run ad-hoc sub-agent analyzer tasks and report their workspaces.",
    )
    subagent_parser.set_defaults(command="spawn-subagents")
    subagent_parser.add_argument(
        "--codebase",
        dest="codebase",
        default=None,
        help="Path to the codebase root. Uses CODEBASE_ROOT_PATH if omitted.",
    )
    subagent_parser.add_argument(
        "--sub-agents-root",
        dest="sub_agents_root",
        default=None,
        help="Directory where sub-agent workspaces should be created.",
    )
    subagent_parser.add_argument(
        "tasks",
        nargs="+",
        help="One or more analyzer task descriptions (wrap sentences in quotes).",
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


def spawn_sub_agents(
    tasks: list[str],
    *,
    codebase: str | Path | None = None,
    sub_agents_root: str | Path | None = None,
) -> list[Path]:
    return run_sub_agent_tasks(
        tasks,
        codebase_root=codebase,
        sub_agents_root=sub_agents_root,
    )


def setup_logging(*, verbose: bool = False, quiet: bool = False) -> None:
    logger.remove()
    if quiet:
        return
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level)


def main() -> None:
    args = parse_args()
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    if args.command == "knowledge-base":
        builder = KnowledgeBaseBuilder(
            codebase_root=args.codebase,
            output_root=args.output,
            sub_agents_root=args.sub_agents_root,
            dry_run=args.dry_run,
            force_rebuild=args.force_rebuild,
            step_delay_seconds=args.step_delay_seconds,
            max_targets=args.max_targets,
        )
        outputs = builder.generate()
        logger.info("Knowledge base written to:\n{}", _format_paths(outputs))
    elif args.command == "tutorials":
        generator = TutorialGenerator(
            codebase_root=args.codebase,
            knowledge_base_root=args.knowledge_base,
            output_root=args.output,
            enable_code_search=args.code_search,
            enable_rag=args.rag,
            rag_max_snippets=args.rag_max_snippets,
            step_delay_seconds=args.step_delay_seconds,
            dry_run=args.dry_run,
        )
        outputs = generator.generate()
        logger.info("Tutorials written to:\n{}", _format_paths(outputs))
    elif args.command == "spawn-subagents":
        workspaces = spawn_sub_agents(
            args.tasks,
            codebase=args.codebase,
            sub_agents_root=args.sub_agents_root,
        )
        if not workspaces:
            logger.warning("No sub-agents were executed; check the provided tasks.")
            return
        workspace_lines = "\n".join(f"- {path}" for path in workspaces)
        logger.info(
            "Sub-agents completed. Workspaces:\n{}",
            workspace_lines,
        )
    else:
        raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
