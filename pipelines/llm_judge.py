"""LLM-as-judge evaluator for tutorial quality assessment.

Usage:
  python -m pipelines.llm_judge --tutorials data/deep_agent_output/xyz/tutorials

This module evaluates tutorials using multiple LLM models in a blind fashion.
Each model scores tutorials on: Accuracy, Completeness, Clarity, Structure, Diagrams.
Results are aggregated into a comprehensive report.
"""

from __future__ import annotations

import os
import argparse
import glob
from pathlib import Path
from loguru import logger
from utils.llm_factory import create_model
from smolagents import LiteLLMModel



import os
import argparse
import glob
import time
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from statistics import mean

try:
    from litellm import completion
    from litellm.exceptions import RateLimitError
except ImportError as exc:
    raise ImportError(
        "litellm is required for LLM judging. Install via `pip install litellm`."
    ) from exc

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("llm_judge")


# Judge models - sequential evaluation for diverse perspectives
JUDGE_MODELS = [
    "vertex_ai/gemini-2.5-pro",
    "openai/gpt-4o",
    "anthropic/claude-3-5-sonnet-20241022",
    "vertex_ai/gemini-2.5-flash",
]

# Evaluation criteria
CRITERIA = ["accuracy", "completeness", "clarity", "structure", "diagrams"]

# Truncation limits
MAX_TUTORIAL_CHARS = 15000
MAX_CODEBASE_CONTEXT_CHARS = 8000


EVALUATION_PROMPT = """You are an expert technical documentation reviewer. Evaluate this tutorial for a software codebase.

## Codebase Context
{codebase_context}

## Tutorial to Evaluate
{tutorial_content}

## Evaluation Criteria

Score each criterion from 1-5:
- **accuracy**: Are code snippets and technical details correct? Do they match the actual codebase?
- **completeness**: Does the tutorial cover all important aspects of the topic?
- **clarity**: Is the writing clear, well-organized, and easy to follow?
- **structure**: Are headings logical? Is there good flow from intro to conclusion?
- **diagrams**: Are Mermaid diagrams present, syntactically correct, and helpful?

## Response Format

Return ONLY valid JSON (no markdown fences):
{{
    "scores": {{
        "accuracy": <1-5>,
        "completeness": <1-5>,
        "clarity": <1-5>,
        "structure": <1-5>,
        "diagrams": <1-5>
    }},
    "overall": <1-5>,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "suggestions": ["suggestion1", "suggestion2"],
    "rationale": "Brief explanation of your scores"
}}
"""

def evaluate_pair(model: LiteLLMModel, model_id: str, file_name: str, path_a: Path, path_b: Path) -> dict | None:
    content_a = path_a.read_text(errors="replace") if path_a.exists() else "MISSING"
    content_b = path_b.read_text(errors="replace") if path_b.exists() else "MISSING"

@dataclass
class TutorialScore:
    """Score for a single tutorial from a single model."""
    tutorial_name: str
    model: str
    scores: Dict[str, int] = field(default_factory=dict)
    overall: float = 0.0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class AggregatedTutorialScore:
    """Aggregated scores for a tutorial across all models."""
    tutorial_name: str
    avg_scores: Dict[str, float] = field(default_factory=dict)
    avg_overall: float = 0.0
    all_strengths: List[str] = field(default_factory=list)
    all_weaknesses: List[str] = field(default_factory=list)
    all_suggestions: List[str] = field(default_factory=list)
    model_scores: List[TutorialScore] = field(default_factory=list)


