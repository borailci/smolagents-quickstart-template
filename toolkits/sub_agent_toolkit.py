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
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

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

# Import config for settings
from config import settings

# API key still from env (security)
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")

DEFAULT_SUB_AGENT_MAX_RETRIES = settings.SUB_AGENT_MAX_RETRIES





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
    codebase_value = codebase_root or settings.CODEBASE_ROOT
    sub_agents_value = sub_agents_root or settings.SUB_AGENTS_ROOT

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
    metrics: Any = None,
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
    logger.info(f"Sub-agent model type: {type(model).__name__}")
    
    # Pre-calculate prompts
    prompt_map = dict(DEFAULT_ROLE_PROMPTS)


    workspaces: List[Path] = []
    request_timestamps: Deque[float] = deque()

    def _prune_timestamps(now: float) -> None:
        while request_timestamps and now - request_timestamps[0] >= window_seconds:
            request_timestamps.popleft()

    # _enforce_min_step_duration definition removed

    for index, spec in enumerate(task_specs, start=1):
        description = spec.description
        role_prompt = spec.instructions or prompt_map.get(spec.role, prompts.SUB_AGENT_KB_PROMPT)

        # Use sub_agents_path directly - caller controls naming
        # Only create subdirs if multiple tasks in same batch
        if len(task_specs) > 1:
            workspace_dir = sub_agents_path / f"sub_agent_{index}"
        else:
            workspace_dir = sub_agents_path
            
        workspace = ensure_directory(workspace_dir)

        logger.info("Launching sub-agent {} in {}", index, workspace)

        base_instructions = _formatted_prompt(description, role_prompt)
        if STRICT_JSON_REMINDER not in base_instructions:
            base_instructions += STRICT_JSON_REMINDER
        
        # Build agent
        # When minimal_tools=True, disable exploration to save tokens
        usage_cb = None
        if metrics:
            def _cb(tool_name: str):
                metrics.record_tool_call(tool_name)
            usage_cb = _cb

        scoped_tools = build_scoped_tools(
            codebase_root=str(codebase_path),
            workspace_root=str(workspace),
            usage_callback=usage_cb,
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
                    
                    # Helpful error message
                    available_files = [f.name for f in kb_path_obj.glob("*.md")][:10]
                    return f"File '{filename}' not found in Knowledge Base. This tool is ONLY for KB summary files. Available KB files: {available_files}. For codebase files like README.md or .py files, use `read_codebase_file` instead."

            scoped_tools.append(ReadKBTool())

        agent = ToolCallingAgent(
            name=f"sub_agent_{index}",
            description=f"Knowledge-base agent for task {index}",
            tools=scoped_tools,
            model=model,
            instructions=base_instructions,
            # No step_callbacks needed for rate limiting anymore
        )

        # Execute with simple retry for non-rate-limit errors (e.g. context length or parsing)
        # Rate limits are now handled internally by llm_factory
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                agent.run(description)
                workspaces.append(workspace)
                break
            except Exception as exc:
                logger.warning(f"Sub-agent {index} failed on attempt {attempt}/{max_attempts}: {exc}. Retrying...")
                # SAFETY NET: Force sleep to prevent rapid-fire retries if LLM layer rate limiting failed
                time.sleep(15.0)
            
            if attempt >= max_attempts:
                logger.error(f"Sub-agent {index} failed permanently.")
                     # We don't raise here to allow other agents to continue, 
                     # but the supervisor will notice the missing output.
                     
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
    metrics: Any = None,
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
        metrics=metrics,
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