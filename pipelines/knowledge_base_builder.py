"""Build the knowledge base for a codebase using sub-agents."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, cast

from dotenv import load_dotenv
from loguru import logger

from toolkits.sub_agent_toolkit import (
    SubAgentRole,
    SubAgentTaskSpec,
    run_typed_sub_agent_tasks,
)
from prompts import prompts
from utils.path_utils import ensure_directory

load_dotenv()

CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
KNOWLEDGE_BASE_OUTPUT_PATH = os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
SUB_AGENTS_ROOT_PATH = os.getenv("SUB_AGENTS_ROOT_PATH")

# Directories to ignore during scanning
_IGNORED_SCAN_DIRS = {
    "node_modules", "venv", "env", ".git", ".idea", ".vscode", 
    "__pycache__", "dist", "build", "site-packages", "htmlcov", ".mypy_cache"
}


@dataclass(frozen=True)
class DocumentationTarget:
    path: Path
    label: str

    @property
    def identifier(self) -> str:
        # Sanitize path for use as a filename/directory name
        safe = str(self.path).replace(os.sep, "_").replace("/", "_").replace("\\", "_")
        return safe if safe else "root"


@dataclass(frozen=True)
class AgentWorkspaceResult:
    index: int
    target: DocumentationTarget
    workspace: Path | None
    error: str | None = None


class KnowledgeBaseBuilder:
    def __init__(
        self,
        codebase_root: str | Path | None = None,
        output_root: str | Path | None = None,
        sub_agents_root: str | Path | None = None,
        dry_run: bool = False,
        force_rebuild: bool = False,  # NEW: Force regeneration of all targets
    ):
        env_codebase = codebase_root or os.getenv("CODEBASE_ROOT_PATH")
        env_output = output_root or os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
        env_sub_agents = sub_agents_root or os.getenv("SUB_AGENTS_ROOT_PATH")

        self.dry_run = dry_run
        self.force_rebuild = force_rebuild

        if not env_codebase:
            raise RuntimeError("CODEBASE_ROOT_PATH is not configured.")
        if not env_output:
            raise RuntimeError("KNOWLEDGE_BASE_OUTPUT_PATH is not configured.")
        if not env_sub_agents:
            raise RuntimeError("SUB_AGENTS_ROOT_PATH is not configured.")

        root_value = cast(str | Path, env_codebase)
        output_value = cast(str | Path, env_output)
        sub_agents_value = cast(str | Path, env_sub_agents)

        self.codebase_root = Path(root_value).expanduser().resolve()
        self.output_root = ensure_directory(output_value)
        self.sub_agents_root = ensure_directory(sub_agents_value)
        self.plan_path = self.output_root / "plan.md"
        self._plan_state: Dict[str, Dict[str, str]] = {}

        if not self.codebase_root.exists():
             raise FileNotFoundError(f"Codebase root does not exist: {self.codebase_root}")

    def generate(self) -> List[Path]:
        logger.info("Starting knowledge base generation from {}", self.codebase_root)
        
        # Now it is safe to reset directories
        if not self.dry_run:
            self._reset_directory(self.sub_agents_root)
            self._reset_directory(self.output_root)
        
        self.output_root.mkdir(parents=True, exist_ok=True)

        # Step 1: Exploratory pass to understand codebase structure
        exploratory_path, context_summary = self._run_exploratory_pass()
        
        # Step 2: Let planner agent decide which folders to document
        targets = self._run_planner_agent(context_summary)
        if not targets:
            raise RuntimeError("Planner agent did not select any documentation targets.")
        
        logger.info("Planner selected {} targets for documentation", len(targets))

        self._initialize_plan(targets)

        results: List[AgentWorkspaceResult] = []
        skipped_count = 0
        
        for index, target in enumerate(targets):
            if self.dry_run:
                logger.info("[DRY RUN] Would spawn analyzer agent for target: {}", target.path)
                continue
            
            # CHECKPOINT: Skip if target hasn't changed
            if not self.force_rebuild and not self._should_regenerate_target(target):
                logger.info("✓ Skipping {} (up-to-date)", target.path)
                skipped_count += 1
                self._mark_task_complete(target, 0)  # Mark as complete but cached
                continue
            
            logger.info("Analyzing {} (changed or new)...", target.path)

            try:
                workspace = self._run_single_target_agent(target, context_summary)
                results.append(
                    AgentWorkspaceResult(
                        index=index,
                        target=target,
                        workspace=workspace,
                        error=None,
                    )
                )
            except Exception as exc:
                logger.exception("Analyzer failed for %s: %s", target.path, exc)
                results.append(
                    AgentWorkspaceResult(
                        index=index,
                        target=target,
                        workspace=None,
                        error=str(exc),
                    )
                )

        # Checkpoint Summary
        logger.info("=" * 60)
        logger.info("CHECKPOINT SUMMARY:")
        logger.info(f"  Analyzed: {len(results)} targets")
        logger.info(f"  Cached: {skipped_count} targets (up-to-date)")
        logger.info(f"  Total: {len(targets)} targets")
        logger.info("=" * 60)

        if self.dry_run:
            logger.info("[DRY RUN] Skipping result collection and summarization.")
            return [exploratory_path] if exploratory_path else []

        if not results and skipped_count == 0:
            raise RuntimeError("Sub-agents did not produce any workspaces.")

        output_files: List[Path] = []
        if exploratory_path:
            output_files.append(exploratory_path)

        output_files.extend(self._collect_outputs(results))

        if self.plan_path.exists():
            output_files.append(self.plan_path)

        overview_path = self._write_overview(targets, output_files)
        output_files.append(overview_path)

        toc_path = self._write_table_of_contents(output_files)
        output_files.append(toc_path)

        summary_path = self._run_summary_agent(output_files)
        if summary_path:
            output_files.append(summary_path)
            # Regenerate TOC to include summary
            toc_path = self._write_table_of_contents(output_files)
            if toc_path not in output_files:
                output_files.append(toc_path)

        logger.info("Knowledge base generated with {} files", len(output_files))
        return sorted(set(output_files), key=lambda path: path.name)

    # ----- Target discovery -------------------------------------------------

    def _run_exploratory_pass(self) -> tuple[Path | None, str]:
        logger.info("Running exploratory pass for codebase snapshot")
        report_path = self.output_root / "scouting_report.md"

        try:
            tree = self._build_directory_tree(self.codebase_root, max_depth=2)
        except Exception as exc:
            logger.warning("Failed to build directory tree: %s", exc)
            tree = "(unable to generate tree view)"

        top_level_summary = self._summarize_top_level_directories()
        readme_excerpt = self._read_file_excerpt(self.codebase_root / "README.md")
        requirements_excerpt = self._read_file_excerpt(self.codebase_root / "requirements.txt")
        if not requirements_excerpt:
             # Try pyproject.toml as fallback
             requirements_excerpt = self._read_file_excerpt(self.codebase_root / "pyproject.toml")

        lines = [
            "# Exploratory Scouting Report",
            "",
            "Generated before launching analyzer sub-agents to capture a high-level snapshot of the repository.",
            "",
            "## Top-Level Structure",
            "```markdown",
            tree.strip(),
            "```",
        ]

        if top_level_summary:
            lines.extend(["", "## First-Level Directories of `src/`", ""])
            lines.extend(f"- {entry}" for entry in top_level_summary)

        if readme_excerpt:
            lines.extend(["", "## README.md (excerpt)", "", "```markdown", readme_excerpt, "```"])

        if requirements_excerpt:
            lines.extend(["", "## Dependency Config (excerpt)", "", "```text", requirements_excerpt, "```"])

        lines.append("")
        
        if not self.dry_run:
             report_path.write_text("\n".join(lines), encoding="utf-8")
        
        # Context summary for agents
        context_summary = (
            f"Codebase Structure:\n{tree}\n\n"
            f"Top-level directories: {', '.join(top_level_summary) if top_level_summary else 'None'}\n"
        )
        if readme_excerpt:
            context_summary += f"\nREADME excerpt:\n{readme_excerpt[:500]}...\n"
            
        return report_path, context_summary
    
    def _run_planner_agent(self, context_summary: str) -> List[DocumentationTarget]:
        """Run planner agent to intelligently select documentation targets."""
        logger.info("Running planner agent to select documentation targets...")
        
        # Build planner task
        task = (
            f"{context_summary}\n\n"
            "Explore the codebase using the provided tools. Select 4-8 distinct folders/files that should be documented.\n"
            "Return ONLY a JSON array of relative paths, nothing else."
        )
        
        # Create simple planner agent (no tools needed, just decision)
        from smolagents import  LiteLLMModel, ToolCallingAgent
        from toolkits.sub_agent_toolkit import LITELLM_MODEL_ID, LITELLM_API_KEY
        from toolkits.scoped_filesystem_toolkit import build_scoped_tools
        
        # Give planner a temporary workspace for tools (even if it doesn't write)
        planner_workspace = self.sub_agents_root / "planner"
        self._reset_directory(planner_workspace)
        
        planner_tools = build_scoped_tools(
            codebase_root=str(self.codebase_root),
            workspace_root=str(planner_workspace)
        )
        # Filter out writing tools to keep it read-only
        planner_tools = [t for t in planner_tools if "write" not in t.name]
        
        model = LiteLLMModel(model_id=LITELLM_MODEL_ID, api_key=LITELLM_API_KEY)
        planner = ToolCallingAgent(
            name="documentation_planner",
            description="Selects which parts of codebase to document",
            tools=planner_tools,
            model=model,
            instructions=prompts.PLANNER_AGENT_PROMPT
        )
        
        try:
            response = planner.run(task)
            response_text = str(response)
            
            # Extract JSON array from response
            import json
            import re
            
            # Try to find JSON array in response
            json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if not json_match:
                logger.warning("Planner output has no JSON array, falling back to heuristic")
                return self._fallback_target_selection()
            
            selected_paths = json.loads(json_match.group(0))
            
            if not isinstance(selected_paths, list) or not selected_paths:
                logger.warning("Invalid planner response, using fallback")
                return self._fallback_target_selection()
            
            # Convert to DocumentationTarget objects
            targets = []
            for path_str in selected_paths:
                relative_path = Path(path_str)
                absolute_path = (self.codebase_root / relative_path).resolve()
                
                if not absolute_path.exists():
                    logger.warning(f"Planner selected non-existent path: {path_str}, skipping")
                    continue
                
                label = relative_path.name or relative_path.as_posix()
                targets.append(DocumentationTarget(path=relative_path, label=label))
            
            return targets
            
        except Exception as exc:
            logger.exception(f"Planner agent failed: {exc}")
            logger.warning("Falling back to heuristic target selection")
            return self._fallback_target_selection()
    
    def _fallback_target_selection(self) -> List[DocumentationTarget]:
        """Simple heuristic if planner fails."""
        identifiers = ["README.md", "src", "tests"]
        targets = []
        for ident in identifiers:
            rel_path = Path(ident)
            abs_path = (self.codebase_root / rel_path).resolve()
            if abs_path.exists():
                targets.append(DocumentationTarget(path=rel_path, label=rel_path.name))
        return targets

    def _discover_targets(self) -> List[DocumentationTarget]:
        identifiers = self._resolve_target_identifiers()
        
        if not identifiers:
             identifiers = self._scan_for_targets()
             logger.info("Discovered {} targets dynamically.", len(identifiers))

        targets: List[DocumentationTarget] = []
        for identifier in identifiers:
            relative_path = Path(identifier)
            # Safety check: ensure target is actually inside codebase
            try:
                absolute_path = (self.codebase_root / relative_path).resolve()
                if not str(absolute_path).startswith(str(self.codebase_root)):
                     logger.warning(f"Target {identifier} resolves outside codebase root. Skipping.")
                     continue
            except Exception:
                 continue

            if not absolute_path.exists():
                logger.info("Skipping target %s because it does not exist.", identifier)
                continue

            label = relative_path.name or relative_path.as_posix()
            targets.append(DocumentationTarget(path=relative_path, label=label))

        return targets

    def _scan_for_targets(self) -> List[str]:
        src_root = self.codebase_root / "src"
        scan_root = src_root if src_root.exists() and src_root.is_dir() else self.codebase_root

        targets = []
        # Always include README if it exists
        if (self.codebase_root / "README.md").exists():
            targets.append("README.md")
        
        # Always include explicit tests folder if present
        if (self.codebase_root / "tests").exists():
            targets.append("tests")

        for item in scan_root.iterdir():
            if item.name.startswith(".") or item.name.startswith("_"):
                continue
            if item.name in _IGNORED_SCAN_DIRS:
                continue
            
            # If scanning root, ignore miscellaneous files (e.g. .gitignore, setup.py)
            # We want to focus on Directories for sub-agents to analyze.
            if scan_root == self.codebase_root and item.is_file():
                continue

            try:
                rel_path = item.relative_to(self.codebase_root).as_posix()
                # Avoid duplicates
                if rel_path not in targets:
                    targets.append(rel_path)
            except ValueError:
                continue
            
        return sorted(targets)

    # ----- Task construction ------------------------------------------------

    def _build_task_description(self, target: DocumentationTarget, context_summary: str = "") -> str:
        relative = target.path.as_posix()
        directory_hint = (
            relative if target.path.suffix == "" else target.path.parent.as_posix()
        )
        directory_hint = directory_hint or "."

        sections = [
            "- Provide an overview of the module's responsibility.",
            "- Enumerate key entrypoints (classes, functions, routes).",
            "- Document configuration or dependencies this area relies on.",
            "- Explain control flow and interactions with other modules.",
            "- Include noteworthy code snippets (keep them concise).",
            "- Highlight extension points and related tests.",
        ]

        instructions = "\n".join(sections)
        return (
            f"Analyze the path `{relative}` within the codebase. Focus on files under `{directory_hint}`.\n"
            "Use markdown headings mirroring the required sections."
            " Save your main report as `summary.md` inside your workspace.\n"
            f"Directory hints: {directory_hint}.\n"
            f"Module label: {target.label}.\n"
            f"Global Context:\n{context_summary}\n"
            f"Checklist:\n{instructions}"
        )

    # ----- Aggregation ------------------------------------------------------

    def _collect_outputs(self, results: Sequence[AgentWorkspaceResult]) -> List[Path]:
        output_files: List[Path] = []

        for result in results:
            target = result.target
            workspace = result.workspace
            
            if not workspace or not workspace.exists():
                logger.warning(f"No workspace found for {target.path}")
                self._mark_task_attention(target, "Agent failed to create workspace")
                continue

            exported = self._export_workspace_markdown(target, workspace)

            if exported:
                output_files.extend(exported)
                self._mark_task_complete(target, len(exported))
                continue

            # Retry logic
            error_detail = result.error or "Empty output"
            logger.warning(f"Retrying {target.path} (Reason: {error_detail})")
            
            retry_workspace = self._retry_target_workspace(target)
            if retry_workspace:
                exported_retry = self._export_workspace_markdown(target, retry_workspace)
                if exported_retry:
                    output_files.extend(exported_retry)
                    self._mark_task_complete(target, len(exported_retry))
                    continue
            
            self._mark_task_attention(target, f"Failed after retry: {error_detail}")

        return output_files

    def _run_single_target_agent(self, target: DocumentationTarget, context_summary: str = "") -> Path | None:
        workspace_root = self.sub_agents_root / target.identifier
        self._reset_directory(workspace_root)

        spec = SubAgentTaskSpec(
            description=self._build_task_description(target, context_summary),
            role=SubAgentRole.ANALYZER,
        )

        workspaces = run_typed_sub_agent_tasks(
            [spec],
            codebase_root=self.codebase_root,
            sub_agents_root=workspace_root,
        )
        return workspaces[0] if workspaces else None

    def _retry_target_workspace(self, target: DocumentationTarget) -> Path | None:
        # Use a distinct directory for retries to avoid file lock issues
        retry_root = self.sub_agents_root / f"retry_{target.identifier}"
        self._reset_directory(retry_root)

        specs = [
            SubAgentTaskSpec(
                description=f"{self._build_task_description(target)}\n\nIMPORTANT: Previous attempt failed. Be extremely verbose.",
                role=SubAgentRole.ANALYZER,
            )
        ]

        workspaces = run_typed_sub_agent_tasks(
            specs,
            codebase_root=self.codebase_root,
            sub_agents_root=retry_root,
        )
        return workspaces[0] if workspaces else None

    def _write_overview(self, targets: Sequence[DocumentationTarget], output_files: Sequence[Path]) -> Path:
        overview_path = self.output_root / "overview.md"
        lines = [
            "# Codebase Overview",
            "",
            "This knowledge base was generated automatically.",
            "",
            "## Covered Areas"
        ]
        for target in targets:
            lines.append(f"- `{target.path.as_posix()}`")
        
        lines.append("")
        if output_files:
            lines.append("## Artifact Index")
            for path in sorted(output_files, key=lambda p: p.name):
                lines.append(f"- [{path.name}]({path.name})")
                
        overview_path.write_text("\n".join(lines), encoding="utf-8")
        return overview_path

    def _write_table_of_contents(self, output_files: Sequence[Path]) -> Path:
        toc_path = self.output_root / "toc.md"
        lines = ["# Knowledge Base Table of Contents", ""]
        for file_path in sorted(output_files, key=lambda p: p.name):
            if file_path.name == "toc.md":
                continue
            lines.append(f"- [{file_path.stem}]({file_path.name})")
        toc_path.write_text("\n".join(lines), encoding="utf-8")
        return toc_path

    def _export_workspace_markdown(self, target: DocumentationTarget, workspace: Path) -> List[Path]:
        markdown_files = sorted(workspace.rglob("*.md"))
        if not markdown_files:
            return []

        exported: List[Path] = []
        for index, file_path in enumerate(markdown_files):
            content = file_path.read_text(encoding="utf-8")
            if not self._has_meaningful_content(content):
                continue

            # Rename file to match target identifier to prevent collisions
            suffix = f"_{index}" if index > 0 else ""
            clean_identifier = target.identifier
            if clean_identifier.endswith(".md"): 
                 clean_identifier = clean_identifier[:-3]
                 
            output_name = f"{clean_identifier}{suffix}.md"
            output_path = self.output_root / output_name
            
            try:
                output_path.write_text(content, encoding="utf-8")
                exported.append(output_path)
            except Exception as e:
                logger.error(f"Failed to export {output_name}: {e}")

        return exported

    # ... [Keep existing summary agent logic, plan init, marking tasks logic] ...

    def _run_summary_agent(self, artifact_paths: Sequence[Path]) -> Path | None:
        if not artifact_paths: return None
        summary_root = self.sub_agents_root / "summary_agent"
        self._reset_directory(summary_root)

        workspaces = run_typed_sub_agent_tasks(
            [SubAgentTaskSpec(description=self._build_summary_task_description(artifact_paths), role=SubAgentRole.SUMMARIZER)],
            codebase_root=self.output_root,
            sub_agents_root=summary_root,
        )
        if not workspaces: return None
        
        # Check for summary.md
        src = workspaces[0] / "summary.md"
        if src.exists():
            dest = self.output_root / "executive_summary.md"
            dest.write_text(src.read_text("utf-8"), "utf-8")
            return dest
        return None

    def _build_summary_task_description(self, artifact_paths: Sequence[Path]) -> str:
        files = "\n".join(f"- {p.name}" for p in artifact_paths)
        return f"Summarize these Knowledge Base files into an executive_summary.md:\n{files}"

    # ... [Helper methods kept mostly as is, just ensuring types] ...
    
    def _initialize_plan(self, targets: Sequence[DocumentationTarget]) -> None:
        self._plan_state = {
            t.identifier: {"path": t.path.as_posix(), "label": t.label, "status": " ", "note": ""}
            for t in targets
        }
        self._write_plan_file()

    def _mark_task_complete(self, target: DocumentationTarget, count: int) -> None:
        if target.identifier in self._plan_state:
            self._plan_state[target.identifier].update({"status": "x", "note": f"Files: {count}"})
            self._write_plan_file()

    def _mark_task_attention(self, target: DocumentationTarget, note: str) -> None:
        if target.identifier in self._plan_state:
            self._plan_state[target.identifier].update({"status": "!", "note": note})
            self._write_plan_file()

    def _write_plan_file(self) -> None:
        lines = ["# Knowledge Base Plan", ""]
        for k, v in self._plan_state.items():
            lines.append(f"- [{v['status']}] {v['path']} ({v['note']})")
        self.plan_path.write_text("\n".join(lines), "utf-8")

    @staticmethod
    def _reset_directory(path: Path) -> None:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _has_meaningful_content(content: str) -> bool:
        return len(content.strip()) > 50 # Simple heuristic

    def _build_directory_tree(self, root: Path, max_depth: int = 2) -> str:
        tree_lines = []
        
        def _add_to_tree(path: Path, current_depth: int, prefix: str = ""):
            if current_depth > max_depth:
                return
            
            try:
                items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except PermissionError:
                return

            items = [i for i in items if not i.name.startswith(".") and i.name not in ["__pycache__", "node_modules", "venv", "env"]]
            
            for index, item in enumerate(items):
                is_last = index == len(items) - 1
                connector = "└── " if is_last else "├── "
                
                tree_lines.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
                
                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    _add_to_tree(item, current_depth + 1, prefix + extension)

        tree_lines.append(f"{root.name}/")
        _add_to_tree(root, 1)
        return "\n".join(tree_lines)

    def _summarize_top_level_directories(self) -> List[str]:
        try:
            return [p.name for p in self.codebase_root.iterdir() if p.is_dir() and not p.name.startswith(".")]
        except Exception:
            return []

    def _read_file_excerpt(self, path: Path, max_chars: int = 2000) -> str | None:
        if path.exists():
            return path.read_text("utf-8")[:max_chars]
        return None
    
    def _should_regenerate_target(self, target: DocumentationTarget) -> bool:
        """
        Check if target needs regeneration based on source file modification times.
        Returns True if:
          - Output file doesn't exist
          - Any source file is newer than the output
          - Output file is empty/corrupted
        """
        # Determine output file path
        base_name = target.identifier
        if base_name.endswith(".md"):
            base_name = base_name[:-3]
        output_file = self.output_root / f"{base_name}.md"
        
        # If output doesn't exist, regenerate
        if not output_file.exists():
            logger.debug(f"  → {target.path}: No existing output")
            return True
        
        # If output is empty or corrupted, regenerate
        try:
            content = output_file.read_text("utf-8")
            if len(content.strip()) < 50:
                logger.debug(f"  → {target.path}: Output too small ({len(content)} bytes)")
                return True
        except Exception:
            logger.debug(f"  → {target.path}: Cannot read output")
            return True
        
        # Get output modification time
        try:
            output_mtime = output_file.stat().st_mtime
        except OSError:
            return True
        
        # Check source files
        source_path = self.codebase_root / target.path
        
        if not source_path.exists():
            logger.debug(f"  → {target.path}: Source no longer exists")
            return False  # Don't regenerate if source is gone
        
        # For single files
        if source_path.is_file():
            try:
                source_mtime = source_path.stat().st_mtime
                if source_mtime > output_mtime:
                    logger.debug(f"  → {target.path}: Source file modified")
                    return True
            except OSError:
                return True
            return False
        
        # For directories, check all Python/config files
        if source_path.is_dir():
            for file in source_path.rglob("*"):
                # Skip non-relevant files
                if file.is_dir():
                    continue
                if file.name.startswith("."):
                    continue
                if any(part in _IGNORED_SCAN_DIRS for part in file.parts):
                    continue
                
                # Check modification time
                try:
                    if file.stat().st_mtime > output_mtime:
                        logger.debug(f"  → {target.path}: File {file.name} modified")
                        return True
                except OSError:
                    continue
        
        logger.debug(f"  → {target.path}: Up-to-date")
        return False


__all__ = ["KnowledgeBaseBuilder"]