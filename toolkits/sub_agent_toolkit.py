"""Tools that orchestrate sub-agent execution for the knowledge-base pipeline."""

from __future__ import annotations

import os
import re
import shutil
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Deque, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv
from loguru import logger
from smolagents import LiteLLMModel, Tool, tool
from smolagents.agents import ToolCallingAgent

from prompts import prompts
from toolkits.scoped_filesystem_toolkit import build_scoped_tools
from utils.path_utils import ensure_directory

__all__ = [
    "SubAgentRole",
    "SubAgentTaskSpec",
    "run_typed_sub_agent_tasks",
    "ToolBudgetExceededError",
    "SubAgentOutputError",
]

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
SUB_AGENTS_ROOT_PATH = os.getenv("SUB_AGENTS_ROOT_PATH")
SUB_AGENT_RPM_ENV = "SUB_AGENT_REQUESTS_PER_MINUTE"
DEFAULT_SUB_AGENT_RPM = 4.0
DEFAULT_SUB_AGENT_MAX_RETRIES = 10
DEFAULT_SUB_AGENT_TOOL_CALL_BUDGET = 6
DEFAULT_SUB_AGENT_DIRECTORY_CALL_BUDGET = 0


_RETRY_IN_PATTERN = re.compile(
    r"retry\s+(?:in|after)\s+([0-9]+(?:\.[0-9]+)?)\s*s", re.IGNORECASE
)
_RETRY_DELAY_PATTERN = re.compile(
    r"\"retryDelay\"\s*:\s*\"([0-9]+(?:\.[0-9]+)?)s\"", re.IGNORECASE
)
_QUOTA_RESET_PATTERN = re.compile(
    r"Please retry in ([0-9]+(?:\.[0-9]+)?)s", re.IGNORECASE
)


class ToolBudgetExceededError(RuntimeError):
    """Raised when an agent exceeds its configured tool usage budget."""


class SubAgentOutputError(RuntimeError):
    """Raised when a sub-agent produces invalid or empty output."""


@dataclass
class ToolUsageBudget:
    agent_index: int
    max_total_calls: int | None = None
    max_directory_calls: int | None = None
    total_calls: int = 0
    directory_calls: int = 0

    def record(self, tool_name: str) -> None:
        if tool_name == "write_workspace_file":
            return
        self.total_calls += 1
        if tool_name == "list_codebase_directory":
            self.directory_calls += 1
            if (
                self.max_directory_calls is not None
                and self.directory_calls > self.max_directory_calls
            ):
                logger.error(
                    "Sub-agent %d exceeded directory listing budget (%d).",
                    self.agent_index,
                    self.max_directory_calls,
                )
                raise ToolBudgetExceededError(
                    "Directory listing limit exceeded; rely on provided structure."
                )

        if self.max_total_calls is not None and self.total_calls > self.max_total_calls:
            logger.error(
                "Sub-agent %d exceeded total tool call budget (%d).",
                self.agent_index,
                self.max_total_calls,
            )
            raise ToolBudgetExceededError(
                "Tool call budget exceeded; consolidate your findings and stop."
            )


class SubAgentRole(str, Enum):
    ANALYZER = "analyzer"
    SUMMARIZER = "summarizer"
    TUTORIAL_WRITER = "tutorial_writer"


@dataclass(frozen=True)
class SubAgentTaskSpec:
    description: str
    role: SubAgentRole = SubAgentRole.ANALYZER
    instructions: Optional[str] = None
    tools: Optional[Sequence[Tool]] = None
    output_format: Optional[str] = None


DEFAULT_ROLE_PROMPTS: Dict[SubAgentRole, str] = {
    SubAgentRole.ANALYZER: prompts.SUB_AGENT_KB_PROMPT,
    SubAgentRole.SUMMARIZER: prompts.SUMMARIZER_KB_PROMPT,
    SubAgentRole.TUTORIAL_WRITER: prompts.TUTORIAL_AGENT_PROMPT,
}


def _formatted_prompt(task_description: str, agent_prompt: str) -> str:
    return f"{agent_prompt.strip()}\n\nTask details:\n{task_description.strip()}"


