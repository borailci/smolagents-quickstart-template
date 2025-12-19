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
from smolagents import LiteLLMModel, CodeAgent
from toolkits.scoped_filesystem_toolkit import build_scoped_tools



import json
import re
from dataclasses import dataclass, field
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
]

# Evaluation criteria
CRITERIA = ["accuracy", "completeness", "clarity", "structure", "diagrams"]

# Truncation limits
MAX_TUTORIAL_CHARS = 50000
MAX_CODEBASE_CONTEXT_CHARS = 50000


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

AGENT_JUDGE_PROMPT = """You are an expert technical documentation reviewer and judge.
Your task is to compare two **Tutorial Series** (A and B) for the provided codebase and pick a winner.
You have access to tools to read the codebase files. 
You MUST use these tools to verify:
1. **Fidelity**: Does the code in the tutorials match the actual codebase? (Check file existence, function names, signatures).
2. **Coverage**: Do the tutorials cover the main components found in the codebase tree? (Use `get_codebase_tree` to see structure).

## Tutorial Series A
{content_a}

## Tutorial Series B
{content_b}

## Evaluation Criteria
1. **Fidelity** (Crucial): Is the code accurate?
2. **Pedagogy**: Is the progression logical?
3. **Coverage**: Is the scope complete?

## Instructions
1. First, explore the codebase using `get_codebase_tree` and `read_codebase_file` to understand the actual project structure and content.
2. Read the tutorials sections above (they are provided in full context).
3. Verify at least 3 assertions/code snippets from the tutorials against the codebase using your tools.
4. Form your judgment.
5. **FINAL ANSWER**: Your task is NOT done until you return the result.
   You must end your execution by calling the `final_answer` function with a Python dictionary matching this structure:
   ```python
   final_answer({{
       "winner": "A" or "B" or "Tie",
       "fidelity_A": 1-5,
       "fidelity_B": 1-5,
       "pedagogy_A": 1-5,
       "pedagogy_B": 1-5,
       "coverage_A": 1-5,
       "coverage_B": 1-5,
       "rationale": "Detailed explanation..."
   }})
   ```
"""

