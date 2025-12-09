"""LLM-as-judge evaluator for baseline vs deep tutorials.

Usage:
  python -m pipelines.llm_judge \
    --bench data/bench/bench_results.json \
    --models vertex_ai/gemini-2.5-pro \
    --output data/bench/llm_judge_results.jsonl \
    --summary data/bench/llm_judge_summary.json

The script reads bench_results.json, pairs baseline vs deep_with_kb tutorials
per codebase, and asks an LLM judge (Gemini by default) to score Fidelity,
Pedagogy, Coverage (1-5) and pick a winner.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, cast

# Fixed defaults to avoid CLI bloat while keeping ample context
TUTORIAL_MAX_CHARS = 12000
CODEBASE_MAX_FILES = 40
CODEBASE_MAX_CHARS = 2000
SAMPLES = 3

try:
    from litellm import completion
    from litellm.exceptions import RateLimitError
except ImportError as exc:
    raise ImportError(
        "litellm is required for LLM judging. Install it via `pip install litellm`."
    ) from exc

try:
    from loguru import logger
except ImportError:  # Fallback if loguru is not installed
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("llm_judge")

PROMPT_TEMPLATE = """
You are an expert technical reviewer. Evaluate two tutorial pipelines for the SAME codebase.

Inputs:
- Codebase digest: directory snapshot and key files with inline content snippets.
- Tutorial set A (baseline pipeline) concatenated.
- Tutorial set B (deep_with_kb pipeline) concatenated.

Tasks:
1) Read the codebase digest to ground your judgments in actual code.
2) Read tutorial set A and tutorial set B.
3) Score each pipeline (A and B) on:
   - Fidelity: factual accuracy vs codebase
   - Pedagogy: clarity and structure
   - Coverage: completeness of key parts promised by the tutorials
4) Pick a winner (A, B, or tie).
5) Provide 2-4 citations referencing file paths and line ranges from the provided digest that support your decision (e.g., "app/api/routes/api.py:L10-L60").
6) Provide concise bullet-style advantages, drawbacks, and suggested improvements for each pipeline (A and B), grounded in the codebase digest. Keep each list to at most 4 short items.

Return only JSON (no code fences, no prose) in this exact shape:
{{
    "fidelity": {{"A": int, "B": int}},
    "pedagogy": {{"A": int, "B": int}},
    "coverage": {{"A": int, "B": int}},
    "winner": "A" | "B" | "tie",
    "rationale": "short string",
    "citations": ["path:line-range", ...],
    "advantages": {{"A": ["..."], "B": ["..."]}},
    "drawbacks": {{"A": ["..."], "B": ["..."]}},
    "improvements": {{"A": ["..."], "B": ["..."]}}
}}

Codebase Digest:
{codebase_digest}

Tutorials A (baseline):
{tutorial_a}

