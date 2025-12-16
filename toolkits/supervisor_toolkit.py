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
    ReadCodebaseFileTool, # Renaming ReadWorkspaceFileTool to use standard codebase read if needed? No, wait.
    # Actually, let's keep ReadWorkspaceFileTool defined here for SUB-AGENT workspace reading
    # But for writing the plan, we use WriteWorkspaceFileTool pointing to OUTPUT_ROOT
)
from utils.constants import IGNORED_DIRS
from utils.path_utils import ensure_directory

__all__ = ["build_supervisor_tools", "build_tutorial_supervisor_tools", "SupervisorContext"]


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
    description = "Get codebase directory tree (max_depth=3). Returns structure and first-level dirs."
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

        # Define first_level_dirs
        first_level_dirs = sorted([
            d.name for d in self.ctx.codebase_root.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name not in IGNORED_DIRS
        ])

        return f"""# Codebase Overview

## Directory Structure
```
{tree}
```

## First-Level Directories
{', '.join(first_level_dirs)}
"""


class ListAvailableToolkitsTool(Tool):
    name = "list_available_toolkits"
    description = "List tools available to sub-agents (filesystem, RAG, etc.)."
    inputs = {}
    output_type = "string"

    def forward(self) -> str:
        return """# Sub-Agent Tools

**KB Analyzer Sub-Agents (minimal):**
- `read_codebase_file(path, start_line=1)` - Read file (350 lines max)
- `write_workspace_file(path, content)` - Write output

**Tutorial Writer Sub-Agents (full access):**
- `read_codebase_file(path)` - Read source code
- `read_knowledge_base_file(filename)` - Read KB file
- `retrieve_relevant_context(query)` - RAG semantic search
- `list_codebase_directory(path)` - List dir contents
- `get_directory_tree(path, depth)` - Directory tree
- `write_tutorial_file(path, content)` - Write output

NOTE: KB Analyzer sub-agents do NOT have directory listing. Include file paths in task.
"""


class ListAvailablePromptsTool(Tool):
    name = "list_available_prompts"
    description = "List sub-agent roles (ANALYZER, SUMMARIZER, TUTORIAL)."
    inputs = {}
    output_type = "string"

    def forward(self) -> str:
        return """# Sub-Agent Roles

- **ANALYZER**: Documents a codebase slice -> summary.md
- **SUMMARIZER**: Creates executive_summary.md from all KB files
- **TUTORIAL**: Writes step-by-step tutorials with code examples
"""


class ListCodebaseDirectoryTool(Tool):
    """Allow supervisor to list directory contents to find actual file paths."""
    name = "list_codebase_directory"
    description = "List files and folders in a directory. Use this to find actual file paths before spawning sub-agents."
    inputs = {
        "dir_path": {
            "type": "string",
            "description": "Directory path relative to codebase root (e.g., 'libs/deepagents/deepagents')",
            "nullable": True,
        }
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, dir_path: str = ".") -> str:
        from utils.path_utils import resolve_within_root
        
        # Handle None explicitly (LLM sometimes sends None instead of using default)
        if dir_path is None:
            dir_path = "."
        
        resolved = resolve_within_root(self.ctx.codebase_root, dir_path)

        
        if not resolved.exists():
            return f"ERROR: Directory '{dir_path}' not found."
        if not resolved.is_dir():
            return f"ERROR: '{dir_path}' is a file, not a directory."
        
        files = []
        dirs = []
        for entry in sorted(resolved.iterdir()):
            if entry.name.startswith(".") or entry.name in IGNORED_DIRS:
                continue
            if entry.is_dir():
                dirs.append(f"{entry.name}/")
            else:
                files.append(entry.name)
        
        result = f"# Contents of `{dir_path}`\n\n"
        if dirs:
            result += "**Directories:**\n" + "\n".join(f"- {d}" for d in dirs) + "\n\n"
        if files:
            result += "**Files:**\n" + "\n".join(f"- {f}" for f in files) + "\n"
        
        if not dirs and not files:
            result += "(empty directory)\n"
        
        return result


