"""Unified metrics tracking for Deep Agent pipeline.

Tracks metrics required for experiments.md Experiment 4:
- Overall Token Cost
- Tool Calls
- Context Overflow Events
- Duration
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = ["RunMetrics", "PhaseMetrics"]


@dataclass
class PhaseMetrics:
    """Metrics for a single phase (KB or Tutorial generation)."""
    
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Token tracking
    input_tokens: int = 0
    output_tokens: int = 0
    
    # Tool tracking
    tool_calls: int = 0
    tool_calls_by_name: Dict[str, int] = field(default_factory=dict)
    
    # Error tracking
    context_overflow_events: int = 0
    model_errors: List[str] = field(default_factory=list)
    
    # Agent tracking
    sub_agents_spawned: int = 0
    
    def record_tool_call(self, tool_name: str) -> None:
        """Record a tool call."""
        self.tool_calls += 1
        self.tool_calls_by_name[tool_name] = self.tool_calls_by_name.get(tool_name, 0) + 1
    
    def record_tokens(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Record token usage."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
    
    def record_error(self, error: str, is_overflow: bool = False) -> None:
        """Record an error."""
        self.model_errors.append(error)
        if is_overflow:
            self.context_overflow_events += 1
    
    def finish(self) -> None:
        """Mark phase as finished."""
        self.end_time = time.time()
    
    @property
    def duration_seconds(self) -> float:
        """Duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.input_tokens + self.output_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "duration_seconds": round(self.duration_seconds, 2),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
            "tool_calls_by_name": dict(self.tool_calls_by_name),
            "context_overflow_events": self.context_overflow_events,
            "model_errors": list(self.model_errors),
            "sub_agents_spawned": self.sub_agents_spawned,
        }


@dataclass
class RunMetrics:
    """Unified metrics for a complete Deep Agent run."""
    
    codebase_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Phase metrics
    kb_phase: Optional[PhaseMetrics] = None
    tutorial_phase: Optional[PhaseMetrics] = None
    
    # Model info
    model_id: str = ""
    
    def start_kb_phase(self) -> PhaseMetrics:
        """Start knowledge base generation phase."""
        self.kb_phase = PhaseMetrics(name="knowledge_base")
        return self.kb_phase
    
    def start_tutorial_phase(self) -> PhaseMetrics:
        """Start tutorial generation phase."""
        self.tutorial_phase = PhaseMetrics(name="tutorial")
        return self.tutorial_phase
    
    def finish(self) -> None:
        """Mark run as finished."""
        self.end_time = time.time()
        if self.kb_phase and not self.kb_phase.end_time:
            self.kb_phase.finish()
        if self.tutorial_phase and not self.tutorial_phase.end_time:
            self.tutorial_phase.finish()
    
    @property
    def duration_seconds(self) -> float:
        """Total duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def total_tokens(self) -> int:
        """Total tokens across all phases."""
        total = 0
        if self.kb_phase:
            total += self.kb_phase.total_tokens
        if self.tutorial_phase:
            total += self.tutorial_phase.total_tokens
        return total
    
    @property
    def total_tool_calls(self) -> int:
        """Total tool calls across all phases."""
        total = 0
        if self.kb_phase:
            total += self.kb_phase.tool_calls
        if self.tutorial_phase:
            total += self.tutorial_phase.tool_calls
        return total
    
    @property
    def total_context_overflows(self) -> int:
        """Total context overflow events."""
        total = 0
        if self.kb_phase:
            total += self.kb_phase.context_overflow_events
        if self.tutorial_phase:
            total += self.tutorial_phase.context_overflow_events
        return total
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "codebase_name": self.codebase_name,
            "model_id": self.model_id,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(self.duration_seconds, 2),
            "total_tokens": self.total_tokens,
            "total_tool_calls": self.total_tool_calls,
            "total_context_overflows": self.total_context_overflows,
            "phases": {
                "knowledge_base": self.kb_phase.to_dict() if self.kb_phase else None,
                "tutorial": self.tutorial_phase.to_dict() if self.tutorial_phase else None,
            },
        }
    
    def to_experiment_table_row(self) -> Dict[str, Any]:
        """
        Format for experiments.md Experiment 4 table.
        
        Returns dict with keys matching the table columns.
        """
        return {
            "Codebase": self.codebase_name,
            "Overall Cost (Tokens)": self.total_tokens,
            "Tool Calls": self.total_tool_calls,
            "Context Overflow": self.total_context_overflows,
            "Duration (s)": round(self.duration_seconds, 1),
        }
    
    def save_json(self, output_path: Path) -> Path:
        """Save metrics to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return output_path
    
    def save_markdown_summary(self, output_path: Path) -> Path:
        """Save metrics as markdown summary."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        lines = [
            f"# Run Metrics: {self.codebase_name}",
            "",
            f"**Model:** {self.model_id}",
            f"**Duration:** {self.duration_seconds:.1f}s ({self.duration_seconds/60:.1f}m)",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Tokens | {self.total_tokens:,} |",
            f"| Tool Calls | {self.total_tool_calls} |",
            f"| Context Overflows | {self.total_context_overflows} |",
            "",
        ]
        
        if self.kb_phase:
            lines.extend([
                "## Knowledge Base Phase",
                "",
                f"- Duration: {self.kb_phase.duration_seconds:.1f}s",
                f"- Tokens: {self.kb_phase.total_tokens:,}",
                f"- Tool Calls: {self.kb_phase.tool_calls}",
                f"- Sub-agents: {self.kb_phase.sub_agents_spawned}",
                "",
            ])
        
        if self.tutorial_phase:
            lines.extend([
                "## Tutorial Phase",
                "",
                f"- Duration: {self.tutorial_phase.duration_seconds:.1f}s",
                f"- Tokens: {self.tutorial_phase.total_tokens:,}",
                f"- Tool Calls: {self.tutorial_phase.tool_calls}",
                "",
            ])
        
        with output_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        return output_path
    
    def save_to_metrics_dir(
        self, 
        pipeline_type: str = "deep-agent",
        metrics_base_dir: Path | str = "metrics"
    ) -> Path:
        """
        Save metrics to centralized metrics directory with organized structure.
        
        Structure: metrics/{pipeline_type}/{codebase_name}_{YYYY-MM-DD_HH-MM}.json
        
        Args:
            pipeline_type: Type of pipeline (e.g., "deep-agent", "baseline")
            metrics_base_dir: Base directory for metrics storage
            
        Returns:
            Path to the saved JSON file
        """
        from datetime import datetime
        
        metrics_base = Path(metrics_base_dir)
        pipeline_dir = metrics_base / pipeline_type
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        safe_name = self.codebase_name.replace("/", "_").replace(" ", "_")
        base_filename = f"{safe_name}_{timestamp}"
        
        # Save both JSON and Markdown
        json_path = pipeline_dir / f"{base_filename}.json"
        md_path = pipeline_dir / f"{base_filename}.md"
        
        self.save_json(json_path)
        self.save_markdown_summary(md_path)
        
        return json_path
