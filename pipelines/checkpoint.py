"""Checkpoint system for pipeline state persistence and resumption."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class PipelineCheckpoint:
    """Represents the state of a pipeline run for resumption."""
    
    phase: str  # "kb_generation", "tutorial_generation", "completed"
    codebase_name: str
    output_root: str
    
    # Knowledge Base state
    kb_completed_targets: list[str] = field(default_factory=list)
    kb_pending_targets: list[str] = field(default_factory=list)
    kb_output_files: list[str] = field(default_factory=list)
    
    # Tutorial state
    tutorial_completed: list[str] = field(default_factory=list)
    tutorial_pending: list[str] = field(default_factory=list)
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    last_error: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineCheckpoint":
        return cls(**data)


def get_checkpoint_path(output_root: Path) -> Path:
    """Get the checkpoint file path for an output root."""
    return output_root / ".pipeline_checkpoint.json"


def save_checkpoint(checkpoint: PipelineCheckpoint) -> Path:
    """Save checkpoint to disk."""
    path = get_checkpoint_path(Path(checkpoint.output_root))
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint.to_dict(), f, indent=2)
    
    logger.debug(f"Checkpoint saved: phase={checkpoint.phase}, path={path}")
    return path


def load_checkpoint(output_root: Path) -> PipelineCheckpoint | None:
    """Load checkpoint from disk if it exists."""
    path = get_checkpoint_path(output_root)
    
    if not path.exists():
        logger.debug(f"No checkpoint found at {path}")
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        checkpoint = PipelineCheckpoint.from_dict(data)
        logger.info(f"Loaded checkpoint: phase={checkpoint.phase}, timestamp={checkpoint.timestamp}")
        return checkpoint
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.warning(f"Invalid checkpoint file, ignoring: {e}")
        return None


def clear_checkpoint(output_root: Path) -> None:
    """Remove checkpoint file after successful completion."""
    path = get_checkpoint_path(output_root)
    if path.exists():
        path.unlink()
        logger.debug(f"Checkpoint cleared: {path}")


def run_with_rate_limit_retry(
    func,
    *args,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    max_retries: int = 10,
    jitter: float = 0.5,
    **kwargs,
):
    """
    Execute a function with exponential backoff and jitter for rate limit errors.
    
    Following Google's best practices:
    - Exponential backoff: delay doubles each attempt
    - Jitter: random variation to prevent thundering herd
    - Max retries: prevents infinite loops
    - Only retries transient errors (429, 5xx)
    
    Args:
        func: Function to execute
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        max_retries: Maximum number of retry attempts (default: 10)
        jitter: Random jitter factor ±50% (default: 0.5)
    """
    import random
    from smolagents.utils import AgentGenerationError
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except (AgentGenerationError, Exception) as e:
            error_str = str(e)
            is_rate_limit = any(x in error_str for x in ["429", "RateLimitError", "RESOURCE_EXHAUSTED", "Too Many Requests"])
            
            if not is_rate_limit:
                # Not a transient error, don't retry
                raise
            
            if attempt == max_retries - 1:
                # Last attempt failed, give up
                logger.error(f"Rate limit retry exhausted after {max_retries} attempts. Last error: {error_str[:200]}")
                raise
            
            # Calculate exponential backoff with jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            jittered_delay = delay * (1 + jitter * (random.random() * 2 - 1))
            
            logger.warning(
                f"Rate limit hit. Retry {attempt + 1}/{max_retries} in {jittered_delay:.1f}s"
            )
            last_error = error_str
            time.sleep(jittered_delay)


class CheckpointedPipelineRunner:
    """Mixin or helper for running pipeline phases with checkpointing."""
    
    def __init__(self, output_root: Path, codebase_name: str, force_rebuild: bool = False):
        self.output_root = output_root
        self.codebase_name = codebase_name
        self.force_rebuild = force_rebuild
        
        # Load or create checkpoint
        if force_rebuild:
            self.checkpoint = None
            clear_checkpoint(output_root)
        else:
            self.checkpoint = load_checkpoint(output_root)
        
        if self.checkpoint is None:
            self.checkpoint = PipelineCheckpoint(
                phase="init",
                codebase_name=codebase_name,
                output_root=str(output_root),
            )
    
    def should_skip_kb_target(self, target: str) -> bool:
        """Check if a KB target was already completed."""
        return target in self.checkpoint.kb_completed_targets
    
    def mark_kb_target_complete(self, target: str, output_file: str | None = None):
        """Mark a KB target as completed and save checkpoint."""
        if target not in self.checkpoint.kb_completed_targets:
            self.checkpoint.kb_completed_targets.append(target)
        if target in self.checkpoint.kb_pending_targets:
            self.checkpoint.kb_pending_targets.remove(target)
        if output_file and output_file not in self.checkpoint.kb_output_files:
            self.checkpoint.kb_output_files.append(output_file)
        self.checkpoint.timestamp = datetime.now().isoformat()
        save_checkpoint(self.checkpoint)
    
    def should_skip_tutorial(self, filename: str) -> bool:
        """Check if a tutorial was already completed."""
        return filename in self.checkpoint.tutorial_completed
    
    def mark_tutorial_complete(self, filename: str):
        """Mark a tutorial as completed and save checkpoint."""
        if filename not in self.checkpoint.tutorial_completed:
            self.checkpoint.tutorial_completed.append(filename)
        if filename in self.checkpoint.tutorial_pending:
            self.checkpoint.tutorial_pending.remove(filename)
        self.checkpoint.timestamp = datetime.now().isoformat()
        save_checkpoint(self.checkpoint)
    
    def set_phase(self, phase: str):
        """Update the current phase."""
        self.checkpoint.phase = phase
        self.checkpoint.timestamp = datetime.now().isoformat()
        save_checkpoint(self.checkpoint)
    
    def set_pending_targets(self, targets: list[str]):
        """Set the pending KB targets."""
        self.checkpoint.kb_pending_targets = targets
        save_checkpoint(self.checkpoint)
    
    def set_pending_tutorials(self, tutorials: list[str]):
        """Set the pending tutorials."""
        self.checkpoint.tutorial_pending = tutorials
        save_checkpoint(self.checkpoint)
    
    def mark_complete(self):
        """Mark the entire pipeline as complete and clear checkpoint."""
        self.checkpoint.phase = "completed"
        clear_checkpoint(self.output_root)