class ReadCodebaseFileTool(Tool):
    """Allow supervisor to read files to check their importance."""
    name = "read_codebase_file"
    description = "Read a source file to check its importance. Use for quick inspection before deciding what to document."
    inputs = {
        "file_path": {
            "type": "string",
            "description": "File path relative to codebase root",
        },
        "max_lines": {
            "type": "integer",
            "description": "Maximum lines to read (default 50 for quick inspection)",
            "nullable": True,
        }
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, file_path: str, max_lines: int = 50) -> str:
        from utils.path_utils import resolve_within_root
        
        resolved = resolve_within_root(self.ctx.codebase_root, file_path)
        
        if not resolved.exists():
            return f"ERROR: File '{file_path}' not found."
        if not resolved.is_file():
            return f"ERROR: '{file_path}' is a directory, not a file."
        
        try:
            lines = []
            with resolved.open("r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"\n... [truncated after {max_lines} lines] ...")
                        break
                    lines.append(line)
            return "".join(lines)
        except UnicodeDecodeError:
            return f"ERROR: '{file_path}' is not a text file."


        except Exception as e:
            return f"ERROR writing file: {e}"


# Removed WritePlanFileTool in favor of WriteWorkspaceFileTool
# defined in scoped_filesystem_toolkit.py and instantiated in build_supervisor_tools



class ReadWorkspaceFileTool(Tool):
    """Allow supervisor to read files from sub-agent workspaces for verification/fixing."""
    name = "read_workspace_file"
    description = "Read a file from a sub-agent's workspace (e.g., to verify content or fix issues)."
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Path to the file relative to sub-agents root (e.g., 'libs_core/sub_agent_1/summary.md')",
        }
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, file_path: str) -> str:
        try:
            # Handle both full absolute paths (if provided by agent) or relative paths
            if file_path.startswith(str(self.ctx.sub_agents_root)):
                full_path = Path(file_path)
            else:
                full_path = self.ctx.sub_agents_root / file_path
                
            if not full_path.exists():
                return f"ERROR: File not found at {file_path}"
                
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"ERROR reading file: {e}"


