"""Shared type definitions and data structures for pipelines."""

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, Optional

@dataclass
class DocumentationTarget:
    """Represents a target file or directory for documentation."""
    path: Path
    label: str

    @property
    def identifier(self) -> str:
        # Sanitize path for use as a filename/directory name
        safe = str(self.path).replace("/", "_").replace("\\", "_").strip("_")
        return safe if safe else "root"

@dataclass
class AgentWorkspaceResult:
    """Result of a sub-agent execution."""
    index: int
    target: DocumentationTarget
    workspace: Optional[Path] = None
    error: Optional[str] = None

class TutorialOutlineItem(TypedDict):
    """Initial outline item before processing."""
    filename: str
    title: str
    description: str

class TutorialRunMetrics(TypedDict):
    """Metrics for tutorial generation run."""
    total_tutorials: int
    duration_seconds: float
    model_costs: dict[str, float]
