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
import os
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List

from dotenv import load_dotenv
from loguru import logger
from smolagents import Tool

from prompts import prompts
from toolkits.sub_agent_toolkit import (
    SubAgentRole,
    SubAgentTaskSpec,
    SubAgentOutputError,
    run_typed_sub_agent_tasks,
)
from toolkits.baseline_toolkit import build_baseline_tools
from utils.constants import IGNORED_DIRS, BLOCKED_EXTENSIONS
from utils.path_utils import ensure_directory

__all__ = ["build_supervisor_tools", "build_tutorial_supervisor_tools", "SupervisorContext"]

load_dotenv()


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


class GetCodebaseOverviewTool(Tool):
    name = "get_codebase_overview"
    description = "Scout the codebase structure to understand what needs documentation. Returns directory tree and README excerpt."
    inputs = {
        "max_depth": {
            "type": "integer",
            "description": "How deep to traverse the directory tree. Default 3.",
            "nullable": True,
        }
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, max_depth: int = 3) -> str:
        def build_tree(path: Path, prefix: str = "", depth: int = 0) -> List[str]:
            if depth >= max_depth:
                return []
            lines = []
            try:
                entries = sorted(
                    e for e in path.iterdir()
                    if not e.name.startswith(".") and e.name not in IGNORED_DIRS
                )
            except PermissionError:
                return [f"{prefix}[permission denied]"]

            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
                if entry.is_dir():
                    extension = "    " if is_last else "│   "
                    lines.extend(build_tree(entry, prefix + extension, depth + 1))
            return lines

        tree_lines = [f"{self.ctx.codebase_root.name}/"]
        tree_lines.extend(build_tree(self.ctx.codebase_root))
        tree = "\n".join(tree_lines[:100])

        readme_content = ""
        for readme_name in ("README.md", "README.rst", "README.txt", "README"):
            readme_path = self.ctx.codebase_root / readme_name
            if readme_path.exists():
                try:
                    readme_content = readme_path.read_text(encoding="utf-8")[:1000]
                    break
                except Exception:
                    pass

        first_level_dirs = [
            d.name for d in self.ctx.codebase_root.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name not in IGNORED_DIRS
        ]

        return f"""# Codebase Overview

## Directory Structure
```
{tree}
```

## First-Level Directories
{', '.join(first_level_dirs)}

## README Excerpt
{readme_content[:500] if readme_content else '(No README found)'}
"""


class ListAvailableToolkitsTool(Tool):
    name = "list_available_toolkits"
    description = "List all available toolkits that sub-agents can use."
    inputs = {}
    output_type = "string"

    def forward(self) -> str:
        return """# Available Toolkits for Sub-Agents

## scoped_filesystem_toolkit
Tools for reading codebase files and writing to workspace:
- read_codebase_file(file_path): Read a file from the target codebase
- write_workspace_file(file_path, content): Write output to agent workspace
- get_codebase_tree(max_depth): Get directory tree structure

## baseline_toolkit (if enabled)
Extended file operations:
- read_file_bulk(file_paths): Read multiple files at once
- search_codebase(pattern): Search for patterns in code

## rag_store (if enabled)
Semantic search:
- retrieve_relevant_context(query): Find relevant code snippets
"""


class ListAvailablePromptsTool(Tool):
    name = "list_available_prompts"
    description = "List available sub-agent roles and their prompts."
    inputs = {}
    output_type = "string"

    def forward(self) -> str:
        return """# Available Sub-Agent Roles

## ANALYZER (SUB_AGENT_KB_PROMPT)
Domain Documentation Specialist that analyzes a specific slice of the codebase.
- Reads focus files and context
- Creates comprehensive markdown documentation
- Outputs: summary.md with purpose, components, data flow, dependencies

## SUMMARIZER (SUMMARIZER_KB_PROMPT)
Executive Summarizer that creates high-level overview.
- Reads all generated documentation
- Creates executive_summary.md
- Outputs: Project overview, architecture, technologies, getting started

## TUTORIAL (TUTORIAL_AGENT_PROMPT)  
Tutorial writer that creates educational content.
- Uses Knowledge Base as primary source
- Creates tutorials with code snippets and diagrams
"""