class RewriteWorkspaceFileTool(Tool):
    """Allow supervisor to rewrite a file in a sub-agent's workspace to fix issues."""
    name = "rewrite_workspace_file"
    description = "Overwrite a file in a sub-agent's workspace with fixed content. Use this to fix minor validation issues (headers, formatting) without respawning the agent."
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Path to the file relative to sub-agents root",
        },
        "content": {
            "type": "string",
            "description": "New content for the file",
        }
    }
    output_type = "string"

    def __init__(self, ctx: SupervisorContext, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, file_path: str, content: str) -> str:
        try:
            if file_path.startswith(str(self.ctx.sub_agents_root)):
                full_path = Path(file_path)
            else:
                full_path = self.ctx.sub_agents_root / file_path
                
            if not full_path.parent.exists():
                return f"ERROR: Directory does not exist: {full_path.parent}"
                
            full_path.write_text(content, encoding="utf-8")
            return f"Successfully rewrote {full_path.name} ({len(content)} chars)"
        except Exception as e:
            return f"ERROR rewriting file: {e}"


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

    def _preload_file_content(self, file_path: str, target_path_str: str = "", max_chars: int = 100000) -> str:
        """Pre-load file content, trying both direct path and target-relative path."""
        try:
            # 1. Try exact path (relative to codebase root)
            full_path = self.ctx.codebase_root / file_path
            
            # 2. If not found, try relative to target_path
            if not full_path.exists() and target_path_str:
                target_relative = self.ctx.codebase_root / target_path_str / file_path
                if target_relative.exists():
                    full_path = target_relative
            
            if not full_path.exists():
                return f"[File not found: {file_path} (checked relative to root and target)]"
            
            file_size = full_path.stat().st_size
            if file_size > max_chars:
                return f"[File too large ({file_size} chars). Use `read_codebase_file('{file_path}')` to read it.]"
            
            content = full_path.read_text(encoding="utf-8")
            return content
        except Exception as e:
            return f"[Error reading {file_path}: {e}]"

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

        # PRE-LOAD file contents to reduce sub-agent tool calls
        preloaded_sections = []
        for f in focus_files:
            content = self._preload_file_content(f, target_path_str=target_path)
            preloaded_sections.append(f"### `{f}`\n```python\n{content}\n```")
        
        preloaded_content = "\n\n".join(preloaded_sections) if preloaded_sections else "(no files provided)"
        
        focus_list = "\n".join(f"- `{f}`" for f in focus_files) if focus_files else "(none)"
        
        task_desc = f"""Analyze and document: `{target_path}`

## PRE-LOADED SOURCE FILES (use these directly, no need to read again):
{preloaded_content}

## YOUR TOOLS (use only if pre-loaded content is insufficient):
- `read_codebase_file(file_path)` - Read additional files if needed
- `list_codebase_directory(path)` - List directory contents
- `get_codebase_tree()` - Get directory structure
- `write_workspace_file(file_path, content)` - Save your documentation

## FILES ANALYZED:
{focus_list}

{custom_instructions or ''}

## OUTPUT REQUIREMENTS:
Write comprehensive documentation to `summary.md` covering:
1. Purpose & Overview
2. Key Components  
3. Data Flow & Dependencies
4. Code Examples (use snippets from above)

IMPORTANT: The source code is already provided above. Write directly to summary.md without additional file reads unless absolutely necessary.
"""

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


