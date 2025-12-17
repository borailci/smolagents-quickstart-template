"""Toolkit for Tutorial Supervisor Agent.

This toolkit provides tools for managing tutorial writer sub-agents and consolidating their outputs.
It is separated from the main supervisor_toolkit to allow independent pipeline execution.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import List, Optional

from loguru import logger
from smolagents import Tool

from toolkits.sub_agent_toolkit import (
    SubAgentRole,
    SubAgentTaskSpec,
    run_typed_sub_agent_tasks,
)
from toolkits.supervisor_toolkit import SupervisorContext
from toolkits.scoped_filesystem_toolkit import ensure_directory


class SpawnTutorialAgentTool(Tool):
    name = "spawn_tutorial_agent"
    description = "Spawn tutorial writer sub-agent. Returns JSON {workspace, status}."
    inputs = {
        "topic": {
            "type": "string",
            "description": "Title or topic of the tutorial",
        },
        "target_filename": {
            "type": "string",
            "description": "Desired filename (e.g., '01_getting_started.md')",
        },
        "focus_instructions": {
            "type": "string",
            "description": "Specific instructions on what to cover in this chapter",
        },
        "focus_files": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of key KB files or source files to pre-load for the agent.",
            "nullable": True
        },
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, topic: str, target_filename: str, focus_instructions: str, focus_files: list[str] = None) -> str:
        safe_name = target_filename.replace(".md", "").replace("/", "_").strip("_")
        workspace_root = self.ctx.sub_agents_root / safe_name

        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        workspace_root.mkdir(parents=True, exist_ok=True)

        # PRE-LOAD DISABLED - Agent reads files on its own
        focus_list = "\n".join(f"- `{f}`" for f in focus_files) if focus_files else "(none)"

        # Use centralized task template
        from prompts import prompts
        task_desc = prompts.TUTORIAL_SPAWN_TASK_TEMPLATE.format(
            topic=topic,
            target_filename=target_filename,
            focus_list=focus_list,
            focus_instructions=focus_instructions,
            sub_agent_path=str(workspace_root),
            knowledge_base_path=str(self.ctx.knowledge_base_root) if self.ctx.knowledge_base_root else "N/A"
        )

        spec = SubAgentTaskSpec(
            description=task_desc,
            role=SubAgentRole.TUTORIAL_WRITER,
        )

        try:
            workspaces = run_typed_sub_agent_tasks(
                [spec],
                codebase_root=self.ctx.codebase_root,
                sub_agents_root=workspace_root,
                min_interval_seconds=5.0,
                max_tool_calls=None,  # No limit
                max_directory_calls=None,  # No limit
                knowledge_base_root=self.ctx.knowledge_base_root,
                minimal_tools=False,  # Allow exploration + RAG for tutorial writers
                metrics=self.ctx.metrics,
            )

            workspace = workspaces[0] if workspaces else None
            if workspace and workspace.exists():
                # Perform immediate validation
                # Perform immediate validation
                # from utils.validation import validate_content
                
                # Tutorial writer creates target_filename, not summary.md
                # We need to find the markdown file
                output_file = workspace / target_filename
                if not output_file.exists():
                    # Fallback search
                    md_files = list(workspace.glob("*.md"))
                    if md_files:
                        output_file = md_files[0]
                
                validation_info = "Validation: N/A (file not found)"
                is_valid = False
                
                if output_file.exists():
                    try:
                        content = output_file.read_text(encoding="utf-8")
                        is_valid = len(content) >= 500
                        issues = [] if is_valid else [f"Length {len(content)} < 500"]
                        res = type('obj', (object,), {'is_valid': is_valid, 'issues': issues})
                        
                        validation_info = f"Valid: {res.is_valid}. Issues: {res.issues}"
                    except Exception as ve:
                        validation_info = f"Validation failed: {ve}"

                status = "completed" if is_valid else "completed_with_issues"

                self.ctx.spawned_agents[target_filename] = {
                    "workspace": str(workspace),
                    "status": status,
                    "validation": validation_info
                }
                return json.dumps({
                    "workspace": str(workspace), 
                    "status": status, 
                    "validation": validation_info,
                    "preview": f"File checked: {output_file.name}. {validation_info}"
                })
            else:
                return json.dumps({"workspace": str(workspace_root), "status": "failed", "error": "No output"})

        except Exception as e:
            logger.warning(f"spawn_tutorial_agent failed for {target_filename}: {e}")
            return json.dumps({"workspace": str(workspace_root), "status": "failed", "error": str(e)})


class FinalizeTutorialsTool(Tool):
    name = "finalize_tutorials"
    description = "Collect all tutorial outputs into final directory."
    inputs = {
        "workspaces": {
            "type": "array",
            "description": "List of workspace paths to collect from",
        },
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, workspaces: List[str]) -> str:
        # Group workspaces and collect files
        # Logic restored from supervisor_toolkit
        
        # Sort workspaces: non-retries first, then retries sorted by N to ensure overwrites work correctly
        def sort_key(p):
            name = Path(p).name
            if name.startswith("retry_"):
                try:
                    n = int(name.split("_")[1])
                    return 1000 + n # Retries come after originals
                except:
                    return 999
            return 0 # Originals first
            
        sorted_workspaces = sorted(workspaces, key=sort_key)
        
        collected_files = []
        for ws_path in sorted_workspaces:
            workspace = Path(ws_path)
            # If path doesn't exist, try looking in sub_agents_root
            if not workspace.exists():
                candidate = self.ctx.sub_agents_root / ws_path
                if candidate.exists():
                    workspace = candidate
            
            if not workspace.exists():
                logger.warning(f"Workspace path not found: {ws_path}")
                continue

            md_files = list(workspace.glob("*.md"))
            
            for md_file in md_files:
                if md_file.name == "summary.md": continue 
                
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if len(content.strip()) < 50: continue

                    out_path = self.ctx.output_root / md_file.name
                    out_path.write_text(content, encoding="utf-8")
                    
                    # Log if we are overwriting
                    if md_file.name in collected_files:
                        logger.info(f"Overwriting {md_file.name} with version from {workspace.name}")
                    else:
                        collected_files.append(md_file.name)
                        
                except Exception as e:
                    logger.warning(f"Failed to collect {md_file}: {e}")

        return f"Collected {len(collected_files)} tutorials to {self.ctx.output_root}: {collected_files}"


def build_tutorial_supervisor_tools(
    codebase_root: str | Path,
    sub_agents_root: str | Path,
    output_root: str | Path,
    knowledge_base_root: str | Path | None = None,
    baseline_mode: bool = False,
    metrics: Any = None,
) -> List[Tool]:
    """Create tools for the Tutorial Supervisor."""
    from toolkits.supervisor_toolkit import RetryAgentTool
    
    ctx = SupervisorContext(
        codebase_root=Path(codebase_root).expanduser().resolve(),
        sub_agents_root=ensure_directory(sub_agents_root),
        output_root=ensure_directory(output_root),
        knowledge_base_root=Path(knowledge_base_root).expanduser().resolve() if knowledge_base_root else None,
        metrics=metrics,
    )
    
    # Handle KB path safely
    kb_path = ctx.knowledge_base_root

    class ListKBTool(Tool):
        name = "list_knowledge_base"
        description = "List available knowledge base files."
        inputs = {}
        output_type = "string"
        
        def forward(self) -> str:
            if metrics:
                metrics.record_tool_call(self.name)
            if baseline_mode:
                return "[Knowledge Base Not Available in Baseline Mode - Use Codebase Tools]"
            if not kb_path or not kb_path.exists():
                return "Knowledge Base directory not found."
            return "\n".join(f.name for f in kb_path.glob("*.md"))

    class ReadKBTool(Tool):
        name = "read_knowledge_base_file"
        description = "Read a knowledge base file."
        inputs = {
            "filename": {
                "type": "string",
                "description": "Name of the file to read (e.g., executive_summary.md)",
            }
        }
        output_type = "string"
        
        def forward(self, filename: str) -> str:
            if metrics:
                metrics.record_tool_call(self.name)
            if baseline_mode:
                return "[Knowledge Base Not Available in Baseline Mode]"
            if not kb_path or not kb_path.exists():
                return "Knowledge Base directory not found."
            p = kb_path / filename
            if p.exists(): 
                return p.read_text(encoding="utf-8")[:30000] # Truncate large files
            return "File not found."

    
    # Baseline Mode Tools (Exploration)
    if baseline_mode:
        from toolkits.scoped_filesystem_toolkit import (
            ReadCodebaseFileTool,
            ListCodebaseDirectoryTool,
            GetCodebaseTreeTool,
        )
        return [
            GetCodebaseTreeTool(ctx.codebase_root, usage_callback=lambda n: metrics.record_tool_call(n) if metrics else None),
            ListCodebaseDirectoryTool(ctx.codebase_root, usage_callback=lambda n: metrics.record_tool_call(n) if metrics else None),
            ReadCodebaseFileTool(ctx.codebase_root, ctx.output_root, usage_callback=lambda n: metrics.record_tool_call(n) if metrics else None),
            SpawnTutorialAgentTool(ctx),
            RetryAgentTool(ctx),
            FinalizeTutorialsTool(ctx),
        ]

    return [
        ListKBTool(),
        ReadKBTool(),
        SpawnTutorialAgentTool(ctx),
        RetryAgentTool(ctx),
        FinalizeTutorialsTool(ctx),
    ]
