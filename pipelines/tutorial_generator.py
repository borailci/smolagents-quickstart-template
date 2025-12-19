"""Generate tutorial markdown files from the knowledge base."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from loguru import logger
from smolagents import LiteLLMModel
from smolagents.agents import ToolCallingAgent

from config import settings
from prompts import prompts
from toolkits.tutorial_toolkit import build_tutorial_supervisor_tools
from toolkits.scoped_filesystem_toolkit import ensure_directory
from utils.llm_factory import create_model

try:
    import tiktoken
except Exception:
    tiktoken = None

__all__ = ["TutorialGenerator", "TutorialOutlineItem", "TutorialRunMetrics"]


@dataclass(frozen=True)
class TutorialOutlineItem:
    filename: str
    title: str
    description: str


@dataclass
class TutorialRunMetrics:
    tool_calls: int = 0
    tool_token_estimate: int = 0
    instructions_token_estimate: int = 0
    tutorial_token_estimate: int = 0
    context_overflow_events: int = 0
    model_errors: list[str] = field(default_factory=list)

    @property
    def total_estimated_tokens(self) -> int:
        return (
            self.tool_token_estimate
            + self.instructions_token_estimate
            + self.tutorial_token_estimate
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_calls": self.tool_calls,
            "tool_token_estimate": self.tool_token_estimate,
            "instructions_token_estimate": self.instructions_token_estimate,
            "tutorial_token_estimate": self.tutorial_token_estimate,
            "total_estimated_tokens": self.total_estimated_tokens,
            "context_overflow_events": self.context_overflow_events,
            "model_errors": list(self.model_errors),
        }


class TutorialGenerator:
    """Generates tutorials from a Knowledge Base using agentic supervisor."""
    
    def __init__(
        self,
        *,
        codebase_root: str | Path | None = None,
        knowledge_base_root: str | Path | None = None,
        output_root: str | Path | None = None,
        sub_agents_root: str | Path | None = None,
        dry_run: bool = False,
        step_delay_seconds: float | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.metrics = TutorialRunMetrics()
        
        # Apply step delay override if provided
        if step_delay_seconds is not None:
            settings.RATE_LIMIT_MIN_INTERVAL = float(step_delay_seconds)
            logger.info(f"Rate limit interval overridden to {step_delay_seconds}s")
        
        # Use config.py for paths
        self.codebase_root = (
            Path(codebase_root) if codebase_root else settings.CODEBASE_ROOT
        ).resolve()
        
        self.knowledge_base_root = (
            Path(knowledge_base_root) if knowledge_base_root else settings.DEEP_AGENT_KB
        ).resolve()
        
        self.output_root = ensure_directory(
            output_root or settings.DEEP_AGENT_TUTORIALS
        )
        
        self.sub_agents_root = ensure_directory(
            sub_agents_root or settings.DEEP_AGENT_SUB_AGENTS
        )
        
        self._token_encoder = self._build_token_encoder(settings.MODEL_ID)
    
    def _build_token_encoder(self, model_id: str) -> Callable[[str], int]:
        if tiktoken is None:
            return lambda text: max(1, len(text) // 4)
        try:
            enc = tiktoken.encoding_for_model(model_id)
            return lambda text: len(enc.encode(text))
        except Exception:
            return lambda text: max(1, len(text) // 4)
    
    def _count_tokens(self, text: str) -> int:
        return self._token_encoder(text)
    
    # =========================================================================
    # Main Entry Points
    # =========================================================================
    
    def generate(self, metrics: Any = None) -> List[Path]:
        """Generate tutorials using supervisor mode (default)."""
        return self.generate_with_supervisor(metrics=metrics)
    
    def generate_with_supervisor(self, metrics: Any = None) -> List[Path]:
        """Generate tutorials using the Tutorial Supervisor Agent."""
        logger.info("Starting supervised tutorial generation...")
        
        if not self.dry_run:
            if self.sub_agents_root.exists():
                shutil.rmtree(self.sub_agents_root)
            self.sub_agents_root.mkdir(parents=True, exist_ok=True)
            
            if self.output_root.exists():
                shutil.rmtree(self.output_root)
            self.output_root.mkdir(parents=True, exist_ok=True)
        
        supervisor = self._create_supervisor_agent(metrics=metrics)
        
        if self.dry_run:
            logger.info("[DRY RUN] Would run Tutorial Supervisor Agent.")
            return []

        from pipelines.checkpoint import run_with_rate_limit_retry
        
        try:
            run_with_rate_limit_retry(
                supervisor.run,
                "Plan and generate the tutorial series following your detailed Execution Workflow in your system prompt.",
                max_steps=50
            )
        except Exception as e:
            logger.error(f"Supervisor failed: {e}")
            if not self.dry_run:
                raise
        
        output_files = list(self.output_root.glob("*.md"))
        logger.info(f"Generated {len(output_files)} tutorials.")
        self._sanitize_tutorial_outputs(output_files)
        return sorted(output_files, key=lambda p: p.name)
    
    def generate_baseline_with_supervisor(self, metrics: Any = None) -> List[Path]:
        """Generate tutorials using the Baseline Supervisor (No KB)."""
        logger.info("Starting BASELINE supervised tutorial generation (No KB)...")
        
        if not self.dry_run:
            if self.sub_agents_root.exists():
                shutil.rmtree(self.sub_agents_root)
            self.sub_agents_root.mkdir(parents=True, exist_ok=True)
            
            if self.output_root.exists():
                shutil.rmtree(self.output_root)
            self.output_root.mkdir(parents=True, exist_ok=True)
        
        supervisor = self._create_baseline_supervisor_agent(metrics=metrics)
        
        from pipelines.checkpoint import run_with_rate_limit_retry
        
        try:
            run_with_rate_limit_retry(
                supervisor.run,
                "Plan and generate the tutorial series by exploring the codebase.",
                max_steps=50
            )
        except Exception as e:
            logger.error(f"Baseline Supervisor failed: {e}")
            if not self.dry_run:
                raise
        
        output_files = list(self.output_root.glob("*.md"))
        logger.info(f"Generated {len(output_files)} baseline tutorials.")
        self._sanitize_tutorial_outputs(output_files)
        return sorted(output_files, key=lambda p: p.name)
    
    # =========================================================================
    # Supervisor Agent Creation
    # =========================================================================
    
    def _create_supervisor_agent(self, metrics: Any = None) -> ToolCallingAgent:
        """Create the Tutorial Supervisor Agent."""
        tools = build_tutorial_supervisor_tools(
            codebase_root=self.codebase_root,
            sub_agents_root=self.sub_agents_root,
            output_root=self.output_root,
            knowledge_base_root=self.knowledge_base_root,
            metrics=metrics
        )
        model = create_model(role="supervisor", metrics=metrics)
        
        return ToolCallingAgent(
            name="tutorial_supervisor",
            tools=tools,
            model=model,
            instructions=prompts.TUTORIAL_SUPERVISOR_PROMPT,
        )
    
    def _create_baseline_supervisor_agent(self, metrics: Any = None) -> ToolCallingAgent:
        """Create the Baseline Tutorial Supervisor Agent."""
        tools = build_tutorial_supervisor_tools(
            codebase_root=self.codebase_root,
            sub_agents_root=self.sub_agents_root,
            output_root=self.output_root,
            knowledge_base_root=None,
            baseline_mode=True,
            metrics=metrics
        )
        model = create_model(role="supervisor", metrics=metrics)
        
        return ToolCallingAgent(
            name="baseline_tutorial_supervisor",
            tools=tools,
            model=model,
            instructions=prompts.BASELINE_TUTORIAL_SUPERVISOR_PROMPT,
        )
    
    # =========================================================================
    # Output Sanitization
    # =========================================================================
    
    def _sanitize_tutorial_outputs(self, paths: List[Path]) -> None:
        """Remove LLM artifacts from tutorial outputs."""
        for path in paths:
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            original = content
            
            # Remove triple-quote wrappers
            if content.startswith("'''") and content.endswith("'''"):
                content = content[3:-3].strip()
            elif content.startswith('"""') and content.endswith('"""'):
                content = content[3:-3].strip()
            
            if content != original:
                path.write_text(content, encoding="utf-8")
                logger.debug(f"Sanitized {path.name}")
    