class SpawnAnalyzerAgentTool(Tool):
    name = "spawn_analyzer_agent"
    description = "Spawn an analyzer sub-agent for a specific target. Returns JSON with workspace path and status."
    inputs = {
        "target_path": {
            "type": "string",
            "description": "Relative path to the directory/file to analyze",
        },
        "focus_files": {
            "type": "array",
            "description": "List of specific files to focus on (2-4 recommended)",
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
        safe_name = target_path.replace("/", "_").replace("\\", "_").strip("_") or "root"
        workspace_root = self.ctx.sub_agents_root / safe_name

        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        workspace_root.mkdir(parents=True, exist_ok=True)

        focus_list = "\n".join(f"- `{f}`" for f in focus_files) if focus_files else "- (explore the target directory)"
        task_desc = f"""Analyze and document: `{target_path}`

IMPORTANT: First use `get_codebase_tree` on the target directory to see actual file paths before reading files.

Suggested focus areas:
{focus_list}

{custom_instructions or ''}

Write your documentation to `summary.md` in your workspace.
"""

        spec = SubAgentTaskSpec(
            description=task_desc,
            role=SubAgentRole.ANALYZER,
        )

        try:
            workspaces = run_typed_sub_agent_tasks(
                [spec],
                codebase_root=self.ctx.codebase_root,
                sub_agents_root=workspace_root,
                min_interval_seconds=5.0,
                max_tool_calls=10,  # Keep low for speed
                max_directory_calls=2,  # Allow tree calls
            )

            workspace = workspaces[0] if workspaces else None
            if workspace and workspace.exists():
                self.ctx.spawned_agents[target_path] = {
                    "workspace": str(workspace),
                    "status": "completed",
                }
                return json.dumps({"workspace": str(workspace), "status": "completed"})
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


class ReadAgentOutputTool(Tool):
    name = "read_agent_output"
    description = "Read the output file from a sub-agent workspace."
    inputs = {
        "workspace_path": {
            "type": "string",
            "description": "Path to the agent's workspace directory",
        },
        "filename": {
            "type": "string",
            "description": "Name of the output file to read. Default: summary.md",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, workspace_path: str, filename: str = "summary.md") -> str:
        workspace = Path(workspace_path)
        if not workspace.exists():
            return f"ERROR: Workspace not found: {workspace_path}"

        target_file = workspace / filename
        if not target_file.exists():
            matches = list(workspace.rglob(filename))
            if matches:
                target_file = matches[0]
            else:
                existing = [f.name for f in workspace.rglob("*.md")]
                return f"ERROR: {filename} not found. Available files: {existing}"

        try:
            content = target_file.read_text(encoding="utf-8")
            return content
        except Exception as e:
            return f"ERROR: Could not read {filename}: {e}"


class EvaluateOutputQualityTool(Tool):
    name = "evaluate_output_quality"
    description = "Evaluate if sub-agent output meets quality standards. Returns JSON with assessment."
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
        issues = []
        stripped = content.strip()

        if not stripped:
            issues.append("Content is empty")
        elif stripped.lower() in ("_no response_", "no response"):
            issues.append("Content is placeholder text")
        elif len(stripped) < min_chars:
            issues.append(f"Content too short ({len(stripped)} chars, need {min_chars})")

        has_headers = any(line.startswith("#") for line in content.split("\n"))
        if not has_headers:
            issues.append("Missing markdown headers")

        has_code = "```" in content
        if not has_code:
            issues.append("No code snippets included")

        is_valid = len(issues) == 0
        return json.dumps({
            "valid": is_valid,
            "char_count": len(stripped),
            "has_headers": has_headers,
            "has_code": has_code,
            "issues": issues,
        })


class RetryAgentTool(Tool):
    name = "retry_agent"
    description = "Re-run a failed sub-agent with specific feedback from Supervisor."
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

        safe_name = target_path.replace("/", "_").replace("\\", "_").strip("_") or "root"
        retry_workspace = self.ctx.sub_agents_root / f"retry_{retry_count + 1}_{safe_name}"
        if retry_workspace.exists():
            shutil.rmtree(retry_workspace)
        retry_workspace.mkdir(parents=True, exist_ok=True)

        task_desc = f"""Analyze and document: `{target_path}`

⚠️ RETRY ATTEMPT {retry_count + 1}/{self.ctx.max_retries}

SUPERVISOR FEEDBACK:
{feedback}

You MUST address the issues above. Write comprehensive documentation to `summary.md`.
"""

        spec = SubAgentTaskSpec(
            description=task_desc,
            role=SubAgentRole.ANALYZER,
        )

        try:
            workspaces = run_typed_sub_agent_tasks(
                [spec],
                codebase_root=self.ctx.codebase_root,
                sub_agents_root=retry_workspace,
                min_interval_seconds=5.0,
                max_tool_calls=10,  # Keep low for speed
                max_directory_calls=2,
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
    description = "Collect all sub-agent outputs and create final knowledge base."
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


class SpawnTutorialAgentTool(Tool):
    name = "spawn_tutorial_agent"
    description = "Spawn a tutorial writer sub-agent for a specific topic."
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
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, topic: str, target_filename: str, focus_instructions: str) -> str:
        safe_name = target_filename.replace(".md", "").replace("/", "_").strip("_")
        workspace_root = self.ctx.sub_agents_root / safe_name

        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        workspace_root.mkdir(parents=True, exist_ok=True)

        task_desc = f"""Write a tutorial: "{topic}"
Target file: {target_filename}

INSTRUCTIONS:
{focus_instructions}

Write your final tutorial to `{target_filename}` in your workspace.
"""

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
                max_tool_calls=10,
                max_directory_calls=1, # KB lookup mostly
                knowledge_base_root=self.ctx.knowledge_base_root,
            )

            workspace = workspaces[0] if workspaces else None
            if workspace and workspace.exists():
                self.ctx.spawned_agents[target_filename] = {
                    "workspace": str(workspace),
                    "status": "completed",
                }
                return json.dumps({"workspace": str(workspace), "status": "completed"})
            else:
                return json.dumps({"workspace": str(workspace_root), "status": "failed", "error": "No output"})

        except Exception as e:
            logger.warning(f"spawn_tutorial_agent failed for {target_filename}: {e}")
            return json.dumps({"workspace": str(workspace_root), "status": "failed", "error": str(e)})


class SpawnBaselineAgentTool(Tool):
    name = "spawn_tutorial_agent"  # Re-use name so supervisor prompt works
    description = "Spawn a baseline tutorial writer sub-agent (No KB access) for a specific topic."
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
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, topic: str, target_filename: str, focus_instructions: str) -> str:
        safe_name = target_filename.replace(".md", "").replace("/", "_").strip("_")
        workspace_root = self.ctx.sub_agents_root / safe_name

        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        workspace_root.mkdir(parents=True, exist_ok=True)

        task_desc = f"""Write a tutorial: "{topic}"
Target file: {target_filename}

INSTRUCTIONS:
{focus_instructions}

Write your final tutorial to `{target_filename}` in your workspace.
"""
        
        # Build baseline tools for this specific agent
        # Note: We pass workspace_root as tutorial_output_root so write_file goes there
        baseline_tools = build_baseline_tools(
            codebase_root=self.ctx.codebase_root,
            tutorial_output_root=workspace_root,
            knowledge_base_root=self.ctx.knowledge_base_root or self.ctx.output_root, 
            # Baseline tools may use RAG if enabled in environment (RAG_CODEBASE_CACHE_DIR)
        )

        spec = SubAgentTaskSpec(
            description=task_desc,
            role=SubAgentRole.TUTORIAL_WRITER,
            output_format="Markdown file",
            tools=baseline_tools, 
        )

        try:
            # We use run_typed_sub_agent_tasks but override the prompt with our BASELINE prompt
            workspaces = run_typed_sub_agent_tasks(
                [spec],
                codebase_root=self.ctx.codebase_root,
                sub_agents_root=workspace_root,
                min_interval_seconds=10.0,
                max_tool_calls=30, # Baseline needs more steps to explore
                max_directory_calls=1,
            )

            workspace = workspaces[0] if workspaces else None
            if workspace and workspace.exists():
                self.ctx.spawned_agents[target_filename] = {
                    "workspace": str(workspace_root),
                    "status": "completed",
                }
                return json.dumps({"workspace": str(workspace_root), "status": "completed"})
            else:
                return json.dumps({"workspace": str(workspace_root), "status": "failed", "error": "No output"})

        except Exception as e:
            logger.warning(f"spawn_tutorial_agent (baseline) failed for {target_filename}: {e}")
            return json.dumps({"workspace": str(workspace_root), "status": "failed", "error": str(e)})


class FinalizeTutorialsTool(Tool):
    name = "finalize_tutorials"
    description = "Collect all successful tutorials into the final output directory."
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

            # Look for any markdown file that isn't summary.md (unless explicitly named so)
            # Actually tutorial writer writes to target_filename.
            md_files = list(workspace.glob("*.md"))
            
            for md_file in md_files:
                if md_file.name == "summary.md": continue # skip artifacts if any
                
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if len(content.strip()) < 50: continue

                    out_path = self.ctx.output_root / md_file.name
                    out_path.write_text(content, encoding="utf-8")
                    collected_files.append(md_file.name)
                except Exception as e:
                    logger.warning(f"Failed to collect {md_file}: {e}")

        return f"Collected {len(collected_files)} tutorials to {self.ctx.output_root}: {collected_files}"


def build_supervisor_tools(
    codebase_root: str | Path,
    sub_agents_root: str | Path,
    output_root: str | Path,
    usage_callback: Callable[[str], None] | None = None,
) -> List[Tool]:
    """Create tools for the Knowledge Base Supervisor."""
    ctx = SupervisorContext(
        codebase_root=Path(codebase_root).expanduser().resolve(),
        sub_agents_root=ensure_directory(sub_agents_root),
        output_root=ensure_directory(output_root),
    )

    return [
        GetCodebaseOverviewTool(ctx),
        ListAvailableToolkitsTool(),
        ListAvailablePromptsTool(),
        SpawnAnalyzerAgentTool(ctx),
        ReadAgentOutputTool(),
        EvaluateOutputQualityTool(),
        RetryAgentTool(ctx),
        FinalizeKnowledgeBaseTool(ctx),
    ]


def build_tutorial_supervisor_tools(
    codebase_root: str | Path,
    sub_agents_root: str | Path,
    output_root: str | Path,
    knowledge_base_root: str | Path, 
    baseline_mode: bool = False,
) -> List[Tool]:
    """Create tools for the Tutorial Supervisor."""
    ctx = SupervisorContext(
        codebase_root=Path(codebase_root).expanduser().resolve(),
        sub_agents_root=ensure_directory(sub_agents_root),
        output_root=ensure_directory(output_root),
        knowledge_base_root=Path(knowledge_base_root).expanduser().resolve() if knowledge_base_root else None,
    )
    
    if baseline_mode:
        # Baseline mode: No KB tools, specialized spawn tool
        return [
            GetCodebaseOverviewTool(ctx), # Baseline needs to explore codebase explicitly
            SpawnBaselineAgentTool(ctx),
            ReadAgentOutputTool(),
            EvaluateOutputQualityTool(),
            RetryAgentTool(ctx),
            FinalizeTutorialsTool(ctx),
        ]
    
    # Standard mode
    kb_path = Path(knowledge_base_root).resolve()
    
    class ListKBTool(Tool):
        name = "list_knowledge_base"
        description = "List available knowledge base files."
        inputs = {}
        output_type = "string"
        def forward(self) -> str:
            return "\\n".join(f.name for f in kb_path.glob("*.md"))

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
            p = kb_path / filename
            if p.exists(): return p.read_text(encoding="utf-8")[:10000] # truncate
            return "File not found."

    return [
        ListKBTool(),
        ReadKBTool(),
        SpawnTutorialAgentTool(ctx),
        ReadAgentOutputTool(),
        EvaluateOutputQualityTool(),
        RetryAgentTool(ctx),
        FinalizeTutorialsTool(ctx),
    ]