def _resolve_paths(
    codebase_root: Optional[str | Path],
    sub_agents_root: Optional[str | Path],
) -> tuple[Path, Path]:
    codebase_value = codebase_root or CODEBASE_ROOT_PATH
    sub_agents_value = sub_agents_root or SUB_AGENTS_ROOT_PATH

    if not codebase_value:
        raise RuntimeError("CODEBASE_ROOT_PATH must be configured or provided.")
    if not sub_agents_value:
        raise RuntimeError("SUB_AGENTS_ROOT_PATH must be configured or provided.")

    codebase_path = Path(codebase_value).expanduser().resolve()
    sub_agents_path = ensure_directory(sub_agents_value)
    return codebase_path, sub_agents_path


def _resolve_sub_agent_rpm() -> float:
    raw_value = os.getenv(SUB_AGENT_RPM_ENV)
    if raw_value is None:
        return DEFAULT_SUB_AGENT_RPM
    try:
        parsed = float(raw_value)
    except ValueError:
        logger.warning(
            "Invalid {} value '{}'; using default {:.1f}",
            SUB_AGENT_RPM_ENV,
            raw_value,
            DEFAULT_SUB_AGENT_RPM,
        )
        return DEFAULT_SUB_AGENT_RPM
    if parsed <= 0:
        logger.warning(
            "Non-positive {} value '{}'; using default {:.1f}",
            SUB_AGENT_RPM_ENV,
            raw_value,
            DEFAULT_SUB_AGENT_RPM,
        )
        return DEFAULT_SUB_AGENT_RPM
    return parsed


from utils.llm_factory import create_model

def _build_model() -> LiteLLMModel:
    return create_model(model_id=LITELLM_MODEL_ID, api_key=LITELLM_API_KEY)


def _extract_retry_after_seconds(exc: Exception, default: float = 25.0) -> float:
    message = str(exc)
    for pattern in (_RETRY_DELAY_PATTERN, _RETRY_IN_PATTERN, _QUOTA_RESET_PATTERN):
        match = pattern.search(message)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return default


STRICT_JSON_REMINDER = (
    "\n\nSTRICT TOOL-CALL FORMAT REMINDER:\n"
    '- Every tool call response must be ONLY the JSON arguments (e.g., {"file_path": "src/api/routes.py"}).\n'
    "- Do not wrap JSON in backticks or add prose before or after.\n"
    "- If you need to provide narration, wait until after the tool has returned.\n"
)


