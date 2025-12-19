import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

class TaskCheckpoint:
    """
    Manages persistent state for tasks to enable resuming after failures
    and avoiding redundant work (caching).
    """
    def __init__(self, checkpoint_path: str | Path):
        self.checkpoint_path = Path(checkpoint_path)
        self.data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Load checkpoint data, initializing if empty."""
        if self.checkpoint_path.exists():
            try:
                content = self.checkpoint_path.read_text(encoding='utf-8')
                if content.strip():
                    return json.loads(content)
            except Exception as e:
                print(f"Warning: Failed to load checkpoint {self.checkpoint_path}: {e}")
        
        return {"processed_tasks": [], "results": {}}

    def is_processed(self, task_id: str) -> bool:
        """Check if a task has legally completed."""
        return task_id in self.data["processed_tasks"]

    def get_result(self, task_id: str) -> Optional[Any]:
        """Retrieve cached result for a task."""
        return self.data["results"].get(task_id)

    def save_progress(self, task_id: str, result: Any) -> None:
        """Save a task result and mark it as processed."""
        if task_id not in self.data["processed_tasks"]:
            self.data["processed_tasks"].append(task_id)
        
        self.data["results"][task_id] = result
        self._flush()

    def _flush(self) -> None:
        """Write current state to disk."""
        try:
            self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            self.checkpoint_path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2), 
                encoding='utf-8'
            )
        except Exception as e:
            print(f"Warning: Failed to save checkpoint to {self.checkpoint_path}: {e}")

    def clear(self) -> None:
        """Clear all checkpoint data."""
        self.data = {"processed_tasks": [], "results": {}}
        if self.checkpoint_path.exists():
            try:
                self.checkpoint_path.unlink()
            except Exception as e:
                print(f"Warning: Failed to delete checkpoint {self.checkpoint_path}: {e}")