class ReadAgentOutputTool(Tool):
    name = "read_agent_output"
    description = "Read markdown file from sub-agent workspace."
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

    def __init__(self, ctx: SupervisorContext = None, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

    def forward(self, workspace_path: str, filename: str = "summary.md") -> str:
        # Try as absolute path first (or direct subdir of CWD)
        workspace = Path(workspace_path)
        
        # If context is available, try resolving relative to sub_agents_root
        if not workspace.exists() and self.ctx:
             workspace = self.ctx.sub_agents_root / workspace_path

        if not workspace.exists():
            return f"ERROR: Workspace not found: {workspace_path} (checked {workspace})"

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
            
            # FOCUSED FIX MODE
            task_desc = f"""FIX FORMATTING ISSUES: `{target_path}`

⚠️ RETRY ATTEMPT {retry_count + 1}/{self.ctx.max_retries}

SUPERVISOR FEEDBACK:
{feedback}

TARGET FILENAME: `{target_filename}`

PREVIOUS DRAFT (Contains errors):
```markdown
{previous_content}
```

YOUR TASK:
1. Fix the formatting errors listed above.
2. Output the COMPLETELY CORRECTED document.
3. Save it to `{target_filename}` using `write_workspace_file` (or `write_tutorial_file`).
4. Do NOT rewrite the content, just fix the syntax/structure.
"""
            role = SubAgentRole.TUTORIAL_WRITER if is_tutorial else SubAgentRole.ANALYZER
            minimal_tools = True # No need to search, just write
            
        else:
            # FULL REGENERATION MODE (Missing content or unknown error)
            if is_tutorial:
                # Tutorial retry - give full tools and RAG access
                task_desc = f"""⚠️ RETRY ATTEMPT {retry_count + 1}/{self.ctx.max_retries}

SUPERVISOR FEEDBACK:
{feedback}

YOUR TOOLS:
- `retrieve_relevant_context(query)` - RAG semantic search (USE THIS!)
- `read_knowledge_base_file(path)` - Read KB documentation
- `read_codebase_file(path)` - Read source code
- `list_codebase_directory(path)` - List files
- `write_tutorial_file(path, content)` - Save tutorial

FIX THE ISSUES ABOVE and rewrite the complete tutorial.
"""
                role = SubAgentRole.TUTORIAL_WRITER
                minimal_tools = False  # Full access for tutorials
            else:
                # KB analyzer retry - now with full tools for exploration
                task_desc = f"""Analyze and document: `{target_path}`

⚠️ RETRY ATTEMPT {retry_count + 1}/{self.ctx.max_retries}

SUPERVISOR FEEDBACK:
{feedback}

YOUR TOOLS (use list_codebase_directory to find correct file names!):
- `list_codebase_directory(path)` - List files in a directory (USE THIS FIRST!)
- `read_codebase_file(file_path)` - Read source files
- `get_codebase_tree()` - Get directory structure
- `write_workspace_file(file_path, content)` - Save documentation

IMPORTANT: If you don't know the exact file names, use `list_codebase_directory` first!
You MUST address the issues above. Write comprehensive documentation to `summary.md`.
"""
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

    def _preload_file_content(self, file_path: str, max_chars: int = 100000) -> str:
        """Pre-load file content from KB or Codebase."""
        try:
            # 1. Try Knowledge Base first (most likely for tutorials)
            if self.ctx.knowledge_base_root:
                kb_path = self.ctx.knowledge_base_root / file_path
                if kb_path.exists():
                    if kb_path.stat().st_size > max_chars:
                        return f"[File too large. Use `read_codebase_file` or `read_knowledge_base_file` to read '{file_path}']"
                    return kb_path.read_text(encoding="utf-8")

            # 2. Try Codebase
            code_path = self.ctx.codebase_root / file_path
            if code_path.exists():
                if code_path.stat().st_size > max_chars:
                    return f"[File too large. Use `read_codebase_file('{file_path}')`]"
                return code_path.read_text(encoding="utf-8")
            
            return f"[File not found: {file_path}]"
        except Exception as e:
            return f"[Error reading {file_path}: {e}]"

    def forward(self, topic: str, target_filename: str, focus_instructions: str, focus_files: list[str] = None) -> str:
        safe_name = target_filename.replace(".md", "").replace("/", "_").strip("_")
        workspace_root = self.ctx.sub_agents_root / safe_name

        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        workspace_root.mkdir(parents=True, exist_ok=True)

        # Pre-load content
        preloaded_section = ""
        if focus_files:
            preloaded_section = "\n## PRE-LOADED CONTEXT (Use directly, NO NEED TO READ AGAIN):\n"
            for f in focus_files:
                content = self._preload_file_content(f)
                # Helper to format markdown nicely inside the prompt
                preloaded_section += f"### `{f}`\n```markdown\n{content}\n```\n\n"

        # Optimized task description
        task_desc = f"""Write tutorial: "{topic}"
Target file: {target_filename}
{preloaded_section}
FOCUS:
{focus_instructions}

WORKFLOW:
1. REVIEW pre-loaded files above first.
2. Search KB/codebase ONLY if missing specific details.
3. Read source files ONLY to verify exact code snippets if not in context.
4. Write tutorial with real examples and Mermaid diagrams.
5. Save to `{target_filename}`
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
                max_tool_calls=None,  # No limit
                max_directory_calls=None,  # No limit
                knowledge_base_root=self.ctx.knowledge_base_root,
                minimal_tools=False,  # Allow exploration + RAG for tutorial writers
            )

            workspace = workspaces[0] if workspaces else None
            if workspace and workspace.exists():
                # Perform immediate validation
                from utils.validation import validate_content
                
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
                        res = validate_content(content, min_chars=500, check_mermaid=True)
                        is_valid = res.is_valid
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
        # Group workspaces by base target name to handle retries
        # Example: "01_getting_started" vs "retry_1_01_getting_started_sub_agent_1"
        groups = {}
        
        for ws_path in workspaces:
            path = Path(ws_path)
            name = path.name
            
            # Extract base name (simplified heuristic)
            if name.startswith("retry_"):
                # format: retry_N_basename_sub_agent_M
                # We need to find the base topic name. 
                # This is tricky without strict naming. Let's assume the component after the retry number matches.
                # Actually, simpler: just use the folder contents to decide what topic it is? 
                # Or rely on the fact that supervisor passes related items?
                # Let's trust that the supervisor might pass all of them.
                pass
            
            # Better approach: Just process them all, but sort them so retries come LAST.
            # If we process original THEN retry, the retry overwrites the original, which is CORRECT.
            # So we just need to ensure the list is sorted by creation time or name such that retries are last.
            pass

        # Sort workspaces: non-retries first, then retries sorted by N
        def sort_key(p):
            name = Path(p).name
            if name.startswith("retry_"):
                try:
                    # extract N from retry_N_
                    n = int(name.split("_")[1])
                    return 1000 + n # Retries come after originals
                except:
                    return 999
            return 0 # Originals first
            
        sorted_workspaces = sorted(workspaces, key=sort_key)
        
        collected_files = []
        for ws_path in sorted_workspaces:
            workspace = Path(ws_path)
            if not workspace.exists():
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


def build_supervisor_tools(
    codebase_root: str | Path,
    sub_agents_root: str | Path,
    output_root: str | Path,
) -> List[Tool]:
    """Create tools for the Knowledge Base Supervisor."""
    ctx = SupervisorContext(
        codebase_root=Path(codebase_root).expanduser().resolve(),
        sub_agents_root=ensure_directory(sub_agents_root),
        output_root=ensure_directory(output_root),
    )

    return [
        GetCodebaseOverviewTool(ctx),
        ListCodebaseDirectoryTool(ctx),
        ReadCodebaseFileTool(ctx),
        # Use generic WriteWorkspaceFileTool bound to supervisor's output_root
        WriteWorkspaceFileTool(workspace_root=ctx.output_root),
        ReadWorkspaceFileTool(ctx),
        RewriteWorkspaceFileTool(ctx),
        SpawnAnalyzerAgentTool(ctx),
        RetryAgentTool(ctx),
        FinalizeKnowledgeBaseTool(ctx),
    ]


def build_tutorial_supervisor_tools(
    codebase_root: str | Path,
    sub_agents_root: str | Path,
    output_root: str | Path,
    knowledge_base_root: str | Path | None = None,
    baseline_mode: bool = False,
) -> List[Tool]:
    """Create tools for the Tutorial Supervisor."""
    ctx = SupervisorContext(
        codebase_root=Path(codebase_root).expanduser().resolve(),
        sub_agents_root=ensure_directory(sub_agents_root),
        output_root=ensure_directory(output_root),
        knowledge_base_root=Path(knowledge_base_root).expanduser().resolve() if knowledge_base_root else None,
    )
    
    # Handle KB path safely
    kb_path = None
    if knowledge_base_root:
        kb_path = Path(knowledge_base_root).resolve()
        if not kb_path.exists() and not baseline_mode:
             # Only create if strict mode? or just warn?
             pass

    class ListKBTool(Tool):
        name = "list_knowledge_base"
        description = "List available knowledge base files."
        inputs = {}
        output_type = "string"
        def forward(self) -> str:
            if baseline_mode or not kb_path or not kb_path.exists():
                return "[Knowledge Base Not Available in Baseline Mode - Use Codebase Tools]"
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
            if baseline_mode or not kb_path or not kb_path.exists():
                return "[Knowledge Base Not Available in Baseline Mode]"
            p = kb_path / filename
            if p.exists(): return p.read_text(encoding="utf-8")[:10000] # truncate
            return "File not found."

    # Validation is now integrated into SpawnTutorialAgentTool
    return [
        ListKBTool(),
        ReadKBTool(),
        SpawnTutorialAgentTool(ctx),
        RetryAgentTool(ctx),
        FinalizeTutorialsTool(ctx),
    ]
