"""Supervisor Agent toolkit for coordinating sub-agents.

Provides tools for the Supervisor Agent to:
- Scout codebase structure
- Know available toolkits and prompts
- Spawn and manage analyzer sub-agents
- Evaluate sub-agent outputs
- Retry failed sub-agents with feedback
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger
from smolagents import Tool

from toolkits.sub_agent_toolkit import (
    SubAgentRole,
    SubAgentTaskSpec,
    run_typed_sub_agent_tasks,
)
from toolkits.scoped_filesystem_toolkit import (
    WriteWorkspaceFileTool, 
    ReadCodebaseFileTool,
    ensure_directory,
    IGNORED_DIRS,
)
from config import settings

__all__ = ["build_supervisor_tools", "SupervisorContext"]


class SupervisorContext:
    """Shared context for supervisor tools."""

    def __init__(
        self,
        codebase_root: Path,
        sub_agents_root: Path,
        output_root: Path,
        max_retries: int = 2,
        knowledge_base_root: Path | None = None,
        metrics: Any = None,
    ):
        self.codebase_root = codebase_root
        self.sub_agents_root = sub_agents_root
        self.output_root = output_root
        self.max_retries = max_retries
        self.knowledge_base_root = knowledge_base_root
        self.metrics = metrics
        self.spawned_agents: Dict[str, Dict[str, Any]] = {}
        self.spawned_agents: Dict[str, Dict[str, Any]] = {}
        self.retry_counts: Dict[str, int] = {}


# ---------------------------------------------------------------------------
# Tool classes (smolagents compatible)
# ---------------------------------------------------------------------------


# GetCodebaseOverviewTool moved to scoped_filesystem_toolkit.py




# ListCodebaseDirectoryTool, ReadCodebaseFileTool moved to scoped_filesystem_toolkit.py
# ReadWorkspaceFileTool, RewriteWorkspaceFileTool also moved


class SpawnSubAgentsTool(Tool):
    name = "spawn_sub_agents"
    description = "Spawn multiple sub-agents in batch to analyze parts of the codebase. Returns a summary of results."
    inputs = {
        "tasks": {
            "type": "array",
            "description": "List of task objects. Each object must have: 'target_path', 'focus_files' (list), 'agent_type' ('analyzer'|'summarizer'), and optional 'custom_instructions'.",
            "items": {
                "type": "object",
                "properties": {
                    "target_path": {"type": "string"},
                    "focus_files": {"type": "array", "items": {"type": "string"}},
                    "agent_type": {"type": "string", "enum": ["analyzer", "summarizer"]},
                    "custom_instructions": {"type": "string", "nullable": True}
                },
                "required": ["target_path", "focus_files"]
            }
        }
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        # Initialize Checkpoint
        from utils.checkpoint import TaskCheckpoint
        checkpoint_path = ctx.output_root / "analysis_checkpoint.json"
        self.checkpoint = TaskCheckpoint(checkpoint_path)

    def forward(self, tasks: List[Dict[str, Any]]) -> str:
        results_summary = []
        specs_to_run = []
        task_metadata = [] # Keep track of metadata for the specs

        # 1. Filter and Prepare Tasks
        for task in tasks:
            target_path = task.get("target_path")
            focus_files = task.get("focus_files", [])
            agent_type = task.get("agent_type", "analyzer")
            custom_instructions = task.get("custom_instructions", "")

            # CHECKPOINT CHECK
            if self.checkpoint.is_processed(target_path):
                result = self.checkpoint.get_result(target_path)
                if result:
                    self.ctx.spawned_agents[target_path] = json.loads(result)
                    logger.info(f"⏩ [SKIP] {target_path} already analyzed.")
                    results_summary.append(f"- {target_path}: Skipped (Already Completed)")
                    continue
            
            # Prepare Spec
            focus_list = "\n".join(f"- `{f}`" for f in focus_files) if focus_files else "(none)"
            
            # Determine Real Directory (for 'partX' virtual paths)
            real_directory = target_path
            if focus_files:
                import os
                # Use the directory of the first file as the "real" directory context
                first_file = focus_files[0]
                real_directory = os.path.dirname(first_file)
                if not real_directory: # If file is at root
                    real_directory = "."
            
            from prompts import prompts
            if agent_type == "summarizer":
                task_desc = prompts.SUMMARIZER_SPAWN_TASK_TEMPLATE.format(
                    target_path=target_path,
                    focus_list=focus_list,
                    real_directory=real_directory
                )
            else:
                 task_desc = prompts.ANALYZER_SPAWN_TASK_TEMPLATE.format(
                    target_path=target_path,
                    focus_list=focus_list,
                    real_directory=real_directory,
                    custom_instructions=custom_instructions or ""
                )
            
            spec = SubAgentTaskSpec(
                description=task_desc,
                role=SubAgentRole.ANALYZER, # Underlying role is same, prompt differs
            )
            
            specs_to_run.append(spec)
            task_metadata.append({
                "target_path": target_path,
                "agent_type": agent_type
            })

        if not specs_to_run:
            return "All requested tasks were already completed (Checkpoint).\n" + "\n".join(results_summary)

        # 2. Run Batch
        logger.info(f"🚀 Spawning batch of {len(specs_to_run)} sub-agents...")
        
        # We need a way to map workspaces back to targets. 
        # run_typed_sub_agent_tasks returns list[Path].
        # We assume order is preserved (it should be).
        
        try:
            workspaces = run_typed_sub_agent_tasks(
                specs_to_run,
                codebase_root=self.ctx.codebase_root,
                sub_agents_root=self.ctx.sub_agents_root, # They will be specialized inside
                min_interval_seconds=5.0,
                max_tool_calls=None,
                max_directory_calls=None,
                minimal_tools=False,
                metrics=self.ctx.metrics,
            )
            
            # 3. Process Results
            for i, workspace in enumerate(workspaces):
                meta = task_metadata[i]
                target_path = meta["target_path"]
                
                if workspace and workspace.exists():
                    # Validate
                    output_file = workspace / "summary.md"
                    validation_info = "No output file."
                    is_valid = False
                    
                    if output_file.exists():
                        content = output_file.read_text(encoding="utf-8")
                        is_valid = len(content) >= 100
                        validation_info = "Valid" if is_valid else f"Too short ({len(content)})"
                    
                    status = "completed" if is_valid else "completed_with_issues"
                    result_data = {
                        "workspace": str(workspace),
                        "status": status,
                        "validation": validation_info
                    }
                    
                    self.ctx.spawned_agents[target_path] = result_data
                    
                    # Update Checkpoint
                    if is_valid:
                        self.checkpoint.save_progress(target_path, json.dumps(result_data))
                        results_summary.append(f"- {target_path}: Success ({workspace.name})")
                    else:
                        results_summary.append(f"- {target_path}: Failed validation ({workspace.name})")

                else:
                    results_summary.append(f"- {target_path}: Failed (No workspace)")
                    
            # Auto-update compilation plan
            self._update_compilation_plan(task_metadata)

        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            return f"Batch execution failed: {e}"

        return "Batch Execution Summary:\n" + "\n".join(results_summary)

    def _update_compilation_plan(self, metadata: List[Dict]):
        try:
            plan_file = self.ctx.output_root / "compilation_plan.md"
            if plan_file.exists():
                content = plan_file.read_text(encoding="utf-8")
                lines = content.splitlines()
                updated_lines = []
                targets = [m["target_path"] for m in metadata]
                
                for line in lines:
                    for t in targets:
                        if t in line and "[ ]" in line:
                            line = line.replace("[ ]", "[x]")
                    updated_lines.append(line)
                
                plan_file.write_text("\n".join(updated_lines), encoding="utf-8")
        except Exception:
            pass



class EvaluateOutputQualityTool(Tool):
    name = "evaluate_output_quality"
    description = "Check if output is valid (has headers, code, min length). Returns JSON."
    inputs = {
        "content": {
            "type": "string",
            "description": "The content to evaluate",
        },
        "min_chars": {
            "type": "integer",
            "description": "Minimum character count required. Default 100.",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, content: str, min_chars: int = 100) -> str:
        is_valid = len(content) >= min_chars
        issues = []
        if not is_valid:
            issues.append(f"Length {len(content)} < {min_chars}")
        
        return json.dumps({"is_valid": is_valid, "issues": issues})


class RetryAgentTool(Tool):
    name = "retry_agent"
    description = "Retry failed sub-agent with supervisor feedback."
    inputs = {
        "target_path": {
            "type": "string",
            "description": "The target that needs to be re-analyzed",
        },
        "feedback": {
            "type": "string",
            "description": "Specific feedback about what was wrong and what to improve",
        },
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, target_path: str, feedback: str) -> str:
        retry_count = self.ctx.retry_counts.get(target_path, 0)
        if retry_count >= self.ctx.max_retries:
            return json.dumps({"status": "max_retries_exceeded", "error": f"Already retried {retry_count} times"})

        self.ctx.retry_counts[target_path] = retry_count + 1

        # Use only the last 2 path components to avoid excessively long folder names
        path_obj = Path(target_path)
        parts = path_obj.parts[-2:] if len(path_obj.parts) >= 2 else path_obj.parts
        short_name = "_".join(parts).replace("/", "_").replace("\\", "_").strip("_") or "root"
        # Truncate to max 50 chars to keep paths manageable
        safe_name = short_name[:50]
        
        # --- WORKSPACE SELECTION ---
        # User requested inplace retries. Try to find original workspace.
        original_workspace_path = None
        
        # 1. Exact match
        if target_path in self.ctx.spawned_agents:
            original_workspace_path = self.ctx.spawned_agents[target_path].get("workspace")
            
        # 2. Fuzzy match (check if target_path is part of key or vice versa)
        if not original_workspace_path:
            target_clean = target_path.replace(".md", "").lower()
            for key, data in self.ctx.spawned_agents.items():
                key_clean = key.replace(".md", "").lower()
                if target_clean in key_clean or key_clean in target_clean:
                    original_workspace_path = data.get("workspace")
                    logger.info(f"RetryAgent fuzzy matched '{target_path}' to '{key}' workspace")
                    break

        if original_workspace_path:
             retry_workspace = Path(original_workspace_path)
             logger.info(f"RetryAgent reusing existing workspace: {retry_workspace}")
        else:
             # Fallback if original not found (should not happen normally)
             logger.warning(f"RetryAgent could not find original workspace for '{target_path}'. Creating new.")
             retry_workspace = self.ctx.sub_agents_root / f"retry_{retry_count + 1}_{safe_name}"
             if retry_workspace.exists():
                 shutil.rmtree(retry_workspace)
             retry_workspace.mkdir(parents=True, exist_ok=True)

        # Detect if this is a tutorial retry
        is_tutorial = "tutorial" in target_path.lower() or target_path.endswith(".md")
        
        # --- SMART RETRY LOGIC ---
        # Check if the feedback indicates a simple formatting/syntax issue
        formatting_keywords = [
            "formatting", "format", "syntax", "unbalanced", "paired", 
            "closing", "code block", "markdown", "invalid"
        ]
        is_formatting_issue = any(k in feedback.lower() for k in formatting_keywords)
        
        # Try to find previous draft to pre-load
        previous_content = ""
        # Use the resolved original_workspace_path instead of trying to get it again
        previous_workspace_path = original_workspace_path 
        if previous_workspace_path:
            try:
                # Find the relevant markdown file
                prev_ws = Path(previous_workspace_path)
                # For KB: summary.md. For Tutorial: target_path might be filename? Not guaranteed.
                # Heuristic: Find largest MD file that is not empty
                md_files = list(prev_ws.glob("*.md"))
                target_md = None
                
                if is_tutorial and target_path.endswith(".md"):
                     # If target_path is filename, look for it
                     target_md = prev_ws / target_path
                     if not target_md.exists(): target_md = None
                
                if not target_md and md_files:
                    # Default to summary.md or the largest file
                    summary = prev_ws / "summary.md"
                    if summary.exists():
                        target_md = summary
                    else:
                        # Pick largest
                        target_md = max(md_files, key=lambda p: p.stat().st_size)
                
                if target_md and target_md.exists():
                    previous_content = target_md.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to read previous draft for retry: {e}")

        # Construct Task & Tools based on issue type
        if is_formatting_issue and previous_content:
            target_filename = target_md.name if target_md else "summary.md"
            
            # Use centralized task template
            from prompts import prompts
            task_desc = prompts.FIX_FORMATTING_TASK_TEMPLATE.format(
                target_path=target_path,
                retry_count=retry_count + 1,
                max_retries=self.ctx.max_retries,
                feedback=feedback,
                target_filename=target_filename,
                previous_content=previous_content
            )
            role = SubAgentRole.TUTORIAL_WRITER if is_tutorial else SubAgentRole.ANALYZER
            minimal_tools = True # No need to search, just write
            
        else:
            # FULL REGENERATION MODE (Missing content or unknown error)
            from prompts import prompts
            if is_tutorial:
                # Tutorial retry - give full tools and RAG access
                task_desc = prompts.TUTORIAL_RETRY_TASK_TEMPLATE.format(
                    retry_count=retry_count + 1,
                    max_retries=self.ctx.max_retries,
                    feedback=feedback
                )
                role = SubAgentRole.TUTORIAL_WRITER
                minimal_tools = False  # Full access for tutorials
            else:
                # KB analyzer retry - now with full tools for exploration
                task_desc = prompts.KB_RETRY_TASK_TEMPLATE.format(
                    target_path=target_path,
                    retry_count=retry_count + 1,
                    max_retries=self.ctx.max_retries,
                    feedback=feedback
                )
                role = SubAgentRole.ANALYZER
                minimal_tools = False  # Enable all tools for retry

        spec = SubAgentTaskSpec(
            description=task_desc,
            role=role,
        )

        try:
            workspaces = run_typed_sub_agent_tasks(
                [spec],
                codebase_root=self.ctx.codebase_root,
                sub_agents_root=retry_workspace,
                min_interval_seconds=5.0,
                max_tool_calls=None,  # No limit
                max_directory_calls=None,  # No limit
                knowledge_base_root=self.ctx.knowledge_base_root,
                minimal_tools=minimal_tools,
                metrics=self.ctx.metrics,
            )

            workspace = workspaces[0] if workspaces else None
            if workspace and workspace.exists():
                self.ctx.spawned_agents[target_path] = {
                    "workspace": str(workspace),
                    "status": "retry_completed",
                }
                return json.dumps({"workspace": str(workspace), "status": "retry_completed"})
            else:
                return json.dumps({"workspace": str(retry_workspace), "status": "retry_failed", "error": "No output"})

        except Exception as e:
            logger.warning(f"retry_agent failed for {target_path}: {e}")
            return json.dumps({"workspace": str(retry_workspace), "status": "retry_failed", "error": str(e)})


class FinalizeKnowledgeBaseTool(Tool):
    name = "finalize_knowledge_base"
    description = "Collect all sub-agent outputs into final KB directory."
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
        collected_files = []
        for ws_path in workspaces:
            workspace = Path(ws_path)
            # If path doesn't exist, try looking in sub_agents_root
            if not workspace.exists():
                candidate = self.ctx.sub_agents_root / ws_path
                if candidate.exists():
                    workspace = candidate
            
            # If still not found, check if it's a logical target name (e.g. "src/auth") mapped in context
            if not workspace.exists() and ws_path in self.ctx.spawned_agents:
                data = self.ctx.spawned_agents[ws_path]
                if "workspace" in data:
                    workspace = Path(data["workspace"])
                    logger.info(f"Resolved logical path '{ws_path}' to workspace '{workspace.name}'")

            if not workspace.exists():
                logger.warning(f"Workspace path not found: {ws_path}")
                continue

            # Extract target name from workspace path (e.g., "app" from ".../app/sub_agent_1")
            # Go up from sub_agent_1 to find the target directory name
            target_name = workspace.parent.name
            # If parent is a generic container, use the workspace name itself (e.g. instructor_dsl_validation)
            if target_name in ("sub_agents_kb", "sub_agents_workspace", "sub_agents") or target_name.startswith("sub_agent"):
                target_name = workspace.name
            
            # Find the first/main markdown file in this workspace
            md_files = list(workspace.glob("*.md"))
            if not md_files:
                md_files = list(workspace.rglob("*.md"))
            
            if not md_files:
                logger.warning(f"No markdown files found in {workspace}")
                continue
            
            # Take the first (usually summary.md)
            main_file = md_files[0]
            
            try:
                content = main_file.read_text(encoding="utf-8")
                if len(content.strip()) < 50:
                    logger.warning(f"Skipping {main_file.name} - too short ({len(content.strip())} chars)")
                    continue

                # Use target directory name for output file
                out_name = f"{target_name}.md"
                out_path = self.ctx.output_root / out_name
                out_path.write_text(content, encoding="utf-8")
                collected_files.append(out_name)
                logger.info(f"Collected {main_file} -> {out_name}")

            except Exception as e:
                logger.warning(f"Failed to collect {main_file}: {e}")

        return f"Collected {len(collected_files)} files to {self.ctx.output_root}: {collected_files}"


# SpawnTutorialAgentTool removed - tutorials are now a separate pipeline





# FinalizeTutorialsTool removed - tutorials are now a separate pipeline




def build_supervisor_tools(
    codebase_root: str | Path,
    sub_agents_root: str | Path,
    output_root: str | Path,
    metrics: Any = None,
) -> List[Tool]:
    """Create tools for the Knowledge Base Supervisor."""
    from toolkits.scoped_filesystem_toolkit import (
        ReadCodebaseFileTool,
        ListCodebaseDirectoryTool,
        WriteWorkspaceFileTool,
        GetCodebaseTreeTool,
    )
    
    ctx = SupervisorContext(
        codebase_root=Path(codebase_root).expanduser().resolve(),
        sub_agents_root=ensure_directory(sub_agents_root),
        output_root=ensure_directory(output_root),
        metrics=metrics,
    )
    
    codebase_path = ctx.codebase_root
    workspace_path = ctx.output_root

    usage_cb = None
    if metrics:
        def _cb(tool_name: str):
            metrics.record_tool_call(tool_name)
        usage_cb = _cb

    return [
        # Filesystem tools from scoped_filesystem_toolkit
        GetCodebaseTreeTool(codebase_path, usage_cb),  # get_codebase_overview equivalent
        ListCodebaseDirectoryTool(codebase_path, usage_cb),
        ReadCodebaseFileTool(codebase_path, workspace_path, usage_cb),
        WriteWorkspaceFileTool(workspace_path, usage_cb),
        # Agent management tools
        SpawnSubAgentsTool(ctx),
        EvaluateOutputQualityTool(),
        RetryAgentTool(ctx),
        FinalizeKnowledgeBaseTool(ctx),
    ]



# build_tutorial_supervisor_tools removed - tutorials are now a separate pipeline

