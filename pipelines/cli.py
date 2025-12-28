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
    eval_parser.add_argument(
        "--colab", action="store_true",
        help="Use Colab-hosted GPT-OSS-20B API (requires LLM_JUDGE_URL env var or --judge-url).",
    )
    eval_parser.add_argument(
        "--judge-url", type=str, default=None,
        help="URL for external LLM judge API (overrides LLM_JUDGE_URL env var).",
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
    deep_agent_parser.add_argument(
        "--no-kb",
        action="store_true",
        dest="no_kb",
        help="Skip Knowledge Base generation (for ablation study). Tutorial generation will proceed without KB context.",
    )
    deep_agent_parser.add_argument(
        "--kb",
        action="store_true",
        dest="kb_only",
        help="Run ONLY the Knowledge Base generation phase (skip Tutorials).",
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
    return builder.generate_with_supervisor()


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
        import pipelines.llm_judge as llm_judge_module
        
        # Handle external API URL
        if args.judge_url:
            llm_judge_module.EXTERNAL_API_URL = args.judge_url
            logger.info(f"Using external judge API: {args.judge_url}")
        
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

             # Select models - --colab flag overrides --models
             if args.colab:
                 models = ["colab"]
                 logger.info("Using Colab-hosted GPT-OSS-20B API for evaluation")
             elif args.models:
                 models = [m.strip() for m in args.models.split(",")]
             else:
                 models = JUDGE_MODELS
             
             all_results = []
             
             # For colab/external API, use multi-turn chat evaluation
             # Reads ALL tutorials upfront, model can request codebase files via READ: commands
             if args.colab:
                 from pipelines.llm_judge import evaluate_series_external
                 
                 logger.info(f"Evaluating with external API (Multi-turn mode - reads ALL tutorials)...")
                 logger.info(f"Series A: {len([f for f in baseline_files if f.name.endswith('.md')])} files")
                 logger.info(f"Series B: {len([f for f in deep_files if f.name.endswith('.md')])} files")
                 
                 res = evaluate_series_external(codebase_root, baseline_files, deep_files)
                 if res:
                     all_results.append(res)
                     print(f"\n{'='*50}")
                     print(f"WINNER: {res.get('winner')}")
                     print(f"{'='*50}")
                     if res.get('fidelity_A'):
                         print(f"Fidelity  - A: {res.get('fidelity_A')}/5, B: {res.get('fidelity_B')}/5")
                         print(f"Pedagogy  - A: {res.get('pedagogy_A')}/5, B: {res.get('pedagogy_B')}/5")
                         print(f"Coverage  - A: {res.get('coverage_A')}/5, B: {res.get('coverage_B')}/5")
                     print(f"Turns: {res.get('turns', 'N/A')}")
                     print(f"Files read: {res.get('files_read', [])}")
                     print(f"Rationale: {res.get('rationale', 'N/A')[:300]}...")
             else:
                 # Use agentic mode for native models
                 for model_id in models:
                     logger.info(f"Comparing Series with {model_id} (Agentic Mode)...")
                     res = evaluate_series(model_id, codebase_root, baseline_files, deep_files)
                     if res:
                         all_results.append(res)
                         print(f"Winner: {res.get('winner')}")
             
             # Save JSON
             output_dir = args.output or Path("evaluation")
             
             import datetime
             timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
             c_name = codebase_root.name
             out_file = output_dir / f"{c_name}_{timestamp}_report.json"
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
        
        # Use config.py for paths
        from config import settings as cfg
        
        if args.codebase:
            codebase_path = args.codebase.expanduser().resolve()
            logger.info(f"Using codebase from --codebase arg: {codebase_path}")
        else:
            # Use config.py CODEBASE_ROOT
            codebase_path = cfg.CODEBASE_ROOT
            logger.info(f"Using codebase from config.py: {codebase_path}")

        # Determine output root from config.py
        if args.mode == "baseline":
            output_root = cfg.BASELINE_ROOT
        else:
            output_root = cfg.DEEP_AGENT_ROOT

        # Mode Selection
        if args.mode == "baseline":
            logger.info("Running in BASELINE mode (No Knowledge Base Generation)")
            logger.info(f"Output directory: {output_root}")
            
            # Init Metrics for Baseline
            from utils.metrics import RunMetrics
            from utils.llm_factory import get_model_for_role
            
            metrics = RunMetrics(
                codebase_name=codebase_path.name,
                model_id=get_model_for_role("supervisor"),
            )
            tutorial_metrics = metrics.start_tutorial_phase()
            
            generator = TutorialGenerator(
                codebase_root=codebase_path,
                knowledge_base_root=cfg.BASELINE_KB,
                output_root=cfg.BASELINE_TUTORIALS,
                sub_agents_root=cfg.BASELINE_SUB_AGENTS,
                dry_run=args.dry_run,
                step_delay_seconds=getattr(args, "step_delay", None),
            )
            outputs = generator.generate_baseline_with_supervisor(metrics=tutorial_metrics)
            
            tutorial_metrics.finish()
            metrics.finish()
            
            # Save Baseline Metrics
            try:
                metrics.save_json(output_root / "metrics.json")
                metrics.save_markdown_summary(output_root / "metrics.md")
                logger.info(f"📊 Baseline Metrics saved to {output_root / 'metrics.json'}")
                
                # Also save to centralized metrics directory
                centralized_path = metrics.save_to_metrics_dir(pipeline_type="baseline")
                logger.info(f"📊 Baseline Metrics also saved to {centralized_path}")
            except Exception as e:
                logger.warning(f"Failed to save baseline metrics: {e}")
            logger.info("Baseline tutorials written to:\n{}", _format_paths(outputs))
            return

        # Standard Deep Agent
        logger.info(f"Output directory: {output_root}")
        
        config = DeepAgentConfig(
            codebase_root=codebase_path,
            output_root=output_root,
            kb_output_path=cfg.DEEP_AGENT_KB,
            tutorial_output_path=cfg.DEEP_AGENT_TUTORIALS,
            kb_sub_agents_path=cfg.DEEP_AGENT_KB_SUB_AGENTS,
            tutorial_sub_agents_path=cfg.DEEP_AGENT_TUTORIAL_SUB_AGENTS,
            force_rebuild_kb=args.force_rebuild if hasattr(args, "force_rebuild") else False,
            force_rebuild_tutorials=args.force_rebuild if hasattr(args, "force_rebuild") else False,
            dry_run=args.dry_run,
            skip_kb=getattr(args, "no_kb", False),  # Ablation mode
            skip_tutorials=getattr(args, "kb_only", False),
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
