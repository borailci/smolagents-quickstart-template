"""Command-line helpers for pipeline workflows (knowledge base, tutorials)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from loguru import logger
from rich.console import Console
from rich.panel import Panel

from config import settings
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
        default=0.0,
        help="Delay in seconds between agent steps (for rate limits).",
    )
    kb_parser.add_argument(
        "--max-targets",
        type=int,
        default=None,
        help="Maximum number of directories to analyze.",
    )
    kb_parser.add_argument(
        "--supervisor",
        action="store_true",
        help="Use the Supervisor Agent instead of simple heuristic.",
    )
    tutorial_parser = subparsers.add_parser(
        "tutorials",
        aliases=["build-tutorials", "tutorial"],
        help="Generate tutorials using the existing knowledge base.",
    )
    tutorial_parser.set_defaults(command="tutorials")
    tutorial_parser.add_argument(
        "--step-delay",
        type=float,
        default=0.0,
        help="Delay in seconds between agent steps.",
    )
    tutorial_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate tutorial generation.",
    )


    # Evaluate command (LLM Judge)
    eval_parser = subparsers.add_parser(
        "evaluate",
        aliases=["eval", "judge"],
        help="Evaluate tutorial quality using multiple LLM judges.",
    )
    eval_parser.set_defaults(command="evaluate")
    eval_parser.add_argument(
        "--tutorials", type=Path, default=None,
        help="Path to tutorial directory containing .md files (Single Eval Mode).",
    )
    eval_parser.add_argument(
        "--baseline", type=Path, default=None,
        help="Path to Baseline tutorials (A/B Compare Mode).",
    )
    eval_parser.add_argument(
        "--deep", type=Path, default=None,
        help="Path to DeepAgent tutorials (A/B Compare Mode).",
    )
    eval_parser.add_argument(
        "--models", type=str, default=None,
        help="Comma-separated list of models to use as judges.",
    )
    eval_parser.add_argument(
        "--codebase", type=Path, default=settings.CODEBASE_ROOT,
        help="Root path of the codebase (for context generation).",
    )
    eval_parser.add_argument(
        "--output", type=Path, default=None,
        help="Optional path to output the evaluation report.",
    )

    deep_agent_parser = subparsers.add_parser(
        "deep-agent",
        help="Run the unified Deep Agent pipeline (KB + Tutorials).",
    )
    deep_agent_parser.set_defaults(command="deep-agent")
    deep_agent_parser.add_argument(
        "--codebase",
        type=Path,
        required=False,
        default=None,
        help="Path to the codebase. If not provided, looks for directories in data/agent_workspace.",
    )
    deep_agent_parser.add_argument(
        "--force-rebuild",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Force regeneration of Knowledge Base and Tutorials (default: True). Use --no-force-rebuild to skip.",
    )
    deep_agent_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without running LLM agents.",
    )
    deep_agent_parser.add_argument(
        "--mode",
        choices=["standard", "baseline"],
        default="standard",
        help="Run mode: 'standard' (full KB + tutorials) or 'baseline' (tutorials from codebase exploration only).",
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
    use_supervisor: bool = False,
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
    if use_supervisor:
        return builder.generate_with_supervisor()
    return builder.generate()


def generate_tutorials(
    *,
    codebase: str | Path | None = None,
    knowledge_base: str | Path | None = None,
    output: str | Path | None = None,
    step_delay_seconds: float | None = None,
    dry_run: bool = False,
) -> list[Path]:
    generator = TutorialGenerator(
        codebase_root=codebase,
        knowledge_base_root=knowledge_base,
        output_root=output,
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
            use_supervisor=args.supervisor,
        )
        logger.info("Knowledge base written to:\n{}", _format_paths(outputs))
    elif args.command == "tutorials":
        generator = TutorialGenerator(
            dry_run=args.dry_run,
            step_delay_seconds=args.step_delay,
        )
        outputs = generator.generate()
        logger.info("Tutorials written to:\n{}", _format_paths(outputs))
    elif args.command == "evaluate":
        from pipelines.llm_judge import evaluate_tutorials, evaluate_pair, evaluate_series, write_json_report, write_markdown_report, JUDGE_MODELS, _build_codebase_context
        
        # A/B Comparison Mode
        if args.baseline and args.deep:
             logger.info(f"Starting A/B Comparison (Series Mode): {args.baseline.name} vs {args.deep.name}")
             
             if args.codebase:
                 codebase_root = args.codebase.expanduser().resolve()
             else:
                 codebase_root = args.deep.parent.parent # Best guess fallback
                 if not codebase_root.exists(): codebase_root = Path(".")

             logger.info(f"Using codebase root: {codebase_root}")

             baseline_files = list(args.baseline.glob("*.md"))
             deep_files = list(args.deep.glob("*.md"))
             
             if not baseline_files or not deep_files:
                 logger.error("Missing tutorial files in one of the directories.")
                 return

             models = [m.strip() for m in args.models.split(",")] if args.models else JUDGE_MODELS
             all_results = []
             
             for model_id in models:
                 logger.info(f"Comparing Series with {model_id} (Agentic Mode)...")
                 # Pass codebase_root as the context argument for the Agent to use tools on
                 res = evaluate_series(model_id, codebase_root, baseline_files, deep_files)
                 if res:
                     all_results.append(res)
                     print(f"Winner: {res.get('winner')}")
             
             # Save JSON
             if args.output:
                 out_file = args.output / "comparison_report.json"
                 out_file.parent.mkdir(parents=True, exist_ok=True)
                 import json
                 out_file.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
                 logger.info(f"Saved comparison report to {out_file}")
             return

        # Single Eval Mode
        if not args.tutorials:
            logger.error("--tutorials is required if not running in A/B mode (--baseline/--deep)")
            return

        tutorial_dir = args.tutorials.expanduser().resolve()
        
        if args.codebase:
            codebase_root = args.codebase.expanduser().resolve()
        else:
            if tutorial_dir.name == "tutorials":
                potential = Path("data/agent_workspace") / tutorial_dir.parent.name
                codebase_root = potential if potential.exists() else tutorial_dir.parent
            else:
                codebase_root = tutorial_dir.parent
        
        models = JUDGE_MODELS
        if args.models:
            models = [m.strip() for m in args.models.split(",") if m.strip()]
        
        report = evaluate_tutorials(tutorial_dir, codebase_root, models)
        
        output_dir = args.output or tutorial_dir.parent
        write_json_report(report, output_dir / "evaluation_report.json")
        write_markdown_report(report, output_dir / "evaluation_report.md")
        
        logger.info(f"Evaluation complete! Overall score: {report.overall_avg}/5.0")

    elif args.command == "deep-agent":
        from pipelines.deep_agent import DeepAgent, DeepAgentConfig
        
        # Priority: 1) .env CODEBASE_ROOT_PATH, 2) --codebase arg, 3) auto-discovery
        import os
        env_codebase = os.getenv("CODEBASE_ROOT_PATH")
        
        if env_codebase:
            codebase_path = Path(env_codebase).expanduser().resolve()
            logger.info(f"Using codebase from .env: {codebase_path}")
        elif args.codebase:
            codebase_path = args.codebase.expanduser().resolve()
            logger.info(f"Using codebase from --codebase arg: {codebase_path}")
        else:
            # Auto-discover from data/agent_workspace
            workspace_root = Path("data/agent_workspace").resolve()
            candidates = [
                d for d in workspace_root.iterdir() 
                if d.is_dir() and not d.name.startswith(".") and d.name not in ("knowledge_base", "sub_agents_workspace")
            ]
            
            if not candidates:
                logger.error("No codebase found. Set CODEBASE_ROOT_PATH in .env, use --codebase, or add repos to data/agent_workspace.")
                sys.exit(1)
            
            if len(candidates) > 1:
                logger.warning(f"Multiple codebases found: {[c.name for c in candidates]}. Using the first one: {candidates[0].name}")
            
            codebase_path = candidates[0]
            logger.info(f"Auto-selected codebase: {codebase_path}")


        # Determine output root for both modes
        if args.mode == "baseline":
            output_root = (settings.BASELINE_OUTPUT_ROOT / codebase_path.name).resolve()
        else:
            output_root = (Path("data/deep_agent_output") / codebase_path.name).resolve()

        # Mode Selection
        if args.mode == "baseline":
            logger.info("Running in BASELINE mode (No Knowledge Base Generation)")
            logger.info(f"Output directory: {output_root}")
            # Baseline output structure
            generator = TutorialGenerator(
                codebase_root=codebase_path,
                knowledge_base_root=output_root / "knowledge_base", # Dummy
                output_root=output_root,
                sub_agents_root=output_root / "sub_agents_tutorials",
                dry_run=args.dry_run,
            )
            # Use wrapped baseline generator
            outputs = generator.generate_baseline_with_supervisor()
            logger.info("Baseline tutorials written to:\n{}", _format_paths(outputs))
            return

        # Standard Deep Agent
        logger.info(f"Output directory: {output_root}")
        
        config = DeepAgentConfig(
            codebase_root=codebase_path,
            output_root=output_root,
            # Sub-paths fully inspectable in data/<codebase-name>/ folder
            kb_output_path=output_root / "knowledge_base",
            tutorial_output_path=output_root / "tutorials",
            kb_sub_agents_path=output_root / "sub_agents_kb",
            tutorial_sub_agents_path=output_root / "sub_agents_tutorials",
            force_rebuild_kb=args.force_rebuild if hasattr(args, "force_rebuild") else False,
            force_rebuild_tutorials=args.force_rebuild if hasattr(args, "force_rebuild") else False,
            dry_run=args.dry_run,
        )
        
        agent = DeepAgent(config)
        agent.run()
    else:
        raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    import sys
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
        sys.exit(0)