def evaluate_series(model_id: str, codebase_context: str, baseline_paths: List[Path], deep_paths: List[Path]) -> dict | None:
    """Compare two complete sets of tutorials using an Agentic Judge."""
    
    # Check codebase_context - we actually interpret it as "codebase_root path" for the agent?
    # CLI passes "full_context" string currently.
    # Refactoring: CLI needs to pass the ROOT PATH, not the content string.
    # But wait, `evaluate_series` signature in CLI call (Step 935) was `evaluate_series(model_id, full_context, ...)`
    # I need to change CLI to pass ROOT PATH.
    # For now, I will extract root path from the FIRST deep_path parent's parent if not passed explicitly?
    # No, I should fix the signature. But let's look at `codebase_context` arg.
    # If the user passed `full_context` string, that won't work for `build_scoped_tools`.
    # I will assume `codebase_context` MIGHT be a Path object or a string.
    # I will update CLI to pass `codebase_root` (Path) instead of `full_context`.
    
    # Logic to locate codebase root if passed as string (won't work). 
    # I will assume CLI update is coming next.
    # For now, assume `codebase_context` is a Path or valid path string.
    
    # Logic to locate codebase root
    candidate_root = Path(codebase_context) if isinstance(codebase_context, (str, Path)) else None
    if not candidate_root or (isinstance(candidate_root, Path) and not candidate_root.exists()):
         # Fallback inference
         candidate_root = deep_paths[0].parent.parent.parent.parent / "agent_workspace" / deep_paths[0].parent.parent.name
         logger.warning(f"Inferred codebase root for Agent Judge: {candidate_root}")
    
    if not candidate_root.exists():
        logger.error(f"Cannot find codebase root at {candidate_root} for agent tools.")
        return {"winner": "Error", "rationale": "Codebase root not found for agent tools."}
        
    logger.info(f"Agent Judge initializing with tools for: {candidate_root}")

    # Setup Evaluation Context in Codebase Root
    import shutil
    
    # We create a temporary evaluation directory inside the codebase root
    # This allows the agent to access them using the scoped tools (which are bound to codebase_root)
    eval_root = candidate_root / "_evaluation_temp"
    dir_a = eval_root / "Series_A"
    dir_b = eval_root / "Series_B"
    
    # Clean/Create dirs
    if eval_root.exists(): shutil.rmtree(eval_root)
    dir_a.mkdir(parents=True)
    dir_b.mkdir(parents=True)
    
    # Copy files
    files_a_names = []
    files_b_names = []
    
    for p in baseline_paths:
        dest = dir_a / p.name
        shutil.copy2(p, dest)
        files_a_names.append(str(dest.relative_to(candidate_root)))

    for p in deep_paths:
        dest = dir_b / p.name
        shutil.copy2(p, dest)
        files_b_names.append(str(dest.relative_to(candidate_root)))
        
    logger.info(f"Staged tutorials in {eval_root}")
    
    # Construct Listing Strings for Prompt
    list_a = "\n".join([f"- {n}" for n in sorted(files_a_names)])
    list_b = "\n".join([f"- {n}" for n in sorted(files_b_names)])

    prompt = AGENT_JUDGE_PROMPT.format(
        content_a=f"Files located at:\n{list_a}\n\n(Use `read_codebase_file` to read them.)",
        content_b=f"Files located at:\n{list_b}\n\n(Use `read_codebase_file` to read them.)"
    )
    
    # Initialize Agent
    tools = build_scoped_tools(
        codebase_root=str(candidate_root),
        workspace_root=str(candidate_root), # Allow reading everything in root
        allow_tree=True,
        allow_directory_listing=True,
        allow_writes=False # Judge is read-only
    )
    
    model = create_model(model_id=model_id)
    
    # Step callback to add delay between steps
    import time as time_module
    def step_delay_callback(step_log):
        time_module.sleep(2)  # 2 second delay between steps
    
    agent = CodeAgent(
        tools=tools,
        model=model,
        add_base_tools=True, # Allow python helpers
        max_steps=12, # Allow 12 steps of exploration
        step_callbacks=[step_delay_callback],
    )

    max_retries = 10
    retry_delay = 5  # Start with 5 seconds
    
    for attempt in range(max_retries):
        try:
            response = agent.run(prompt)
            
            # Cleanup
            if eval_root.exists(): shutil.rmtree(eval_root)
            
            # If agent uses final_answer(dict), response is the dict!
            if isinstance(response, dict):
                response["file_name"] = "Comparison (Agentic)"
                response["model"] = model_id
                return response
            
            # Try to parse result from agent content
            content = str(response)
            
            # Try JSON parse
            import json
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    data["file_name"] = "Comparison (Agentic)"
                    data["model"] = model_id
                    return data
            except: pass
            
            # Try to find JSON in the content
            json_pattern = r'\{[^{}]*"winner"[^{}]*\}'
            import re
            match = re.search(json_pattern, content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                    if isinstance(data, dict):
                        data["file_name"] = "Comparison (Agentic)"
                        data["model"] = model_id
                        return data
                except: pass

            # Try AST on raw content?
            try:
                import ast
                data = ast.literal_eval(content)
                if isinstance(data, dict):
                    data["file_name"] = "Comparison (Agentic)"
                    data["model"] = model_id
                    return data
            except: pass
            
            return {"file_name": "Comparison", "model": model_id, "winner": "Error", "rationale": f"JSON parse error: {content[:200]}"}
            
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "rate" in error_str or "resource_exhausted" in error_str
            
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                import time
                time.sleep(wait_time)
                continue
            
            logger.error(f"Agentic comparison failed: {e}")
            # Cleanup on error
            if eval_root.exists(): shutil.rmtree(eval_root)
            return {"file_name": "Comparison", "model": model_id, "winner": "Error", "rationale": str(e)}


def evaluate_pair(model_id: str, file_name: str, codebase_context: str, path_a: Path, path_b: Path) -> dict | None:
    """Compare two tutorials using an LLM."""
    content_a = path_a.read_text(errors="replace") if path_a.exists() else "MISSING"
    content_b = path_b.read_text(errors="replace") if path_b.exists() else "MISSING"
    
    if content_a == "MISSING" and content_b == "MISSING":
        return None
        
    truncate_len = 6000 # Shorter to fit two into context
    
    prompt = COMPARE_PROMPT.format(
        codebase_context=codebase_context,
        content_a=_truncate(content_a, truncate_len),
        content_b=_truncate(content_b, truncate_len)
    )
    
    try:
        from utils.llm_factory import create_model
        model = create_model(model_id=model_id)
        
        response = model(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096
        )
        
        # smolagents Model returns ChatMessage directly
        if hasattr(response, "content"):
             content = str(response.content).strip()
        else:
             # Fallback for other potential return types
             content = str(response).strip()
        
        if content in ["None", ""] or content is None:
            logger.warning(f"Empty response for {file_name}. Retry suggested.")
            return {"file_name": file_name, "model": model_id, "winner": "Error", "rationale": "Empty/Blocked response from model"}

        # Strip markdown fences
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE).strip()
        content = re.sub(r"\s*```$", "", content).strip()
        
        # Simple cleanup for common JSON errors
        content = re.sub(r",\s*\}", "}", content) # Trailing comma in object
        content = re.sub(r",\s*\]", "]", content) # Trailing comma in list

        try:
            data = json.loads(content)
            data["file_name"] = file_name
            data["model"] = model_id
            return data
        except json.JSONDecodeError as exc:
            # Fallback: Try to find the first JSON object in the string
            match = re.search(r"(\{.*\})", content, flags=re.DOTALL)
            if match:
                 try:
                    c_fixed = match.group(1)
                    c_fixed = re.sub(r",\s*\}", "}", c_fixed)
                    data = json.loads(c_fixed)
                    data["file_name"] = file_name
                    data["model"] = model_id
                    return data
                 except:
                    pass
            
            logger.error(f"JSON Parse Error for {file_name}.\nError: {exc}\nContent:\n{content}")
            return {"file_name": file_name, "model": model_id, "winner": "Error", "rationale": f"JSON parse error. Content: {content[:200]}"}
            
    except Exception as e:
        logger.error(f"Comparison failed for {file_name}: {e}")
        return {"file_name": file_name, "model": model_id, "winner": "Error", "rationale": str(e)}


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
            
            # Handle smolagents.models.ChatMessage or LiteLLM response
            if hasattr(response, "content"):
                content = str(response.content).strip()
            elif isinstance(response, dict):
                choices = response.get("choices") or []
                if not choices:
                    raise RuntimeError("Judge model returned no choices")
                content = str(choices[0].get("message", {}).get("content", "")).strip()
            else:
                content = str(response).strip()

            if not content:
                raise RuntimeError("Judge model returned empty content")
            
            # Strip markdown fences if present
            content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE).strip()
            content = re.sub(r"\s*```$", "", content).strip()
            
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
    # Mode 1: Single directory eval
    parser.add_argument(
        "--tutorials", type=Path, default=None,
        help="Path to tutorial directory containing .md files"
    )
    
    # Mode 2: A/B Comparison
    parser.add_argument("--baseline", type=Path, default=None, help="Path to Baseline tutorials")
    parser.add_argument("--deep", type=Path, default=None, help="Path to DeepAgent tutorials")
    
    # Common
    parser.add_argument(
        "--codebase", type=Path, default=None,
        help="Path to codebase root (auto-detected if not provided)"
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output directory for reports"
    )
    parser.add_argument(
        "--models", type=str, default=None,
        help="Comma-separated list of models"
    )
    args = parser.parse_args()
    
    # Determine Codebase
    codebase_root = None
    if args.codebase:
        codebase_root = args.codebase.expanduser().resolve()
    
    # Mode: Compare
    if args.baseline and args.deep:
        if not codebase_root:
            # Fallback assumption
            codebase_root = args.deep.parent.parent # data/deep_agent_output/REPO/tutorials -> REPO ? No.
            # safe fallback: current dir
            if not codebase_root or not codebase_root.exists():
                 codebase_root = Path(".")
        
        logger.info(f"Starting A/B Comparison: {args.baseline.name} vs {args.deep.name}")
        
        baseline_files = set(f.name for f in args.baseline.glob("*.md"))
        deep_files = set(f.name for f in args.deep.glob("*.md"))
        common_files = sorted(list(baseline_files.intersection(deep_files)))
        
        if not common_files:
            logger.error("No common files to compare!")
            return

        logger.info(f"Comparing {len(common_files)} common files...")
        context = _build_codebase_context(codebase_root)
        
        models = [m.strip() for m in args.models.split(",")] if args.models else JUDGE_MODELS
        all_results = []
        
        for file_name in common_files:
            for model_id in models:
                logger.info(f"Comparing {file_name} with {model_id}...")
                res = evaluate_pair(model_id, file_name, context, args.baseline/file_name, args.deep/file_name)
                if res:
                    all_results.append(res)
                    print(f"Winner: {res.get('winner')} | {file_name}")

        # Summary
        wins = {"A": 0, "B": 0, "Tie": 0, "Error": 0}
        for r in all_results:
            w = r.get("winner", "Error")
            wins[w] = wins.get(w, 0) + 1
            
        print("\n" + "="*50)
        print("AGGREGATE WIN RATES")
        print("="*50)
        total = len(all_results)
        if total > 0:
            print(f"Total: {total}")
            print(f"Baseline (A): {wins['A']} ({wins['A']/total*100:.1f}%)")
            print(f"DeepAgent (B): {wins['B']} ({wins['B']/total*100:.1f}%)")
            print(f"Tie:          {wins['Tie']} ({wins['Tie']/total*100:.1f}%)")
        
        # Write JSON
        if args.output:
            out_file = args.output / "comparison_report.json"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
            logger.info(f"Saved comparison report to {out_file}")
            
        return

    # Mode: Single Eval
    if args.tutorials:
        tutorial_dir = args.tutorials.expanduser().resolve()
        if not tutorial_dir.exists():
            logger.error(f"Tutorial directory not found: {tutorial_dir}")
            return
            
        if not codebase_root:
             codebase_root = tutorial_dir.parent # Best guess
        
        models = [m.strip() for m in args.models.split(",")] if args.models else JUDGE_MODELS
        report = evaluate_tutorials(tutorial_dir, codebase_root, models)
        
        output_dir = args.output or tutorial_dir.parent
        write_json_report(report, output_dir / "evaluation_report.json")
        write_markdown_report(report, output_dir / "evaluation_report.md")
        logger.info(f"Evaluation complete! Score: {report.overall_avg}/5.0")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
