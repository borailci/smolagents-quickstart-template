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
)
from config import settings
from utils.constants import IGNORED_DIRS
from utils.path_utils import ensure_directory

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
    ):
        self.codebase_root = codebase_root
        self.sub_agents_root = sub_agents_root
        self.output_root = output_root
        self.max_retries = max_retries
        self.knowledge_base_root = knowledge_base_root
        self.spawned_agents: Dict[str, Dict[str, Any]] = {}
        self.retry_counts: Dict[str, int] = {}


# ---------------------------------------------------------------------------
# Tool classes (smolagents compatible)
# ---------------------------------------------------------------------------


# GetCodebaseOverviewTool moved to scoped_filesystem_toolkit.py




# ListCodebaseDirectoryTool, ReadCodebaseFileTool moved to scoped_filesystem_toolkit.py
# ReadWorkspaceFileTool, RewriteWorkspaceFileTool also moved


class SpawnAnalyzerAgentTool(Tool):
    name = "spawn_analyzer_agent"
    description = "Spawn analyzer sub-agent for a directory. Returns JSON {workspace, status}."
    inputs = {
        "target_path": {
            "type": "string",
            "description": "Relative path to the directory/file to analyze",
        },
        "focus_files": {
            "type": "array",
            "description": "List of specific files to focus on (3-5 recommended)",
        },
        "custom_instructions": {
            "type": "string",
            "description": "Additional instructions from Supervisor",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, target_path: str, focus_files: List[str], custom_instructions: str = "") -> str:
        # Use only the last 2 path components to avoid excessively long folder names
        path_obj = Path(target_path)
        parts = path_obj.parts[-2:] if len(path_obj.parts) >= 2 else path_obj.parts
        short_name = "_".join(parts).replace("/", "_").replace("\\", "_").strip("_") or "root"
        safe_name = short_name[:50]  # Truncate to max 50 chars
        workspace_root = self.ctx.sub_agents_root / safe_name

        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        workspace_root.mkdir(parents=True, exist_ok=True)

        # PRE-LOAD DISABLED - Agent reads files on its own to reduce input tokens
        focus_list = "\n".join(f"- `{f}`" for f in focus_files) if focus_files else "(none)"
        
        # Use centralized task template from prompts.py
        from prompts import prompts
        task_desc = prompts.ANALYZER_SPAWN_TASK_TEMPLATE.format(
            target_path=target_path,
            focus_list=focus_list,
            custom_instructions=custom_instructions or ""
        )

        spec = SubAgentTaskSpec(
            description=task_desc,
            role=SubAgentRole.ANALYZER,
        )

        try:
            import time
            start_time = time.monotonic()
            workspaces = run_typed_sub_agent_tasks(
                [spec],
                codebase_root=self.ctx.codebase_root,
                sub_agents_root=workspace_root,
                min_interval_seconds=5.0,
                max_tool_calls=None,
                max_directory_calls=None,
            minimal_tools=False,  # Enable all tools per architecture spec
            )
            
            # --- METRICS LOGGING ---
            duration = time.monotonic() - start_time
            try:
                metrics_file = self.ctx.output_root / "metrics.md"
                if not metrics_file.exists():
                    metrics_file.write_text("# Agent Execution Metrics\n\n| Date | Agent | Target | Duration |\n|---|---|---|---|\n", encoding="utf-8")
                
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                target_name = target_path if len(target_path) < 40 else f"...{target_path[-37:]}"
                metrics_line = f"| {timestamp} | Analyzer | `{target_name}` | {duration:.2f}s |\n"
                
                with metrics_file.open("a", encoding="utf-8") as f:
                    f.write(metrics_line)
            except Exception as e:
                logger.warning(f"Failed to write metrics: {e}")
            # -----------------------

            workspace = workspaces[0] if workspaces else None
            if workspace and workspace.exists():
                # Perform immediate validation
                from utils.validation import validate_content
                
                output_file = workspace / "summary.md"
                validation_info = "Validation: N/A (file not found)"
                is_valid = False
                
                if output_file.exists():
                    try:
                        content = output_file.read_text(encoding="utf-8")
                        res = validate_content(content, min_chars=100)
                        is_valid = res.is_valid
                        validation_info = f"Valid: {res.is_valid}. Issues: {res.issues}"
                    except Exception as ve:
                        validation_info = f"Validation failed: {ve}"
                
                status = "completed" if is_valid else "completed_with_issues"
                
                self.ctx.spawned_agents[target_path] = {
                    "workspace": str(workspace),
                    "status": status,
                    "validation": validation_info
                }
                
                return json.dumps({
                    "workspace": str(workspace), 
                    "status": status, 
                    "validation": validation_info,
                    "preview": f"File created at {output_file.name}. {validation_info}"
                })
            else:
                self.ctx.spawned_agents[target_path] = {
                    "workspace": str(workspace_root),
                    "status": "failed",
                    "error": "No workspace returned",
                }
                return json.dumps({"workspace": str(workspace_root), "status": "failed", "error": "No workspace returned"})

        except Exception as e:
            logger.warning(f"spawn_analyzer_agent failed for {target_path}: {e}")
            self.ctx.spawned_agents[target_path] = {
                "workspace": str(workspace_root),
                "status": "failed",
                "error": str(e),
            }
            return json.dumps({"workspace": str(workspace_root), "status": "failed", "error": str(e)})



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
        from utils.validation import validate_content
        
        result = validate_content(
            content,
            min_chars=min_chars,
            check_mermaid=True,
            strict_heading_start=False,  # Allow blockquotes
        )
        return json.dumps(result.to_dict())


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
            if not workspace.exists():
                continue

            # Extract target name from workspace path (e.g., "app" from ".../app/sub_agent_1")
            # Go up from sub_agent_1 to find the target directory name
            target_name = workspace.parent.name
            if target_name in ("sub_agents_workspace", "data"):
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
    )
    
    codebase_path = ctx.codebase_root
    workspace_path = ctx.output_root

    return [
        # Filesystem tools from scoped_filesystem_toolkit
        GetCodebaseTreeTool(codebase_path, None),  # get_codebase_overview equivalent
        ListCodebaseDirectoryTool(codebase_path, None),
        ReadCodebaseFileTool(codebase_path, workspace_path, None),
        WriteWorkspaceFileTool(workspace_path, None),
        # Agent management tools
        SpawnAnalyzerAgentTool(ctx),
        EvaluateOutputQualityTool(),
        RetryAgentTool(ctx),
        FinalizeKnowledgeBaseTool(ctx),
    ]



# build_tutorial_supervisor_tools removed - tutorials are now a separate pipeline

