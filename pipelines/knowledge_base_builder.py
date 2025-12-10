"""Build the knowledge base for a codebase using sub-agents."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, cast

from dotenv import load_dotenv
from loguru import logger

from toolkits.sub_agent_toolkit import (
    SubAgentRole,
    SubAgentTaskSpec,
    SubAgentOutputError,
    run_typed_sub_agent_tasks,
)
from prompts import prompts
from utils.path_utils import ensure_directory

__all__ = ["KnowledgeBaseBuilder", "DocumentationTarget", "AgentWorkspaceResult"]

load_dotenv()

CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
KNOWLEDGE_BASE_OUTPUT_PATH = os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
SUB_AGENTS_ROOT_PATH = os.getenv("SUB_AGENTS_ROOT_PATH")
TUTORIAL_OUTPUT_PATH = os.getenv("TUTORIAL_OUTPUT_PATH")
DEFAULT_BASE_ROOT = Path("data/agent_workspace").expanduser().resolve()
KNOWLEDGE_BASE_STEP_DELAY_SECONDS_ENV = "KNOWLEDGE_BASE_STEP_DELAY_SECONDS"
KNOWLEDGE_BASE_MAX_TARGETS_ENV = "KNOWLEDGE_BASE_MAX_TARGETS"
DEFAULT_KB_STEP_DELAY_SECONDS = 0.0
DEFAULT_SUB_AGENT_MIN_INTERVAL = 5.0
DEFAULT_ANCHOR_TOOL_CALLS = 5
DEFAULT_ANCHOR_DIRECTORY_LISTINGS = 0
MAX_FOCUS_FILES = 2  # keep KB focused and concise
FOCUS_KEYWORDS: tuple[str, ...] = (
    "router",
    "routes",
    "api",
    "controller",
    "service",
    "handler",
    "model",
    "models",
    "schema",
    "schemas",
    "db",
    "database",
    "config",
    "settings",
    "dependency",
    "tests",
    "test",
)

# Directories to ignore during scanning
_IGNORED_SCAN_DIRS = {
    "node_modules",
    "venv",
    "env",
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "dist",
    "build",
    "site-packages",
    "htmlcov",
    ".mypy_cache",
}

TARGET_WHITELIST_ENV = "KNOWLEDGE_BASE_TARGET_WHITELIST"

# Curated defaults cover the major RealWorld-style domains we document most.
# Support both src/ and app/ directory structures.
DEFAULT_TARGET_IDENTIFIERS: tuple[str, ...] = (
    "README.md",
    "src/api",
    "src/models",
    "app/api",
    "app/models",
    "tests",
    "scripts",
)

# Soft priority order for planner/fallback trimming
PRIORITIZED_TARGETS: tuple[str, ...] = (
    "README.md",
    "src/api",
    "src/models",
    "src/config",
    "src/utils",
    "app/api",
    "app/models",
    "app/services",
    "app/core",
    "app/db",
    "tests",
    "scripts",
    "postman",
)

MIN_PLANNER_TARGETS = 4
MAX_PLANNER_TARGETS = 8  # increased for better codebase coverage


@dataclass(frozen=True)
class DocumentationTarget:
    path: Path
    label: str

    @property
    def identifier(self) -> str:
        # Sanitize path for use as a filename/directory name
        safe = str(self.path).replace(os.sep, "_").replace("/", "_").replace("\\", "_")
        return safe if safe else "root"


@dataclass(frozen=True)
class AgentWorkspaceResult:
    index: int
    target: DocumentationTarget
    workspace: Path | None
    error: str | None = None


class KnowledgeBaseBuilder:
    def __init__(
        self,
        codebase_root: str | Path | None = None,
        output_root: str | Path | None = None,
        sub_agents_root: str | Path | None = None,
        dry_run: bool = False,
        force_rebuild: bool = False,  # NEW: Force regeneration of all targets
        step_delay_seconds: float | None = None,
        max_targets: int | None = None,
    ):
        env_codebase = (
            codebase_root or os.getenv("CODEBASE_ROOT_PATH") or DEFAULT_BASE_ROOT
        )
        env_output = (
            output_root
            or os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
            or (DEFAULT_BASE_ROOT / "knowledge_base")
        )
        env_sub_agents = (
            sub_agents_root
            or os.getenv("SUB_AGENTS_ROOT_PATH")
            or (DEFAULT_BASE_ROOT / "sub_agents_workspace")
        )

        self.dry_run = dry_run
        self.force_rebuild = force_rebuild

        self.codebase_root = Path(env_codebase).expanduser().resolve()
        self.output_root = ensure_directory(env_output)
        self.sub_agents_root = ensure_directory(env_sub_agents)
        tutorial_output_value = (
            Path(TUTORIAL_OUTPUT_PATH).expanduser().resolve()
            if TUTORIAL_OUTPUT_PATH
            else (DEFAULT_BASE_ROOT / "tutorials")
        )
        self.tutorial_output_root = tutorial_output_value
        self.plan_path = self.output_root / "plan.md"
        self._plan_state: Dict[str, Dict[str, str]] = {}
        self._focus_files_cache: Dict[str, List[str]] = {}
        self._max_tool_calls = DEFAULT_ANCHOR_TOOL_CALLS
        self._max_directory_calls = DEFAULT_ANCHOR_DIRECTORY_LISTINGS
        self._step_delay_seconds = self._resolve_float_option(
            step_delay_seconds,
            KNOWLEDGE_BASE_STEP_DELAY_SECONDS_ENV,
            default=DEFAULT_KB_STEP_DELAY_SECONDS,
            minimum=0.0,
        )
        self._max_targets = self._resolve_optional_int_option(
            max_targets,
            KNOWLEDGE_BASE_MAX_TARGETS_ENV,
            minimum=1,
            default=MAX_PLANNER_TARGETS,
        )
        self._scouting_tree: str = ""
        self._context_summary: str = ""

        if not self.codebase_root.exists():
            raise FileNotFoundError(
                f"Codebase root does not exist: {self.codebase_root}"
            )

    def generate(self) -> List[Path]:
        logger.info("Starting knowledge base generation from {}", self.codebase_root)

        # Now it is safe to reset directories
        if not self.dry_run:
            self._reset_directory(self.sub_agents_root)
            self._reset_directory(self.output_root)
            self._clear_rag_vector_store()

        self.output_root.mkdir(parents=True, exist_ok=True)

        # Step 1: Exploratory pass to understand codebase structure
        exploratory_path, context_summary = self._run_exploratory_pass()
        self._context_summary = context_summary

        # Step 2: Let planner agent decide which folders to document
        targets = self._run_planner_agent(context_summary)
        targets = self._apply_target_cap(targets)
        if not targets:
            raise RuntimeError(
                "Planner agent did not select any documentation targets."
            )

        logger.info("Planner selected {} targets for documentation", len(targets))

        self._initialize_plan(targets)

        results: List[AgentWorkspaceResult] = []
        skipped_count = 0

        for index, target in enumerate(targets):
            if self.dry_run:
                logger.debug(
                    "[DRY RUN] Would spawn analyzer agent for target: {}", target.path
                )
                continue

            # CHECKPOINT: Skip if target hasn't changed
            if not self.force_rebuild and not self._should_regenerate_target(target):
                logger.debug("Skipping {} (up-to-date)", target.path)
                skipped_count += 1
                self._mark_task_complete(target, 0)  # Mark as complete but cached
                continue

            logger.debug("Analyzing {} (changed or new)...", target.path)

            try:
                workspace = self._run_single_target_agent(target, context_summary)
                results.append(
                    AgentWorkspaceResult(
                        index=index,
                        target=target,
                        workspace=workspace,
                        error=None,
                    )
                )
            except Exception as exc:
                logger.exception("Analyzer failed for %s: %s", target.path, exc)
                results.append(
                    AgentWorkspaceResult(
                        index=index,
                        target=target,
                        workspace=None,
                        error=str(exc),
                    )
                )

        # Checkpoint Summary
        logger.info(
            "Checkpoint: analyzed=%d cached=%d total=%d",
            len(results),
            skipped_count,
            len(targets),
        )

        if self.dry_run:
            logger.debug("[DRY RUN] Skipping result collection and summarization.")
            return [exploratory_path] if exploratory_path else []

        if not results and skipped_count == 0:
            raise RuntimeError("Sub-agents did not produce any workspaces.")

        output_files: List[Path] = []
        if exploratory_path:
            output_files.append(exploratory_path)

        output_files.extend(self._collect_outputs(results))

        if self.plan_path.exists():
            output_files.append(self.plan_path)

        summary_path = self._run_summary_agent(output_files)
        if summary_path:
            output_files.append(summary_path)

        logger.info("Knowledge base generated with {} files", len(output_files))
        return sorted(set(output_files), key=lambda path: path.name)

    def generate_with_supervisor(self) -> List[Path]:
        """Generate knowledge base using the Supervisor Agent.
        
        The Supervisor Agent handles planning, sub-agent coordination, output
        evaluation, and retries autonomously.
        """
        logger.info("Starting supervised knowledge base generation from {}", self.codebase_root)
        
        # Check existing content
        if not self.force_rebuild and self.output_root.exists():
            existing_files = list(self.output_root.glob("*.md"))
            if existing_files:
                logger.info("KB exists at {} ({} files). Skipping rebuild.", self.output_root, len(existing_files))
                return sorted(existing_files, key=lambda p: p.name)
        
        # Reset directories
        if not self.dry_run:
            self._reset_directory(self.sub_agents_root)
            self._reset_directory(self.output_root)
            self._clear_rag_vector_store()
        
        self.output_root.mkdir(parents=True, exist_ok=True)
        
        if self.dry_run:
            logger.debug("[DRY RUN] Would run Supervisor Agent")
            return []
        
        # Create and run Supervisor Agent
        supervisor = self._create_supervisor_agent()
        task = f"""Create a comprehensive Knowledge Base for tutorial generation.