def _execute_sub_agent_runs(
    task_specs: Sequence[SubAgentTaskSpec],
    *,
    codebase_root: Optional[str | Path] = None,
    sub_agents_root: Optional[str | Path] = None,
    max_retries: int = DEFAULT_SUB_AGENT_MAX_RETRIES,
    window_seconds: float = 90.0,
    max_requests_per_window: int = 4,
    min_interval_seconds: float = 5.0,
    max_tool_calls: int | None = None,
    max_directory_calls: int | None = None,
    knowledge_base_root: Optional[str | Path] = None,
) -> List[Path]:
    if not task_specs:
        return []

    codebase_path, sub_agents_path = _resolve_paths(codebase_root, sub_agents_root)
    model = _build_model()
    
    # Pre-calculate prompts
    prompt_map = dict(DEFAULT_ROLE_PROMPTS)


    workspaces: List[Path] = []
    request_timestamps: Deque[float] = deque()

    def _prune_timestamps(now: float) -> None:
        while request_timestamps and now - request_timestamps[0] >= window_seconds:
            request_timestamps.popleft()

    def _enforce_min_step_duration(elapsed: float) -> None:
        if elapsed >= min_interval_seconds:
            return
        remaining = min_interval_seconds - elapsed
        logger.info(
            "Step completed in {:.2f}s; sleeping {:.2f}s to satisfy cooldown.",
            elapsed,
            remaining,
        )
        time.sleep(remaining)

    for index, spec in enumerate(task_specs, start=1):
        description = spec.description
        role_prompt = spec.instructions or prompt_map.get(spec.role, prompts.SUB_AGENT_KB_PROMPT)

        workspace_dir = sub_agents_path / f"sub_agent_{index}"
        workspace_exists = workspace_dir.exists()
        workspace = ensure_directory(workspace_dir)

        existing_summary = workspace / "summary.md"
        if workspace_exists and existing_summary.exists():
            logger.info(
                "Skipping sub-agent {}; existing output detected at {}.",
                index,
                existing_summary,
            )
            workspaces.append(workspace)
            continue

        if workspace_exists:
            try:
                shutil.rmtree(workspace_dir)
            except (PermissionError, OSError) as exc:
                logger.warning(
                    "Failed to remove existing workspace {}: {}. Proceeding anyway.",
                    workspace_dir,
                    exc,
                )
            workspace = ensure_directory(workspace_dir)

        logger.info("Launching sub-agent {} in {}", index, workspace)

        budget = (
            ToolUsageBudget(
                agent_index=index,
                max_total_calls=max_tool_calls,
                max_directory_calls=max_directory_calls,
            )
            if max_tool_calls is not None or max_directory_calls is not None
            else None
        )

        base_instructions = _formatted_prompt(description, role_prompt)
        if STRICT_JSON_REMINDER not in base_instructions:
            base_instructions += STRICT_JSON_REMINDER
        current_instructions = base_instructions

        def _build_agent(instructions: str) -> ToolCallingAgent:
            if spec.tools:
                run_tools = spec.tools
            else:
                run_tools = build_scoped_tools(
                    codebase_root=str(codebase_path),
                    workspace_root=str(workspace),
                    usage_callback=budget.record if budget else None,
                    allow_directory_listing=False,
                    allow_tree=False,
                    allow_mermaid=False,
                    allow_writes=True,
                    allow_kb_read=True if knowledge_base_root else False,
                    knowledge_base_root=str(knowledge_base_root) if knowledge_base_root else None,
                )

            return ToolCallingAgent(
                name=f"sub_agent_{index}",
                description=f"Knowledge-base agent for task {index}",
                tools=run_tools,
                model=model,
                instructions=instructions,
            )

        agent = _build_agent(current_instructions)

        attempt = 0
        rate_limit_consecutive = 0
        while True:
            attempt += 1
            now = time.monotonic()
            _prune_timestamps(now)

            if request_timestamps:
                time_since_last = now - request_timestamps[-1]
                if time_since_last < min_interval_seconds:
                    wait_gap = min_interval_seconds - time_since_last
                    logger.info(
                        "Previous step finished {:.2f}s ago; sleeping {:.2f}s to maintain cooldown.",
                        time_since_last,
                        wait_gap,
                    )
                    time.sleep(wait_gap)
                    now = time.monotonic()
                    _prune_timestamps(now)

            if len(request_timestamps) >= max_requests_per_window:
                wait_time = window_seconds - (now - request_timestamps[0])
                logger.debug(
                    "Rate limiting active. Sleeping {:.2f}s before next request.",
                    wait_time,
                )
                time.sleep(max(wait_time, 0.1))
                continue

            # Initialize to avoid UnboundLocalError
            is_rate_limit = False
            parse_error = False
            last_exc = None

            step_start = time.monotonic()
            try:
                agent.run(description)
                step_end = time.monotonic()
                request_timestamps.append(step_end)
                elapsed = step_end - step_start
                _enforce_min_step_duration(elapsed)
                workspaces.append(workspace)
                break
            except Exception as exc:
                last_exc = exc
                if isinstance(exc, ToolBudgetExceededError):
                    raise

                step_end = time.monotonic()
                request_timestamps.append(step_end)
                elapsed = step_end - step_start
                is_rate_limit = (
                    getattr(exc, "__class__", type(exc))
                    .__name__.lower()
                    .startswith("ratelimit")
                    or "quota" in str(exc).lower()
                )
                parse_error = (
                    "Expecting property name enclosed in double quotes" in str(exc)
                    or "Message contains no content" in str(exc)
                )

                if parse_error:
                    if STRICT_JSON_REMINDER not in current_instructions:
                        logger.warning(
                            "Sub-agent {} produced invalid JSON tool call. Reinforcing instructions and retrying.",
                            index,
                        )
                        current_instructions = base_instructions + STRICT_JSON_REMINDER
                        agent = _build_agent(current_instructions)
                    else:
                        logger.warning(
                            "Sub-agent {} still failing JSON format after reinforcement: {}",
                            index,
                            exc,
                        )
                    if attempt >= max_retries:
                        raise
                    _enforce_min_step_duration(elapsed)
                    continue

                if is_rate_limit:
                    rate_limit_consecutive += 1
                    # Infinite retry for rate limits as requested, but with backoff
                    base_wait = _extract_retry_after_seconds(exc, default=5.0)
                    
                    # Exponential backoff: 5, 10, 20, 40, 60...
                    # (2^(count-1)) * base
                    multiplier = 2 ** (rate_limit_consecutive - 1)
                    wait_seconds = min(base_wait * multiplier, 60.0)

                    logger.warning(
                        "Sub-agent {} hit provider quota. Waiting {:.2f}s before retry (attempt {}/inf).",
                        index,
                        wait_seconds,
                        attempt
                    )
                    time.sleep(wait_seconds)
                     # Decrement attempt counter to effectively retry forever on quota
                    attempt -= 1 
                    continue
                else:
                    rate_limit_consecutive = 0

                if attempt >= max_retries:
                    raise

                # Generic error backoff now fixed at 5 seconds per request to avoid exponential waits
                wait_seconds = 5.0
                logger.warning(
                    "Sub-agent {} failed on attempt {}/{}: {}. Retrying in {:.1f}s...",
                    index,
                    attempt,
                    max_retries,
                    last_exc,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                _enforce_min_step_duration(elapsed)

    return workspaces


def run_sub_agent_tasks(
    task_descriptions: List[str],
    *,
    codebase_root: Optional[str | Path] = None,
    sub_agents_root: Optional[str | Path] = None,
    max_retries: int = DEFAULT_SUB_AGENT_MAX_RETRIES,
    window_seconds: float = 90.0,
    max_requests_per_window: int = 5,
    min_interval_seconds: float = 5.0,
    instruction_prompt: str = prompts.SUB_AGENT_KB_PROMPT,
    max_tool_calls: int | None = None,
    max_directory_calls: int | None = None,
) -> List[Path]:
    """Execute analyzer-style sub-agents and return their workspace paths."""

    if not isinstance(task_descriptions, list) or not task_descriptions:
        return []

    specs = [
        SubAgentTaskSpec(
            description=desc,
            role=SubAgentRole.ANALYZER,
            instructions=instruction_prompt
        ) for desc in task_descriptions
    ]

    return _execute_sub_agent_runs(
        specs,
        codebase_root=codebase_root,
        sub_agents_root=sub_agents_root,
        max_retries=max_retries,
        window_seconds=window_seconds,
        max_requests_per_window=max_requests_per_window,
        min_interval_seconds=min_interval_seconds,
        max_tool_calls=max_tool_calls,
        max_directory_calls=max_directory_calls,
        knowledge_base_root=knowledge_base_root,
    )


def run_typed_sub_agent_tasks(
    task_specs: Sequence[SubAgentTaskSpec],
    *,
    codebase_root: Optional[str | Path] = None,
    sub_agents_root: Optional[str | Path] = None,
    max_retries: int = DEFAULT_SUB_AGENT_MAX_RETRIES,
    window_seconds: float = 90.0,
    max_requests_per_window: int = 5,
    min_interval_seconds: float = 5.0,
    role_prompts: Optional[Dict[SubAgentRole, str]] = None,
    max_tool_calls: int | None = None,
    max_directory_calls: int | None = None,
    knowledge_base_root: Optional[str | Path] = None,
) -> List[Path]:
    """Execute sub-agents with explicit roles and return their workspace paths."""

    if not task_specs:
        return []

    # Pass specs directly
    return _execute_sub_agent_runs(
        task_specs,
        codebase_root=codebase_root,
        sub_agents_root=sub_agents_root,
        max_retries=max_retries,
        window_seconds=window_seconds,
        max_requests_per_window=max_requests_per_window,
        min_interval_seconds=min_interval_seconds,
        max_tool_calls=max_tool_calls,
        max_directory_calls=max_directory_calls,
        knowledge_base_root=knowledge_base_root,
    )


def get_sub_agent_tools() -> List[Tool]:
    """Return tools for managing sub-agent execution."""

    @tool
    def spawn_sub_agents(task_descriptions: List[str]) -> str:
        """Run a sequence of sub-agents using scoped file access."""

        workspaces = run_sub_agent_tasks(task_descriptions)

        if not workspaces:
            return "No sub-agent tasks provided."

        summary_lines = [
            f"All {len(workspaces)} sub-agents finished.",
            "Results saved in:",
        ]
        summary_lines.extend(f"- {path}" for path in workspaces)
        return "\n".join(summary_lines)

    spawn_sub_agents.run_sub_agent_tasks = run_sub_agent_tasks  # type: ignore[attr-defined]

    return [spawn_sub_agents]
