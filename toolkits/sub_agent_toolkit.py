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

from config import settings
from prompts import prompts
from toolkits.scoped_filesystem_toolkit import build_scoped_tools, ensure_directory
from utils.llm_factory import create_model

__all__ = [
    "SubAgentRole",
    "SubAgentTaskSpec",
    "SubAgentOutputError",
    "run_typed_sub_agent_tasks",
    "ToolBudgetExceededError",
    "validate_markdown_output",
]


class SubAgentOutputError(Exception):
    """Error raised when sub-agent output validation fails."""
    pass

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
SUB_AGENTS_ROOT_PATH = os.getenv("SUB_AGENTS_ROOT_PATH")

DEFAULT_SUB_AGENT_MAX_RETRIES = 10

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


def validate_markdown_output(
    content: str,
    expected_title: str | None = None,
    min_length: int = 200,
) -> tuple[bool, list[str]]:
    """
    Validate sub-agent markdown output structural integrity.
    
    Returns (is_valid, list_of_errors).
    This catches broken outputs from truncated generation, bad concatenation, etc.
    
    Note: Uses core validation from utils/validation.py.
    """
    """
    Validate sub-agent markdown output structural integrity.
    
    Returns (is_valid, list_of_errors).
    Simplified check since validation.py was removed.
    """
    issues = []
    if not content:
        issues.append("Content is empty")
        return False, issues
        
    if len(content) < min_length:
        issues.append(f"Content length {len(content)} < {min_length}")
        return False, issues
        
    return True, []


# ToolUsageBudget removed - no budget enforcement


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


def _build_model() -> LiteLLMModel:
    # Sub-agents use Flash model for high volume (hybrid strategy)
    return create_model(role="sub_agent")



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
    window_seconds: float = None,  # Uses settings.RATE_LIMIT_WINDOW_SECONDS
    max_requests_per_window: int = None,  # Uses settings.RATE_LIMIT_MAX_REQUESTS
    min_interval_seconds: float = None,  # Uses settings.RATE_LIMIT_MIN_INTERVAL
    max_tool_calls: int | None = None,
    max_directory_calls: int | None = None,
    knowledge_base_root: Optional[str | Path] = None,
    minimal_tools: bool = True,  # Disable exploration by default
) -> List[Path]:
    # Apply config defaults if not specified
    if window_seconds is None:
        window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS
    if max_requests_per_window is None:
        max_requests_per_window = settings.RATE_LIMIT_MAX_REQUESTS
    if min_interval_seconds is None:
        min_interval_seconds = settings.RATE_LIMIT_MIN_INTERVAL
    
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

        # Use sub_agents_path directly - caller controls naming
        # Only create subdirs if multiple tasks in same batch
        if len(task_specs) > 1:
            workspace_dir = sub_agents_path / f"sub_agent_{index}"
        else:
            workspace_dir = sub_agents_path
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

        # Budget enforcement removed

        base_instructions = _formatted_prompt(description, role_prompt)
        if STRICT_JSON_REMINDER not in base_instructions:
            base_instructions += STRICT_JSON_REMINDER
        current_instructions = base_instructions

        def _build_agent(instructions: str) -> ToolCallingAgent:
            # When minimal_tools=True, disable exploration to save tokens
            scoped_tools = build_scoped_tools(
                codebase_root=str(codebase_path),
                workspace_root=str(workspace),
                usage_callback=None,  # budget system removed
                allow_directory_listing=not minimal_tools,
                allow_tree=not minimal_tools,
                allow_mermaid=False,
                allow_writes=True,
            )

            # ADD KB TOOL FOR SUB-AGENTS
            if knowledge_base_root and Path(knowledge_base_root).exists():
                kb_path_obj = Path(knowledge_base_root)
                
                class ReadKBTool(Tool):
                    name = "read_knowledge_base_file"
                    description = "Read a knowledge base file (markdown summary)."
                    inputs = {
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to read (e.g., executive_summary.md). Do NOT provide full path.",
                        }
                    }
                    output_type = "string"
                    
                    def forward(self, filename: str) -> str:
                        # Handle both simple filenames and full paths if agent hallucinates
                        target = None
                        if "/" in filename:
                             # Try to treat as relative or check if it matches kb_path
                             maybe_path = Path(filename)
                             if str(kb_path_obj) in str(maybe_path.resolve()):
                                 target = maybe_path
                             else:
                                 # Try stripping path
                                 target = kb_path_obj / maybe_path.name
                        else:
                            target = kb_path_obj / filename
                            
                        if target and target.exists() and str(kb_path_obj) in str(target.resolve()):
                             return target.read_text(encoding="utf-8")
                        return f"File '{filename}' not found in Knowledge Base."

                scoped_tools.append(ReadKBTool())

            return ToolCallingAgent(
                name=f"sub_agent_{index}",
                description=f"Knowledge-base agent for task {index}",
                tools=scoped_tools,
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
                    or "429" in str(exc)
                )
                parse_error = (
                    "Expecting property name enclosed in double quotes" in str(exc)
                )
                empty_response = (
                    "Message contains no content" in str(exc)
                    or "no tool calls" in str(exc).lower()
                )

                # Handle empty LLM responses - wait and retry
                if empty_response:
                    wait_seconds = 5.0  # Wait before retry
                    logger.warning(
                        "Sub-agent {} received empty response. Retry {}/{} in {:.1f}s.",
                        index,
                        attempt,
                        max_retries,
                        wait_seconds,
                    )
                    if attempt >= max_retries:
                        raise
                    time.sleep(wait_seconds)
                    _enforce_min_step_duration(elapsed)
                    continue

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
                    if attempt >= max_retries:
                        logger.error(
                            "Sub-agent {} exhausted retries after quota errors: {}.",
                            index,
                            last_exc,
                        )
                        raise

                    wait_seconds = _extract_retry_after_seconds(exc, default=5.0)
                    rate_limit_consecutive += 1

                    logger.warning(
                        "Sub-agent {} hit provider quota. Retry {}/{} in {:.1f}s.",
                        index,
                        attempt,
                        max_retries,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue
                else:
                    rate_limit_consecutive = 0

                if attempt >= max_retries:
                    raise

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
    knowledge_base_root: Optional[str | Path] = None,
    minimal_tools: bool = True,  # Disable exploration by default
) -> List[Path]:
    """
    Execute analyzer-style sub-agents and return their workspace paths.
    
    .. deprecated::
        Use `run_typed_sub_agent_tasks` instead for explicit role-based execution.
    """

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
        minimal_tools=minimal_tools,
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
    minimal_tools: bool = True,  # Disable exploration by default
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
        minimal_tools=minimal_tools,
    )


def get_sub_agent_tools() -> List[Tool]:
    """
    Return tools for managing sub-agent execution.
    
    .. deprecated::
        This function is not actively used. Use direct calls to
        `run_typed_sub_agent_tasks` instead for production code.
    """

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
        return "\\n".join(summary_lines)

    # spawn_sub_agents.run_sub_agent_tasks = run_sub_agent_tasks  # type: ignore[attr-defined] # Not needed with new structure

    return [spawn_sub_agents]