TARGET CODEBASE: {self.codebase_root}

GOAL: Generate documentation that enables high-quality tutorial creation. The Knowledge Base must provide information that a tutorial writer cannot easily derive from raw code alone.

REQUIRED DIFFERENTIATORS (include in custom_instructions for each sub-agent):
1. Entry Points - Where to start reading, initialization order
2. Key Concepts - Define domain terms (Repository, DTO, Service, etc.)
3. Dependencies & Relationships - What calls what (e.g., "Service → Repository → DB")
4. Patterns & Conventions - Cross-cutting concerns, error handling, naming conventions
5. Code Examples - Annotated snippets with "Why this matters" explanations
6. Tutorial Hints - Common questions, pitfalls, prerequisites

WORKFLOW:
1. Scout the codebase structure first (get_codebase_overview)
2. Identify ALL meaningful directories (app, tests, scripts, config, docs, etc.)
3. Spawn sub-agents with specific custom_instructions for each target
4. Evaluate each output for quality and required sections
5. Retry with feedback if sections are missing
6. Finalize by collecting all successful outputs

QUALITY STANDARD: Each documentation file must have all 7 sections. Reject and retry if incomplete.
"""
        
        # Retry loop for rate limits
        import time
        retry_delay = 5.0
        attempt = 0
        
        while True:
            attempt += 1
            try:
                result = supervisor.run(task)
                logger.info("Supervisor Agent completed: {}", str(result)[:200])
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = "rate" in error_str or "429" in error_str or "exhausted" in error_str
                
                if is_rate_limit:
                    logger.warning(
                        "Rate limit hit (attempt {}). Waiting {}s before retry...",
                        attempt, retry_delay
                    )
                    time.sleep(retry_delay)
                else:
                    logger.exception("Supervisor Agent failed: {}", e)
                    raise RuntimeError(f"Supervisor Agent failed: {e}") from e
        
        # Collect output files from supervisor
        output_files = list(self.output_root.glob("*.md"))
        
        # Run summary agent to create executive_summary.md for tutorial generator
        if output_files:
            summary_path = self._run_summary_agent(output_files)
            if summary_path:
                output_files.append(summary_path)
        
        logger.info("Knowledge base generated with {} files", len(output_files))
        return sorted(output_files, key=lambda p: p.name)

    def _create_supervisor_agent(self):
        """Create the Supervisor Agent with its tools."""
        from smolagents import ToolCallingAgent
        from toolkits.supervisor_toolkit import build_supervisor_tools
        from utils.llm_factory import create_model

        tools = build_supervisor_tools(
            codebase_root=str(self.codebase_root),
            sub_agents_root=str(self.sub_agents_root),
            output_root=str(self.output_root),
        )

        model = create_model()

        return ToolCallingAgent(
            name="knowledge_base_supervisor",
            description="Supervises and coordinates knowledge base generation",
            tools=tools,
            model=model,
            instructions=prompts.SUPERVISOR_AGENT_PROMPT,
        )

    # ----- Target discovery -------------------------------------------------

    def _run_exploratory_pass(self) -> tuple[Path | None, str]:
        logger.debug("Running exploratory pass for codebase snapshot")
        report_path = self.output_root / "scouting_report.md"

        try:
            tree = self._build_directory_tree(self.codebase_root, max_depth=2)
        except Exception as exc:
            logger.warning("Failed to build directory tree: %s", exc)
            tree = "(unable to generate tree view)"

        self._scouting_tree = tree

        top_level_summary = self._summarize_top_level_directories()
        readme_excerpt = self._read_file_excerpt(self.codebase_root / "README.md")
        requirements_excerpt = self._read_file_excerpt(
            self.codebase_root / "requirements.txt"
        )
        if not requirements_excerpt:
            # Try pyproject.toml as fallback
            requirements_excerpt = self._read_file_excerpt(
                self.codebase_root / "pyproject.toml"
            )

        lines = [
            "# Exploratory Scouting Report",
            "",
            "Generated before launching analyzer sub-agents to capture a high-level snapshot of the repository.",
            "",
            "## Top-Level Structure",
            "```markdown",
            tree.strip(),
            "```",
        ]

        if top_level_summary:
            lines.extend(["", "## First-Level Directories of `src/`", ""])
            lines.extend(f"- {entry}" for entry in top_level_summary)

        if readme_excerpt:
            lines.extend(
                ["", "## README.md (excerpt)", "", "```markdown", readme_excerpt, "```"]
            )

        if requirements_excerpt:
            lines.extend(
                [
                    "",
                    "## Dependency Config (excerpt)",
                    "",
                    "```text",
                    requirements_excerpt,
                    "```",
                ]
            )

        lines.append("")

        if not self.dry_run:
            report_path.write_text("\n".join(lines), encoding="utf-8")

        # Context summary for agents
        context_summary = (
            f"Codebase Structure:\n{tree}\n\n"
            f"Top-level directories: {', '.join(top_level_summary) if top_level_summary else 'None'}\n"
        )
        if readme_excerpt:
            context_summary += f"\nREADME excerpt:\n{readme_excerpt[:500]}...\n"

        return report_path, context_summary

    def _run_planner_agent(self, context_summary: str) -> List[DocumentationTarget]:
        """Run planner agent to intelligently select documentation targets."""
        logger.debug("Running planner agent to select documentation targets...")

        # Build planner task
        scout_tree = self._scouting_tree or "(scout tree unavailable)"
        report_hint = (self.output_root / "scouting_report.md").as_posix()
        task = (
            "You already have a scouting snapshot of the repository. Reuse it to avoid extra directory calls.\n"
            f"Scouting report path: {report_hint}\n"
            "Key tree excerpt (depth 2):\n"
            f"```markdown\n{scout_tree}\n```\n\n"
            f"{context_summary}\n\n"
            "Based ONLY on this snapshot plus targeted file reads, select 3-6 distinct folders/files that should be documented. Prioritize the defaults (README, src/api, src/models, tests) and stop once you have at most six.\n"
            "Return ONLY a JSON array of relative paths, nothing else."
        )

        # Create simple planner agent (no tools needed, just decision)
        from smolagents import LiteLLMModel, ToolCallingAgent
        from toolkits.sub_agent_toolkit import LITELLM_MODEL_ID, LITELLM_API_KEY
        from toolkits.scoped_filesystem_toolkit import build_scoped_tools

        # Give planner a temporary workspace for tools (even if it doesn't write)
        planner_workspace = self.sub_agents_root / "planner"
        self._reset_directory(planner_workspace)

        planner_tools = build_scoped_tools(
            codebase_root=str(self.codebase_root),
            workspace_root=str(planner_workspace),
            allow_directory_listing=False,
            allow_tree=False,
            allow_mermaid=False,
            allow_writes=False,
        )
        # Filter out writing tools to keep it read-only
        planner_tools = [t for t in planner_tools if "write" not in t.name]

        model = LiteLLMModel(model_id=LITELLM_MODEL_ID, api_key=LITELLM_API_KEY)
        planner = ToolCallingAgent(
            name="documentation_planner",
            description="Selects which parts of codebase to document",
            tools=planner_tools,
            model=model,
            instructions=prompts.PLANNER_AGENT_PROMPT,
        )

        try:
            response = planner.run(task)
            response_text = str(response)

            # Extract JSON array from response
            import json
            import re

            # Try to find JSON array in response
            json_match = re.search(r"\[.*?\]", response_text, re.DOTALL)
            if not json_match:
                logger.warning(
                    "Planner output has no JSON array, falling back to heuristic"
                )
                return self._fallback_target_selection()

            selected_paths = json.loads(json_match.group(0))

            if not isinstance(selected_paths, list) or not selected_paths:
                logger.warning("Invalid planner response, using fallback")
                return self._fallback_target_selection()

            # Convert to DocumentationTarget objects
            targets = []
            for path_str in selected_paths:
                relative_path = Path(path_str)
                absolute_path = (self.codebase_root / relative_path).resolve()

                if not absolute_path.exists():
                    logger.warning(
                        f"Planner selected non-existent path: {path_str}, skipping"
                    )
                    continue

                label = relative_path.name or relative_path.as_posix()
                targets.append(DocumentationTarget(path=relative_path, label=label))

            normalized = self._normalize_planner_targets(targets)
            if len(normalized) < MIN_PLANNER_TARGETS:
                logger.warning(
                    "Planner produced fewer than %d targets; using fallback selection.",
                    MIN_PLANNER_TARGETS,
                )
                return self._fallback_target_selection()

            return normalized

        except Exception as exc:
            logger.exception(f"Planner agent failed: {exc}")
            logger.warning("Falling back to heuristic target selection")
            return self._fallback_target_selection()

    def _normalize_planner_targets(
        self, targets: Sequence[DocumentationTarget]
    ) -> List[DocumentationTarget]:
        if not targets:
            return []

        seen: set[str] = set()
        normalized: List[DocumentationTarget] = []
        for target in targets:
            key = target.path.as_posix()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(target)

        normalized.sort(key=self._target_priority)

        cap = self._max_targets or MAX_PLANNER_TARGETS
        if len(normalized) > cap:
            normalized = normalized[:cap]

        if len(normalized) < MIN_PLANNER_TARGETS:
            fallback_candidates = self._discover_targets()
            for candidate in fallback_candidates:
                key = candidate.path.as_posix()
                if key in seen:
                    continue
                normalized.append(candidate)
                seen.add(key)
                if len(normalized) >= MIN_PLANNER_TARGETS:
                    break

        return normalized

    def _target_priority(self, target: DocumentationTarget) -> tuple[int, int, str]:
        path_str = target.path.as_posix()
        if path_str in PRIORITIZED_TARGETS:
            return (0, PRIORITIZED_TARGETS.index(path_str), path_str)

        lower = path_str.lower()
        if "api" in lower or "routes" in lower:
            return (1, len(path_str), path_str)
        if "model" in lower:
            return (2, len(path_str), path_str)
        if lower.startswith("tests") or "test" in lower:
            return (3, len(path_str), path_str)
        return (4, len(path_str), path_str)

    def _fallback_target_selection(self) -> List[DocumentationTarget]:
        """Simple heuristic if planner fails."""
        identifiers = self._resolve_target_identifiers()
        targets: List[DocumentationTarget] = []
        for ident in identifiers:
            rel_path = Path(ident)
            abs_path = (self.codebase_root / rel_path).resolve()
            if abs_path.exists():
                targets.append(DocumentationTarget(path=rel_path, label=rel_path.name))

        if len(targets) < MIN_PLANNER_TARGETS:
            discovered = self._discover_targets()
            seen = {t.path.as_posix() for t in targets}
            for candidate in discovered:
                key = candidate.path.as_posix()
                if key in seen:
                    continue
                targets.append(candidate)
                seen.add(key)
                if len(targets) >= MIN_PLANNER_TARGETS:
                    break

        normalized = self._normalize_planner_targets(targets)
        capped = self._apply_target_cap(normalized)
        return capped

    def _discover_targets(self) -> List[DocumentationTarget]:
        identifiers = self._resolve_target_identifiers()

        if not identifiers:
            identifiers = self._scan_for_targets()
            logger.debug("Discovered %d targets dynamically.", len(identifiers))

        targets: List[DocumentationTarget] = []
        for identifier in identifiers:
            relative_path = Path(identifier)
            # Safety check: ensure target is actually inside codebase
            try:
                absolute_path = (self.codebase_root / relative_path).resolve()
                if not str(absolute_path).startswith(str(self.codebase_root)):
                    logger.warning(
                        f"Target {identifier} resolves outside codebase root. Skipping."
                    )
                    continue
            except Exception:
                continue

            if not absolute_path.exists():
                logger.debug(
                    "Skipping target %s because it does not exist.", identifier
                )
                continue

            label = relative_path.name or relative_path.as_posix()
            targets.append(DocumentationTarget(path=relative_path, label=label))

        return targets

    def _resolve_target_identifiers(self) -> List[str]:
        """Return curated target identifiers, honoring an optional whitelist env."""
        env_value = os.getenv(TARGET_WHITELIST_ENV)
        if not env_value:
            return list(DEFAULT_TARGET_IDENTIFIERS)

        # Allow comma or newline separated values and trim whitespace/duplications.
        raw_entries = env_value.replace("\n", ",").split(",")
        seen: set[str] = set()
        identifiers: List[str] = []
        for entry in raw_entries:
            cleaned = entry.strip().strip("/")
            if not cleaned:
                continue
            normalized = cleaned.replace("\\", "/")
            if normalized not in seen:
                identifiers.append(normalized)
                seen.add(normalized)
        return identifiers or list(DEFAULT_TARGET_IDENTIFIERS)

    def _scan_for_targets(self) -> List[str]:
        src_root = self.codebase_root / "src"
        scan_root = (
            src_root if src_root.exists() and src_root.is_dir() else self.codebase_root
        )

        targets = []
        # Always include README if it exists
        if (self.codebase_root / "README.md").exists():
            targets.append("README.md")

        # Always include explicit tests folder if present
        if (self.codebase_root / "tests").exists():
            targets.append("tests")

        for item in scan_root.iterdir():
            if item.name.startswith(".") or item.name.startswith("_"):
                continue
            if item.name in _IGNORED_SCAN_DIRS:
                continue

            # If scanning root, ignore miscellaneous files (e.g. .gitignore, setup.py)
            # We want to focus on Directories for sub-agents to analyze.
            if scan_root == self.codebase_root and item.is_file():
                continue

            try:
                rel_path = item.relative_to(self.codebase_root).as_posix()
                # Avoid duplicates
                if rel_path not in targets:
                    targets.append(rel_path)
            except ValueError:
                continue

        return sorted(targets)

    # ----- Task construction ------------------------------------------------

    def _get_focus_files(self, target: DocumentationTarget) -> List[str]:
        cache_key = target.identifier
        if cache_key not in self._focus_files_cache:
            self._focus_files_cache[cache_key] = self._select_representative_files(
                target
            )
        return self._focus_files_cache[cache_key]

    def _determine_tool_budget(
        self, target: DocumentationTarget
    ) -> tuple[int | None, int | None]:
        focus_count = len(self._get_focus_files(target))
        total_budget = self._max_tool_calls
        if total_budget is not None:
            minimum_reads = max(focus_count, 1)
            total_budget = max(total_budget, minimum_reads * 2 + 3)
        return total_budget, self._max_directory_calls

    def _select_representative_files(
        self, target: DocumentationTarget, max_files: int = MAX_FOCUS_FILES
    ) -> List[str]:
        absolute = (self.codebase_root / target.path).resolve()

        if absolute.is_file():
            return [target.path.as_posix()]
        if not absolute.exists() or not absolute.is_dir():
            return []

        candidates: List[tuple[int, int, str]] = []
        stack: List[tuple[Path, int]] = [(absolute, 0)]

        while stack:
            current, depth = stack.pop()
            if depth > 2:
                continue
            try:
                entries = sorted(
                    child
                    for child in current.iterdir()
                    if not child.name.startswith(".")
                    and child.name not in _IGNORED_SCAN_DIRS
                )
            except OSError:
                continue

            for child in entries:
                if child.is_dir():
                    if depth + 1 <= 2:
                        stack.append((child, depth + 1))
                    continue
                if child.name == "__init__.py":
                    continue
                relative = child.relative_to(self.codebase_root).as_posix()
                score = self._score_focus_file(child.name, depth)
                candidates.append((score, depth, relative))

            if len(candidates) >= max_files * 5:
                break

        if not candidates:
            try:
                fallback = [
                    child.relative_to(self.codebase_root).as_posix()
                    for child in absolute.iterdir()
                    if child.is_file() and child.name != "__init__.py"
                ][:max_files]
                return fallback
            except OSError:
                return []

        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [relative for _, _, relative in candidates[:max_files]]

    @staticmethod
    def _score_focus_file(filename: str, depth: int) -> int:
        lower = filename.lower()
        score = 1
        for weight, keyword in enumerate(FOCUS_KEYWORDS[::-1], start=1):
            if keyword in lower:
                score += weight * 10
                break
        if lower.endswith("__init__.py"):
            score += 4
        if lower.startswith("test") or lower.endswith("test.py"):
            score += 6
        return max(score - depth, 1)

    def _build_task_description(
        self, target: DocumentationTarget, context_summary: str = ""
    ) -> str:
        relative = target.path.as_posix()
        directory_hint = (
            relative if target.path.suffix == "" else target.path.parent.as_posix()
        )
        directory_hint = directory_hint or "."

        sections = [
            "- Open with context: why this area exists and when a tutorial author would reach for it.",
            "- Describe architecture, dependencies, and control flow, weaving in code references with relative paths and line ranges.",
            "- Surface the primary entrypoints (classes, functions, CLI, routes) alongside parameters, error handling, and extension seams.",
            "- Capture configuration, environment contracts, and external services or data stores this code touches.",
            "- Explain how to exercise or test the feature (fixtures, CLI commands, HTTP calls) so future guides can reuse the steps.",
            "- Call out risks, gotchas, or follow-up work tutorial agents should remember when teaching this portion of the system.",
        ]

        focus_files = self._get_focus_files(target)
        if focus_files:
            focus_lines = "\n".join(f"- `{path}`" for path in focus_files)
            focus_section = (
                "Focus files (ONLY call `read_codebase_file` on these paths):\n"
                f"{focus_lines}\n"
            )
        else:
            focus_section = "Focus files (none provided):\n- Read the primary target path directly and reuse the scouting summaries.\n"

        instructions = "\n".join(sections)
        tool_constraints = (
            "You have access to `read_codebase_file` for the listed focus files and `write_workspace_file` for outputs. "
            "Directory listing tools are disabled—do not attempt to explore beyond the provided files. Keep the writeup high-level (aim < ~600 words) and cite only short code snippets with line ranges. Diagrams are NOT required for the knowledge base."
        )
        return (
            f"Analyze the path `{relative}` within the codebase. Focus on files under `{directory_hint}`.\n"
            "Use descriptive markdown headings for each theme above so the output is ready for downstream tutorials."
            " Favor paragraphs with short, labeled code snippets over bullet dumps, and cite files like `src/api/routes.py#L42`. Keep summaries concise and architectural."
            " Save your main report as `summary.md` inside your workspace.\n"
            f"Directory hints: {directory_hint}.\n"
            f"{focus_section}"
            f"Tool constraints: {tool_constraints}\n"
            f"Module label: {target.label}.\n"
            f"Global Context:\n{context_summary}\n"
            f"Checklist:\n{instructions}"
        )

    # ----- Aggregation ------------------------------------------------------

    def _collect_outputs(self, results: Sequence[AgentWorkspaceResult]) -> List[Path]:
        output_files: List[Path] = []

        for result in results:
            target = result.target
            workspace = result.workspace

            if not workspace or not workspace.exists():
                logger.warning(f"No workspace found for {target.path}")
                self._mark_task_attention(target, "Agent failed to create workspace")
                continue

            exported = self._export_workspace_markdown(target, workspace)

            if exported:
                output_files.extend(exported)
                self._mark_task_complete(target, len(exported))
                continue

            # Retry logic
            error_detail = result.error or "Empty output"
            logger.warning(f"Retrying {target.path} (Reason: {error_detail})")

            retry_workspace = self._retry_target_workspace(target)
            if retry_workspace:
                exported_retry = self._export_workspace_markdown(
                    target, retry_workspace
                )
                if exported_retry:
                    output_files.extend(exported_retry)
                    self._mark_task_complete(target, len(exported_retry))
                    continue

            self._mark_task_attention(target, f"Failed after retry: {error_detail}")

        return output_files

    def _run_single_target_agent(
        self, target: DocumentationTarget, context_summary: str = ""
    ) -> Path | None:
        """Run a single target analyzer with output validation and retry."""
        max_retries = 2
        last_error: str | None = None
        
        for attempt in range(max_retries + 1):
            workspace_root = self.sub_agents_root / target.identifier
            if attempt > 0:
                # Use distinct directory for retries
                workspace_root = self.sub_agents_root / f"retry_{attempt}_{target.identifier}"
            self._reset_directory(workspace_root)
            
            # Build task description with retry feedback if needed
            task_desc = self._build_task_description(target, context_summary)
            if attempt > 0 and last_error:
                task_desc += (
                    f"\n\n⚠️ RETRY {attempt}/{max_retries}: Previous attempt failed: {last_error}\n"
                    "You MUST write substantial markdown content (100+ chars) to your workspace.\n"
                    "Do NOT write empty files or placeholder text."
                )
            
            spec = SubAgentTaskSpec(
                description=task_desc,
                role=SubAgentRole.ANALYZER,
            )
            total_budget, directory_budget = self._determine_tool_budget(target)
            
            try:
                workspaces = run_typed_sub_agent_tasks(
                    [spec],
                    codebase_root=self.codebase_root,
                    sub_agents_root=workspace_root,
                    min_interval_seconds=self._sub_agent_min_interval(),
                    max_tool_calls=total_budget,
                    max_directory_calls=directory_budget,
                )
                
                if not workspaces:
                    last_error = "No workspace returned"
                    logger.warning(f"Attempt {attempt + 1}/{max_retries + 1}: {last_error}")
                    continue
                
                workspace = workspaces[0]
                
                # Validate workspace has meaningful output
                self._validate_workspace_output(workspace)
                
                return workspace
                
            except SubAgentOutputError as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} validation failed: {e}")
                if attempt >= max_retries:
                    raise
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}")
                if attempt >= max_retries:
                    raise
        
        return None

    def _validate_workspace_output(self, workspace: Path, min_chars: int = 100) -> None:
        """Validate that workspace contains meaningful output files."""
        md_files = list(workspace.glob("*.md"))
        if not md_files:
            raise SubAgentOutputError(f"No markdown files in {workspace.name}")
        
        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8").strip()
            if len(content) < min_chars:
                raise SubAgentOutputError(
                    f"{md_file.name}: {len(content)} chars < {min_chars} required"
                )
            if content.lower() in ("_no response_", "no response"):
                raise SubAgentOutputError(f"Placeholder content in {md_file.name}")

    def _retry_target_workspace(self, target: DocumentationTarget) -> Path | None:
        # Use a distinct directory for retries to avoid file lock issues
        retry_root = self.sub_agents_root / f"retry_{target.identifier}"
        self._reset_directory(retry_root)

        specs = [
            SubAgentTaskSpec(
                description=f"{self._build_task_description(target)}\n\nIMPORTANT: Previous attempt failed. Be extremely verbose.",
                role=SubAgentRole.ANALYZER,
            )
        ]
        total_budget, directory_budget = self._determine_tool_budget(target)

        workspaces = run_typed_sub_agent_tasks(
            specs,
            codebase_root=self.codebase_root,
            sub_agents_root=retry_root,
            min_interval_seconds=self._sub_agent_min_interval(),
            max_tool_calls=total_budget,
            max_directory_calls=directory_budget,
        )
        return workspaces[0] if workspaces else None

    def _write_overview(
        self, targets: Sequence[DocumentationTarget], output_files: Sequence[Path]
    ) -> Path:
        overview_path = self.output_root / "overview.md"
        lines = [
            "# Codebase Overview",
            "",
            "This knowledge base was generated automatically.",
            "",
            "## Covered Areas",
        ]
        for target in targets:
            lines.append(f"- `{target.path.as_posix()}`")

        lines.append("")
        if output_files:
            lines.append("## Artifact Index")
            for path in sorted(output_files, key=lambda p: p.name):
                lines.append(f"- [{path.name}]({path.name})")

        overview_path.write_text("\n".join(lines), encoding="utf-8")
        return overview_path

    def _write_table_of_contents(self, output_files: Sequence[Path]) -> Path:
        toc_path = self.output_root / "toc.md"
        lines = ["# Knowledge Base Table of Contents", ""]
        for file_path in sorted(output_files, key=lambda p: p.name):
            if file_path.name == "toc.md":
                continue
            lines.append(f"- [{file_path.stem}]({file_path.name})")
        toc_path.write_text("\n".join(lines), encoding="utf-8")
        return toc_path

    def _export_workspace_markdown(
        self, target: DocumentationTarget, workspace: Path
    ) -> List[Path]:
        markdown_files = sorted(workspace.rglob("*.md"))
        if not markdown_files:
            return []

        exported: List[Path] = []
        for file_path in markdown_files:
            content = file_path.read_text(encoding="utf-8")
            if not self._has_meaningful_content(content):
                continue

            clean_identifier = target.identifier
            if clean_identifier.endswith(".md"):
                clean_identifier = clean_identifier[:-3]

            output_name = f"{clean_identifier}.md"
            output_path = self.output_root / output_name

            try:
                output_path.write_text(content, encoding="utf-8")
                exported.append(output_path)
            except Exception as e:
                logger.error(f"Failed to export {output_name}: {e}")

            # Keep only the first meaningful markdown per target to cap KB size
            if exported:
                break

        return exported

    # ... [Keep existing summary agent logic, plan init, marking tasks logic] ...

    def _run_summary_agent(self, artifact_paths: Sequence[Path]) -> Path | None:
        if not artifact_paths:
            return None
        summary_root = self.sub_agents_root / "summary_agent"
        self._reset_directory(summary_root)

        workspaces = run_typed_sub_agent_tasks(
            [
                SubAgentTaskSpec(
                    description=self._build_summary_task_description(artifact_paths),
                    role=SubAgentRole.SUMMARIZER,
                )
            ],
            codebase_root=self.output_root,
            sub_agents_root=summary_root,
            min_interval_seconds=self._sub_agent_min_interval(),
        )
        if not workspaces:
            return None

        # Check for output file - summarizer may write summary.md or executive_summary.md
        workspace = workspaces[0]
        possible_names = ["executive_summary.md", "summary.md"]
        
        for name in possible_names:
            src = workspace / name
            if src.exists():
                dest = self.output_root / "executive_summary.md"
                dest.write_text(src.read_text("utf-8"), "utf-8")
                logger.info("Copied {} to {}", src, dest)
                return dest
        
        logger.warning("Summary agent did not produce executive_summary.md or summary.md")
        return None

    def _build_summary_task_description(self, artifact_paths: Sequence[Path]) -> str:
        files = "\n".join(f"- {p.name}" for p in artifact_paths)
        return f"Summarize these Knowledge Base files into an executive_summary.md:\n{files}"

    # ... [Helper methods kept mostly as is, just ensuring types] ...

    def _initialize_plan(self, targets: Sequence[DocumentationTarget]) -> None:
        self._plan_state = {
            t.identifier: {
                "path": t.path.as_posix(),
                "label": t.label,
                "status": " ",
                "note": "",
            }
            for t in targets
        }
        for target in targets:
            self._get_focus_files(target)
        self._write_plan_file()

    def _mark_task_complete(self, target: DocumentationTarget, count: int) -> None:
        if target.identifier in self._plan_state:
            self._plan_state[target.identifier].update(
                {"status": "x", "note": f"Files: {count}"}
            )
            self._write_plan_file()

    def _mark_task_attention(self, target: DocumentationTarget, note: str) -> None:
        if target.identifier in self._plan_state:
            self._plan_state[target.identifier].update({"status": "!", "note": note})
            self._write_plan_file()

    def _write_plan_file(self) -> None:
        lines = ["# Knowledge Base Plan", ""]
        if self._scouting_tree:
            report_path = (self.output_root / "scouting_report.md").as_posix()
            lines.extend(
                [
                    "## Scout Snapshot",
                    f"- Source: `{report_path}`",
                    "",
                ]
            )
        for k, v in self._plan_state.items():
            lines.append(f"- [{v['status']}] {v['path']} ({v['note']})")
            focus_listing = self._focus_files_cache.get(k, [])
            for focus_path in focus_listing:
                lines.append(f"    - focus: {focus_path}")
        self.plan_path.write_text("\n".join(lines), "utf-8")

    def _apply_target_cap(
        self, targets: Sequence[DocumentationTarget]
    ) -> List[DocumentationTarget]:
        if self._max_targets is None or len(targets) <= self._max_targets:
            return list(targets)
        logger.info(
            "Limiting knowledge-base targets from %d to %d to control sub-agent work.",
            len(targets),
            self._max_targets,
        )
        return list(targets[: self._max_targets])

    def _sub_agent_min_interval(self) -> float:
        return max(0.0, DEFAULT_SUB_AGENT_MIN_INTERVAL + self._step_delay_seconds)

    @staticmethod
    def _reset_directory(path: Path) -> None:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)

    def _clear_rag_vector_store(self) -> None:
        """Remove any persisted RAG vector store so tutorials rebuild from fresh KB."""
        if not self.tutorial_output_root:
            return

        parent = self.tutorial_output_root.parent
        store_root = (
            parent / "rag_vector_store"
            if parent != self.tutorial_output_root
            else self.tutorial_output_root / "rag_vector_store"
        )

        if store_root.exists():
            logger.info("Clearing stale RAG vector store at {}", store_root)
            shutil.rmtree(store_root, ignore_errors=True)

    @staticmethod
    def _resolve_float_option(
        override: float | None,
        env_var: str,
        *,
        default: float,
        minimum: float = 0.0,
    ) -> float:
        if override is not None:
            return max(minimum, override)
        raw = os.getenv(env_var)
        if raw:
            try:
                return max(minimum, float(raw))
            except ValueError:
                logger.warning(
                    "Invalid %s value '%s'; using default %.2f",
                    env_var,
                    raw,
                    default,
                )
        return max(minimum, default)

    @staticmethod
    def _resolve_optional_int_option(
        override: int | None,
        env_var: str,
        *,
        minimum: int = 1,
        default: int | None = None,
    ) -> int | None:
        if override is not None:
            return max(minimum, override)
        raw = os.getenv(env_var)
        if raw:
            try:
                return max(minimum, int(raw))
            except ValueError:
                logger.warning(
                    "Invalid %s value '%s'; ignoring optional limit",
                    env_var,
                    raw,
                )
                return default

    @staticmethod
    def _has_meaningful_content(content: str) -> bool:
        return len(content.strip()) > 50  # Simple heuristic

    def _build_directory_tree(self, root: Path, max_depth: int = 2) -> str:
        tree_lines = []

        def _add_to_tree(path: Path, current_depth: int, prefix: str = ""):
            if current_depth > max_depth:
                return

            try:
                items = sorted(
                    path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
                )
            except PermissionError:
                return

            items = [
                i
                for i in items
                if not i.name.startswith(".")
                and i.name not in ["__pycache__", "node_modules", "venv", "env"]
            ]

            for index, item in enumerate(items):
                is_last = index == len(items) - 1
                connector = "└── " if is_last else "├── "

                tree_lines.append(
                    f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}"
                )

                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    _add_to_tree(item, current_depth + 1, prefix + extension)

        tree_lines.append(f"{root.name}/")
        _add_to_tree(root, 1)
        return "\n".join(tree_lines)

    def _summarize_top_level_directories(self) -> List[str]:
        try:
            return [
                p.name
                for p in self.codebase_root.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            ]
        except Exception:
            return []

    def _read_file_excerpt(self, path: Path, max_chars: int = 2000) -> str | None:
        if path.exists():
            return path.read_text("utf-8")[:max_chars]
        return None

    def _should_regenerate_target(self, target: DocumentationTarget) -> bool:
        """
        Check if target needs regeneration based on source file modification times.
        Returns True if:
          - Output file doesn't exist
          - Any source file is newer than the output
          - Output file is empty/corrupted
        """
        # Determine output file path
        base_name = target.identifier
        if base_name.endswith(".md"):
            base_name = base_name[:-3]
        output_file = self.output_root / f"{base_name}.md"

        # If output doesn't exist, regenerate
        if not output_file.exists():
            logger.debug(f"  → {target.path}: No existing output")
            return True

        # If output is empty or corrupted, regenerate
        try:
            content = output_file.read_text("utf-8")
            if len(content.strip()) < 50:
                logger.debug(
                    f"  → {target.path}: Output too small ({len(content)} bytes)"
                )
                return True
        except Exception:
            logger.debug(f"  → {target.path}: Cannot read output")
            return True

        # Get output modification time
        try:
            output_mtime = output_file.stat().st_mtime
        except OSError:
            return True

        # Check source files
        source_path = self.codebase_root / target.path

        if not source_path.exists():
            logger.debug(f"  → {target.path}: Source no longer exists")
            return False  # Don't regenerate if source is gone

        # For single files
        if source_path.is_file():
            try:
                source_mtime = source_path.stat().st_mtime
                if source_mtime > output_mtime:
                    logger.debug(f"  → {target.path}: Source file modified")
                    return True
            except OSError:
                return True
            return False

        # For directories, check all Python/config files
        if source_path.is_dir():
            for file in source_path.rglob("*"):
                # Skip non-relevant files
                if file.is_dir():
                    continue
                if file.name.startswith("."):
                    continue
                if any(part in _IGNORED_SCAN_DIRS for part in file.parts):
                    continue

                # Check modification time
                try:
                    if file.stat().st_mtime > output_mtime:
                        logger.debug(f"  → {target.path}: File {file.name} modified")
                        return True
                except OSError:
                    continue

        logger.debug(f"  → {target.path}: Up-to-date")
        return False


__all__ = [
    "KnowledgeBaseBuilder",
    "DEFAULT_TARGET_IDENTIFIERS",
    "TARGET_WHITELIST_ENV",
]