@dataclass
class EvaluationReport:
    """Complete evaluation report."""
    tutorial_dir: str
    codebase: str
    models_used: List[str] = field(default_factory=list)
    tutorials: List[AggregatedTutorialScore] = field(default_factory=list)
    overall_avg: float = 0.0
    generated_at: str = ""


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text while preserving beginning and end."""
    if len(text) <= max_chars:
        return text
    half = (max_chars - 50) // 2
    return text[:half] + "\n\n... [truncated] ...\n\n" + text[-half:]


def _build_codebase_context(codebase_root: Path, max_chars: int = MAX_CODEBASE_CONTEXT_CHARS) -> str:
    """Build a context string from codebase files."""
    context_parts = [f"# Codebase: {codebase_root.name}\n"]
    
    # Prioritize README and key files
    priority_files = ["README.md", "readme.md", "README.rst", "setup.py", "pyproject.toml", "package.json"]
    
    files_added = 0
    total_chars = 0
    
    for pf in priority_files:
        fp = codebase_root / pf
        if fp.exists() and fp.is_file():
            try:
                content = fp.read_text(encoding="utf-8")[:2000]
                context_parts.append(f"\n## {pf}\n```\n{content}\n```")
                total_chars += len(content)
                files_added += 1
            except Exception:
                continue
    
    # Add some source files if space allows
    if total_chars < max_chars - 2000:
        for ext in [".py", ".ts", ".js"]:
            for fp in codebase_root.rglob(f"*{ext}"):
                if files_added >= 10 or total_chars >= max_chars:
                    break
                if any(skip in str(fp) for skip in ["node_modules", "__pycache__", ".git", "venv", "test"]):
                    continue
                try:
                    content = fp.read_text(encoding="utf-8")[:1500]
                    rel_path = fp.relative_to(codebase_root)
                    context_parts.append(f"\n## {rel_path}\n```\n{content}\n```")
                    total_chars += len(content)
                    files_added += 1
                except Exception:
                    continue
    
    return _truncate("\n".join(context_parts), max_chars)





def _call_judge(
    model: str,
    tutorial_content: str,
    codebase_context: str,
    temperature: float = 0.0,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Call a single judge model and parse response."""
    prompt = EVALUATION_PROMPT.format(
        codebase_context=codebase_context,
        tutorial_content=_truncate(tutorial_content, MAX_TUTORIAL_CHARS),
    )
    
    last_error: Exception | None = None
    
    for attempt in range(1, max_retries + 1):
        try:
            response = model(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )
            
            choices = resp.get("choices") or []
            if not choices:
                raise RuntimeError("Judge model returned no choices")
            
            content = str(choices[0].get("message", {}).get("content", "")).strip()
            if not content:
                raise RuntimeError("Judge model returned empty content")
            
            # Strip markdown fences if present
            if content.startswith("```"):
                content = re.sub(r"^```\w*\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            
            # Parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON object
                match = re.search(r"\{.*\}", content, flags=re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                raise RuntimeError(f"Invalid JSON response: {content[:200]}")
                
        except RateLimitError as exc:
            last_error = exc
            wait = min(5.0 * attempt, 20.0)
            logger.warning(f"Rate limited on {model} (attempt {attempt}/{max_retries}); sleeping {wait}s")
            time.sleep(wait)
        except Exception as exc:
            last_error = exc
            if attempt >= max_retries:
                raise
            wait = min(3.0 * attempt, 15.0)
            logger.warning(f"Judge call failed on {model} (attempt {attempt}/{max_retries}): {exc}")
            time.sleep(wait)
    
    if last_error:
        raise last_error
    raise RuntimeError("Unknown judge failure")


def evaluate_tutorial(
    tutorial_path: Path,
    codebase_context: str,
    models: List[str] = JUDGE_MODELS,
) -> AggregatedTutorialScore:
    """Evaluate a single tutorial with multiple models."""
    
    tutorial_content = tutorial_path.read_text(encoding="utf-8")
    tutorial_name = tutorial_path.name
    
    model_scores: List[TutorialScore] = []
    
    for model in models:
        logger.info(f"  → Evaluating with {model}...")
        try:
            result = _call_judge(model, tutorial_content, codebase_context)
            
            score = TutorialScore(
                tutorial_name=tutorial_name,
                model=model,
                scores=result.get("scores", {}),
                overall=result.get("overall", 0),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", []),
                rationale=result.get("rationale", ""),
            )
            model_scores.append(score)
            
        except Exception as e:
            logger.error(f"  ✗ {model} failed: {e}")
            # Add a placeholder score
            model_scores.append(TutorialScore(
                tutorial_name=tutorial_name,
                model=model,
                rationale=f"Evaluation failed: {e}"
            ))
    
    # Aggregate scores
    valid_scores = [s for s in model_scores if s.scores]
    
    if valid_scores:
        avg_scores = {}
        for criterion in CRITERIA:
            values = [s.scores.get(criterion, 0) for s in valid_scores if s.scores.get(criterion)]
            avg_scores[criterion] = round(mean(values), 2) if values else 0.0
        
        overall_values = [s.overall for s in valid_scores if s.overall]
        avg_overall = round(mean(overall_values), 2) if overall_values else 0.0
    else:
        avg_scores = {c: 0.0 for c in CRITERIA}
        avg_overall = 0.0
    
    # Collect all feedback
    all_strengths = list(set(s for score in valid_scores for s in score.strengths))
    all_weaknesses = list(set(w for score in valid_scores for w in score.weaknesses))
    all_suggestions = list(set(s for score in valid_scores for s in score.suggestions))
    
    return AggregatedTutorialScore(
        tutorial_name=tutorial_name,
        avg_scores=avg_scores,
        avg_overall=avg_overall,
        all_strengths=all_strengths[:5],
        all_weaknesses=all_weaknesses[:5],
        all_suggestions=all_suggestions[:5],
        model_scores=model_scores,
    )


def evaluate_tutorials(
    tutorial_dir: Path,
    codebase_root: Path,
    models: List[str] = JUDGE_MODELS,
) -> EvaluationReport:
    """Evaluate all tutorials in a directory."""
    
    tutorial_files = sorted(tutorial_dir.glob("*.md"))
    if not tutorial_files:
        raise ValueError(f"No markdown tutorials found in {tutorial_dir}")
    
    logger.info(f"Found {len(tutorial_files)} tutorials to evaluate")
    logger.info(f"Using models: {models}")
    
    # Build codebase context once
    logger.info("Building codebase context...")
    codebase_context = _build_codebase_context(codebase_root)
    
    # Evaluate each tutorial
    tutorial_scores: List[AggregatedTutorialScore] = []
    
    for i, tutorial_path in enumerate(tutorial_files, 1):
        logger.info(f"\n[{i}/{len(tutorial_files)}] Evaluating: {tutorial_path.name}")
        score = evaluate_tutorial(tutorial_path, codebase_context, models)
        tutorial_scores.append(score)
    
    # Calculate overall average
    all_overalls = [t.avg_overall for t in tutorial_scores if t.avg_overall > 0]
    overall_avg = round(mean(all_overalls), 2) if all_overalls else 0.0
    
    from datetime import datetime
    
    return EvaluationReport(
        tutorial_dir=str(tutorial_dir),
        codebase=str(codebase_root),
        models_used=models,
        tutorials=tutorial_scores,
        overall_avg=overall_avg,
        generated_at=datetime.now().isoformat(),
    )


def write_json_report(report: EvaluationReport, output_path: Path) -> None:
    """Write evaluation report as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "tutorial_dir": report.tutorial_dir,
        "codebase": report.codebase,
        "models_used": report.models_used,
        "overall_avg": report.overall_avg,
        "generated_at": report.generated_at,
        "tutorials": [
            {
                "name": t.tutorial_name,
                "avg_scores": t.avg_scores,
                "avg_overall": t.avg_overall,
                "strengths": t.all_strengths,
                "weaknesses": t.all_weaknesses,
                "suggestions": t.all_suggestions,
                "model_details": [
                    {
                        "model": s.model,
                        "scores": s.scores,
                        "overall": s.overall,
                        "rationale": s.rationale,
                    }
                    for s in t.model_scores
                ],
            }
            for t in report.tutorials
        ],
    }
    
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"JSON report written to: {output_path}")


def write_markdown_report(report: EvaluationReport, output_path: Path) -> None:
    """Write evaluation report as Markdown."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = [
        "# Tutorial Evaluation Report",
        "",
        f"**Generated:** {report.generated_at}",
        f"**Codebase:** `{Path(report.codebase).name}`",
        f"**Tutorial Directory:** `{report.tutorial_dir}`",
        f"**Models Used:** {', '.join(report.models_used)}",
        "",
        f"## Overall Score: {report.overall_avg}/5.0",
        "",
        "---",
        "",
        "## Summary by Tutorial",
        "",
        "| Tutorial | Accuracy | Completeness | Clarity | Structure | Diagrams | Overall |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    
    for t in report.tutorials:
        row = [
            t.tutorial_name,
            str(t.avg_scores.get("accuracy", "-")),
            str(t.avg_scores.get("completeness", "-")),
            str(t.avg_scores.get("clarity", "-")),
            str(t.avg_scores.get("structure", "-")),
            str(t.avg_scores.get("diagrams", "-")),
            str(t.avg_overall),
        ]
        lines.append("| " + " | ".join(row) + " |")
    
    lines.extend(["", "---", ""])
    
    # Detailed breakdowns
    for t in report.tutorials:
        lines.extend([
            f"## {t.tutorial_name}",
            "",
            f"**Average Score:** {t.avg_overall}/5.0",
            "",
        ])
        
        if t.all_strengths:
            lines.append("### Strengths")
            for s in t.all_strengths:
                lines.append(f"- {s}")
            lines.append("")
        
        if t.all_weaknesses:
            lines.append("### Weaknesses")
            for w in t.all_weaknesses:
                lines.append(f"- {w}")
            lines.append("")
        
        if t.all_suggestions:
            lines.append("### Suggestions")
            for s in t.all_suggestions:
                lines.append(f"- {s}")
            lines.append("")
        
        lines.append("### Model Opinions")
        for ms in t.model_scores:
            model_name = ms.model.split("/")[-1]
            lines.append(f"- **{model_name}**: {ms.overall}/5 — {ms.rationale[:100]}...")
        
        lines.extend(["", "---", ""])
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Markdown report written to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate tutorials using multiple LLM judges"
    )
    parser.add_argument(
        "--tutorials", type=Path, required=True,
        help="Path to tutorial directory containing .md files"
    )
    parser.add_argument(
        "--codebase", type=Path, default=None,
        help="Path to codebase root (auto-detected if not provided)"
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output directory for reports (defaults to same as tutorials)"
    )
    parser.add_argument(
        "--models", type=str, default=None,
        help="Comma-separated list of models (defaults to 4 diverse models)"
    )
    args = parser.parse_args()
    
    tutorial_dir = args.tutorials.expanduser().resolve()
    if not tutorial_dir.exists():
        logger.error(f"Tutorial directory not found: {tutorial_dir}")
        return
    
    # Auto-detect codebase
    if args.codebase:
        codebase_root = args.codebase.expanduser().resolve()
    else:
        # Try to find codebase from tutorial path structure
        # Assumes: data/deep_agent_output/{codebase}/tutorials
        if tutorial_dir.name == "tutorials":
            potential_codebase = Path("data/agent_workspace") / tutorial_dir.parent.name
            if potential_codebase.exists():
                codebase_root = potential_codebase
            else:
                codebase_root = tutorial_dir.parent
        else:
            codebase_root = tutorial_dir.parent
    
    # Parse models
    models = JUDGE_MODELS
    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    
    # Run evaluation
    report = evaluate_tutorials(tutorial_dir, codebase_root, models)
    
    # Write reports
    output_dir = args.output or tutorial_dir.parent
    write_json_report(report, output_dir / "evaluation_report.json")
    write_markdown_report(report, output_dir / "evaluation_report.md")
    
    logger.info(f"\n✓ Evaluation complete! Overall score: {report.overall_avg}/5.0")

    for model_id in model_ids:
        try:
            # Create model instance for this specific judge
            model = create_model(model_id=model_id)
            
            for file_name in all_files:
                path_a = args.baseline / file_name
                path_b = args.deep / file_name
                
                result = evaluate_pair(model, model_id, file_name, path_a, path_b)
                
                if result:
                    all_results.append(result)
                    print(f"{model_id:<25} | {file_name:<30} | {result.get('winner', '?'):<6} | "
                          f"{result.get('fidelity_A', 0):<5} | {result.get('fidelity_B', 0):<5} | "
                          f"{result.get('pedagogy_A', 0):<5} | {result.get('pedagogy_B', 0):<5} | "
                          f"{result.get('coverage_A', 0):<5} | {result.get('coverage_B', 0):<5}")
                
                 # Inter-file throttle
                time.sleep(1.0)
                
        except Exception as e:
            logger.error(f"Failed to initialize model {model_id}: {e}")

    # Aggregation Table
    if all_results:
        print("\n" + "="*50)
        print("AGGREGATE WIN RATES")
        print("="*50)
        
        wins = {"A": 0, "B": 0, "Tie": 0}
        total = 0
        
        for r in all_results:
            w = r.get("winner", "Tie")
            if w not in wins: w = "Tie"
            wins[w] += 1
            total += 1
            
        print(f"Total Evaluations: {total}")
        print(f"Baseline Wins (A): {wins['A']} ({wins['A']/total*100:.1f}%)")
        print(f"Deep Agent Wins (B): {wins['B']} ({wins['B']/total*100:.1f}%)")
        print(f"Ties:             {wins['Tie']} ({wins['Tie']/total*100:.1f}%)")

if __name__ == "__main__":
    main()
