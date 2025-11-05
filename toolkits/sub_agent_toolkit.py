"""Tools that orchestrate sub-agent execution for the knowledge-base pipeline."""

from __future__ import annotations

import os
import shutil
import time
from collections import deque
from pathlib import Path
from typing import Deque, List, Optional

from dotenv import load_dotenv
from loguru import logger
from smolagents import LiteLLMModel, Tool, tool
from smolagents.agents import ToolCallingAgent

from prompts import prompts
from toolkits.scoped_filesystem_toolkit import build_scoped_tools
from utils.path_utils import ensure_directory

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
SUB_AGENTS_ROOT_PATH = os.getenv("SUB_AGENTS_ROOT_PATH")


def _formatted_prompt(task_description: str) -> str:
    return f"{prompts.SUB_AGENT_KB_PROMPT.strip()}\n\nTask details:\n{task_description.strip()}"


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
    if not LITELLM_MODEL_ID or not LITELLM_API_KEY:
        raise RuntimeError("LITELLM_MODEL_ID and LITELLM_API_KEY must be configured.")
    return LiteLLMModel(model_id=LITELLM_MODEL_ID, api_key=LITELLM_API_KEY)


def run_sub_agent_tasks(
    task_descriptions: List[str],
    *,
    codebase_root: Optional[str | Path] = None,
    sub_agents_root: Optional[str | Path] = None,
    max_retries: int = 1,
    window_seconds: float = 90.0,
    max_requests_per_window: int = 5,
) -> List[Path]:
    """Execute sub-agents sequentially and return their workspace paths."""

    if not isinstance(task_descriptions, list) or not task_descriptions:
        return []

    codebase_path, sub_agents_path = _resolve_paths(codebase_root, sub_agents_root)
    model = _build_model()

    workspaces: List[Path] = []

    request_timestamps: Deque[float] = deque()

    for index, description in enumerate(task_descriptions):
        workspace_dir = sub_agents_path / f"sub_agent_{index}"
        workspace_exists = workspace_dir.exists()
        workspace = ensure_directory(workspace_dir)

        existing_summary = workspace / "summary.md"
        if workspace_exists and existing_summary.exists():
            logger.info(
                "Skipping sub-agent %s; existing output detected at %s.",
                index,
                existing_summary,
            )
            workspaces.append(workspace)
            continue

        if workspace_exists:
            shutil.rmtree(workspace_dir)
            workspace = ensure_directory(workspace_dir)

        logger.info("Launching sub-agent %s in %s", index, workspace)

        scoped_tools = build_scoped_tools(
            codebase_root=str(codebase_path),
            workspace_root=str(workspace),
        )

        agent = ToolCallingAgent(
            name=f"sub_agent_{index}",
            description=f"Knowledge-base analyzer for task {index}",
            tools=scoped_tools,
            model=model,
            instructions=_formatted_prompt(description),
        )

        attempt = 0
        while True:
            attempt += 1
            now = time.monotonic()
            while request_timestamps and now - request_timestamps[0] >= window_seconds:
                request_timestamps.popleft()

            if len(request_timestamps) >= max_requests_per_window:
                wait_time = window_seconds - (now - request_timestamps[0])
                logger.debug(
                    "Rate limiting active. Sleeping %.2fs before next request.",
                    wait_time,
                )
                time.sleep(max(wait_time, 0.1))
                continue

            try:
                agent.run(description)
                request_timestamps.append(time.monotonic())
                workspaces.append(workspace)
                break
            except Exception as exc:
                is_rate_limit = (
                    getattr(exc, "__class__", type(exc))
                    .__name__.lower()
                    .startswith("ratelimit")
                    or "quota" in str(exc).lower()
                )
                if is_rate_limit:
                    logger.error(
                        "Sub-agent %s hit provider quota: %s. Aborting further retries.",
                        index,
                        exc,
                    )
                    raise

                if attempt >= max_retries:
                    raise
                logger.warning(
                    "Sub-agent %s failed on attempt %s/%s: %s. Retrying...",
                    index,
                    attempt,
                    max_retries,
                    exc,
                )
                time.sleep(2.0)

    return workspaces


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