Tutorials B (deep_with_kb):
{tutorial_b}
"""


@dataclass
class PipelineBundle:
    codebase: str
    tutorials_a: str
    tutorials_b: str
    codebase_digest: str


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1000] + "\n... [truncated] ...\n" + text[-1000:]


def _read_concat(paths: Sequence[str], max_chars: int) -> str:
    parts: List[str] = []
    for path in paths:
        content = Path(path).read_text(encoding="utf-8")
        parts.append(f"# {Path(path).name}\n" + _truncate(content, max_chars))
    return "\n\n".join(parts)


def _is_valid_source(path: Path) -> bool:
    if any(
        part in {".git", "__pycache__", "node_modules", "venv", ".idea", ".vscode"}
        for part in path.parts
    ):
        return False
    if not path.is_file():
        return False
    if path.suffix.lower() not in {".py", ".md", ".txt"}:
        return False
    try:
        return path.stat().st_size <= 120_000
    except FileNotFoundError:
        return False


def _build_codebase_digest(
    codebase_root: Path, max_files: int = 12, max_chars_per_file: int = 1200
) -> str:
    files: List[Path] = []
    for path in sorted(codebase_root.rglob("*")):
        if _is_valid_source(path):
            files.append(path)
        if len(files) >= max_files:
            break

    parts: List[str] = []
    parts.append(f"Codebase: {codebase_root}")
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        parts.append(
            f"\n## {fp.relative_to(codebase_root)}\n"
            + _truncate(text, max_chars_per_file)
        )
    return "\n".join(parts)


def _load_bundles(
    bench_path: Path,
    tutorial_max_chars: int = TUTORIAL_MAX_CHARS,
    codebase_max_files: int = CODEBASE_MAX_FILES,
    codebase_max_chars: int = CODEBASE_MAX_CHARS,
) -> List[PipelineBundle]:
    data = json.loads(bench_path.read_text(encoding="utf-8"))
    grouped: Dict[str, Dict[str, Dict[str, Sequence[str]]]] = {}

    for entry in data.get("results", []):
        codebase = entry["codebase"]
        variant = entry["variant"]
        grouped.setdefault(codebase, {})[variant] = entry

    bundles: List[PipelineBundle] = []
    for codebase, variants in grouped.items():
        if "baseline" not in variants or "deep_with_kb" not in variants:
            logger.warning("Skipping %s: missing baseline or deep_with_kb", codebase)
            continue

        base_paths = variants["baseline"].get("tutorial_outputs", [])
        deep_paths = variants["deep_with_kb"].get("tutorial_outputs", [])
        if not base_paths or not deep_paths:
            logger.warning("Skipping %s: missing tutorial outputs", codebase)
            continue

        tutorials_a = _read_concat(base_paths, tutorial_max_chars)
        tutorials_b = _read_concat(deep_paths, tutorial_max_chars)
        digest = _build_codebase_digest(
            Path(codebase),
            max_files=codebase_max_files,
            max_chars_per_file=codebase_max_chars,
        )

        bundles.append(
            PipelineBundle(
                codebase=codebase,
                tutorials_a=tutorials_a,
                tutorials_b=tutorials_b,
                codebase_digest=digest,
            )
        )

    return bundles


def _judge(
    model: str, bundle: PipelineBundle, temperature: float, max_retries: int
) -> Dict:
    prompt = PROMPT_TEMPLATE.format(
        codebase_digest=bundle.codebase_digest,
        tutorial_a=bundle.tutorials_a,
        tutorial_b=bundle.tutorials_b,
    )
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            resp_dict = cast(Dict[str, Any], resp)
            choices = resp_dict.get("choices") or []
            if not choices:
                raise RuntimeError("Judge model returned no choices")
            message = cast(Dict[str, Any], choices[0].get("message", {}))
            content = str(message.get("content", "")).strip()
            if not content:
                raise RuntimeError("Judge model returned empty content")

            # Strip Markdown fences like ```json ... ``` if present
            if content.startswith("```"):
                # remove leading fence
                parts = content.split("\n", 1)
                content = parts[1] if len(parts) > 1 else ""
                if content.endswith("```"):
                    content = content.rsplit("```", 1)[0].strip()

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract the first JSON object if extra text remains
                match = re.search(r"\{.*\}", content, flags=re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                raise RuntimeError(f"Judge response was not valid JSON: {content}")
        except RateLimitError as exc:
            last_error = exc
            wait = min(5.0 * attempt, 20.0)
            logger.warning(
                "Rate limited on %s (attempt %d/%d); sleeping %.1fs",
                model,
                attempt,
                max_retries,
                wait,
            )
            time.sleep(wait)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_retries:
                raise
            wait = min(3.0 * attempt, 15.0)
            logger.warning(
                "Judge call failed on %s (attempt %d/%d); sleeping %.1fs: %s",
                model,
                attempt,
                max_retries,
                wait,
                exc,
            )
            time.sleep(wait)

    if last_error:
        raise last_error
    raise RuntimeError("Unknown judge failure")


def _write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _aggregate_results(results: List[Dict]) -> Dict:
    """Combine multiple judge samples into one aggregated record."""

    if not results:
        raise ValueError("No results to aggregate")

    n = len(results)

    def _avg_metric(key: str) -> Dict[str, float]:
        return {
            side: round(
                sum(r.get(key, {}).get(side, 0) for r in results) / n,
                2,
            )
            for side in ["A", "B"]
        }

    winner_counts = Counter(r.get("winner", "tie") for r in results)
    top_winner, top_count = winner_counts.most_common(1)[0]
    winner = top_winner if top_count > 1 or n == 1 else "tie"

    citations: List[str] = []
    seen = set()
    for r in results:
        for c in r.get("citations", []) or []:
            if c not in seen:
                seen.add(c)
                citations.append(c)

    base = results[0]
    return {
        "fidelity": _avg_metric("fidelity"),
        "pedagogy": _avg_metric("pedagogy"),
        "coverage": _avg_metric("coverage"),
        "winner": winner,
        "rationale": base.get("rationale", ""),
        "citations": citations,
        "advantages": base.get("advantages", {}),
        "drawbacks": base.get("drawbacks", {}),
        "improvements": base.get("improvements", {}),
    }


def _summarize(rows: List[Dict]) -> Dict:
    summary: Dict[str, Dict[str, int]] = {}
    for row in rows:
        model = row["model"]
        winner = row["winner"]
        summary.setdefault(model, {"A": 0, "B": 0, "tie": 0})
        summary[model][winner] = summary[model].get(winner, 0) + 1
    return summary


def _write_markdown_report(path: Path, rows: List[Dict], summary: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("# LLM Judge Report")
    models = list(summary.keys())
    if models:
        lines.append(f"\n- Models: {', '.join(models)}")
    codebases = sorted({row.get("codebase", "") for row in rows})
    if codebases:
        lines.append(f"- Codebases: {', '.join(codebases)}")

    lines.append("\n## Aggregate")
    lines.append("\n| Model | A Wins | B Wins | Ties |")
    lines.append("| --- | --- | --- | --- |")
    for model, counts in summary.items():
        lines.append(
            f"| {model} | {counts.get('A', 0)} | {counts.get('B', 0)} | {counts.get('tie', 0)} |"
        )

    lines.append("\n## Pipeline Scores")
    # Separate tables for clearer A/B reading
    lines.append("\n### Pipeline A (baseline)")
    lines.append(
        "\n| Codebase | Model | Samples | Fidelity A | Pedagogy A | Coverage A | Advantages A | Drawbacks A | Improvements A | Citations | Winner | Rationale |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    for row in rows:
        citations = "; ".join(row.get("citations", []))
        advantages = (
            row.get("advantages", {}) if isinstance(row.get("advantages"), dict) else {}
        )
        drawbacks = (
            row.get("drawbacks", {}) if isinstance(row.get("drawbacks"), dict) else {}
        )
        improvements = (
            row.get("improvements", {})
            if isinstance(row.get("improvements"), dict)
            else {}
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("codebase", "")),
                    str(row.get("model", "")),
                    str(row.get("samples", 1)),
                    str(row.get("fidelity", {}).get("A", "")),
                    str(row.get("pedagogy", {}).get("A", "")),
                    str(row.get("coverage", {}).get("A", "")),
                    "; ".join(advantages.get("A", [])),
                    "; ".join(drawbacks.get("A", [])),
                    "; ".join(improvements.get("A", [])),
                    citations,
                    str(row.get("winner", "")),
                    str(row.get("rationale", "")).replace("\n", " "),
                ]
            )
            + " |"
        )

    lines.append("\n### Pipeline B (deep_with_kb)")
    lines.append(
        "\n| Codebase | Model | Samples | Fidelity B | Pedagogy B | Coverage B | Advantages B | Drawbacks B | Improvements B | Citations | Winner | Rationale |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    for row in rows:
        citations = "; ".join(row.get("citations", []))
        advantages = (
            row.get("advantages", {}) if isinstance(row.get("advantages"), dict) else {}
        )
        drawbacks = (
            row.get("drawbacks", {}) if isinstance(row.get("drawbacks"), dict) else {}
        )
        improvements = (
            row.get("improvements", {})
            if isinstance(row.get("improvements"), dict)
            else {}
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("codebase", "")),
                    str(row.get("model", "")),
                    str(row.get("samples", 1)),
                    str(row.get("fidelity", {}).get("B", "")),
                    str(row.get("pedagogy", {}).get("B", "")),
                    str(row.get("coverage", {}).get("B", "")),
                    "; ".join(advantages.get("B", [])),
                    "; ".join(drawbacks.get("B", [])),
                    "; ".join(improvements.get("B", [])),
                    citations,
                    str(row.get("winner", "")),
                    str(row.get("rationale", "")).replace("\n", " "),
                ]
            )
            + " |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LLM-as-judge on tutorial pipelines"
    )
    parser.add_argument(
        "--bench", type=Path, default=Path("data/bench/bench_results.json")
    )
    parser.add_argument("--models", type=str, default="vertex_ai/gemini-2.5-pro")
    parser.add_argument(
        "--output", type=Path, default=Path("data/bench/llm_judge_results.jsonl")
    )
    parser.add_argument(
        "--summary", type=Path, default=Path("data/bench/llm_judge_summary.json")
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("data/bench/llm_judge_report.md"),
        help="Optional markdown report output",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    bundles = _load_bundles(args.bench)
    if not bundles:
        logger.error("No tutorial bundles found. Check bench file and variants.")
        return

    rows: List[Dict] = []
    for bundle in bundles:
        for model in models:
            logger.info("Judging pipeline A vs B on {} with {}", bundle.codebase, model)
            sample_results = [
                _judge(model, bundle, args.temperature, args.max_retries)
                for _ in range(max(1, SAMPLES))
            ]
            result = (
                sample_results[0]
                if len(sample_results) == 1
                else _aggregate_results(sample_results)
            )
            rows.append(
                {
                    "codebase": bundle.codebase,
                    "model": model,
                    "samples": len(sample_results),
                    "winner": result.get("winner", "tie"),
                    "fidelity": result.get("fidelity", {}),
                    "pedagogy": result.get("pedagogy", {}),
                    "coverage": result.get("coverage", {}),
                    "rationale": result.get("rationale", ""),
                    "citations": result.get("citations", []),
                    "advantages": result.get("advantages", {}),
                    "drawbacks": result.get("drawbacks", {}),
                    "improvements": result.get("improvements", {}),
                }
            )

    _write_jsonl(args.output, rows)
    summary = _summarize(rows)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.report:
        _write_markdown_report(args.report, rows, summary)
        logger.info("Report written to {}", args.report)

    logger.info("Judge results written to {}", args.output)
    logger.info("Summary written to {}", args.summary)


if __name__ == "__main__":
    main()
