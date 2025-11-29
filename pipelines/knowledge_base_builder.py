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
from utils.path_utils import ensure_directory

load_dotenv()

CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
KNOWLEDGE_BASE_OUTPUT_PATH = os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
SUB_AGENTS_ROOT_PATH = os.getenv("SUB_AGENTS_ROOT_PATH")
TARGET_WHITELIST_ENV = "KNOWLEDGE_BASE_TARGET_WHITELIST"
DEFAULT_TARGET_IDENTIFIERS: tuple[str, ...] = (
    "README.md",
    "src/api",
    "src/config",
    "src/models",
    "src/utils",
    "tests",
)


@dataclass(frozen=True)
class DocumentationTarget:
    path: Path
    label: str

    @property
    def identifier(self) -> str:
        safe = str(self.path).replace("/", "_")
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
    ):
        env_codebase = codebase_root or os.getenv("CODEBASE_ROOT_PATH")
        env_output = output_root or os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
        env_sub_agents = sub_agents_root or os.getenv("SUB_AGENTS_ROOT_PATH")

        self.dry_run = dry_run

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

    def generate(self) -> List[Path]:
        logger.info("Starting knowledge base generation from {}", self.codebase_root)

        self._reset_directory(self.sub_agents_root)
        self._reset_directory(self.output_root)

        self._reset_directory(self.output_root)

        exploratory_path, context_summary = self._run_exploratory_pass()

        targets = self._discover_targets()
        if not targets:
            raise RuntimeError("No documentation targets found in the codebase.")

        self._initialize_plan(targets)

        results: List[AgentWorkspaceResult] = []
        results: List[AgentWorkspaceResult] = []
        for index, target in enumerate(targets):
            if self.dry_run:
                logger.info("[DRY RUN] Would spawn analyzer agent for target: {}", target.path)
                # In dry run, we don't spawn agents.
                continue

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
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Analyzer failed for %s: %s", target.path, exc)
                results.append(
                    AgentWorkspaceResult(
                        index=index,
                        target=target,
                        workspace=None,
                        error=str(exc),
                    )
                )

        if self.dry_run:
            logger.info("[DRY RUN] Skipping result collection and summarization.")
            output_files: List[Path] = []
            if exploratory_path:
                output_files.append(exploratory_path)
            return output_files

        if not results:
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
            # Regenerate the table of contents so the summary is included.
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
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to build directory tree: %s", exc)
            tree = "(unable to generate tree view)"

        top_level_summary = self._summarize_top_level_directories()
        readme_excerpt = self._read_file_excerpt(self.codebase_root / "README.md")
        requirements_excerpt = self._read_file_excerpt(
            self.codebase_root / "requirements.txt"
        )

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
            lines.extend(
                [
                    "",
                    "## README.md (excerpt)",
                    "",
                    "```markdown",
                    readme_excerpt,
                    "```",
                ]
            )

        if requirements_excerpt:
            lines.extend(
                [
                    "",
                    "## requirements.txt (excerpt)",
                    "",
                    "```text",
                    requirements_excerpt,
                    "```",
                ]
            )

        lines.append("")

        report_path.write_text("\n".join(lines), encoding="utf-8")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        
        # Create a concise summary for context injection
        context_summary = (
            f"Codebase Structure:\n{tree}\n\n"
            f"Top-level directories: {', '.join(top_level_summary) if top_level_summary else 'None'}\n"
        )
        if readme_excerpt:
            context_summary += f"\nREADME excerpt:\n{readme_excerpt[:500]}...\n"
            
        return report_path, context_summary

    def _discover_targets(self) -> List[DocumentationTarget]:
        identifiers = self._resolve_target_identifiers()
        
        # If no identifiers returned (meaning no whitelist and defaults were skipped/empty),
        # perform dynamic discovery.
        if not identifiers:
             identifiers = self._scan_for_targets()
             logger.info("Discovered {} targets dynamically.", len(identifiers))

        targets: List[DocumentationTarget] = []

        for identifier in identifiers:
            relative_path = Path(identifier)
            absolute_path = self.codebase_root / relative_path
            if not absolute_path.exists():
                logger.info(
                    "Skipping knowledge-base target %s because it does not exist.",
                    identifier,
                )
                continue

            label = relative_path.name or relative_path.as_posix()
            targets.append(DocumentationTarget(path=relative_path, label=label))

        return targets

    def _scan_for_targets(self) -> List[str]:
        src_root = self.codebase_root / "src"
        if not src_root.exists():
            # Fallback to scanning root if src doesn't exist
            scan_root = self.codebase_root
        else:
            scan_root = src_root

        targets = []
        # Always include README if it exists
        if (self.codebase_root / "README.md").exists():
            targets.append("README.md")

        for item in scan_root.iterdir():
            if item.is_dir():
                if item.name.startswith(".") or item.name.startswith("_"):
                    continue
                if item.name in {"node_modules", "venv", "env", "tests", "docs", "site-packages"}:
                    continue
                
                # Use relative path from codebase root
                try:
                    rel_path = item.relative_to(self.codebase_root).as_posix()
                    targets.append(rel_path)
                except ValueError:
                    continue
        
        # Explicitly add tests if it exists at root
        if (self.codebase_root / "tests").exists():
            targets.append("tests")
            
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

    def _collect_outputs(
        self,
        results: Sequence[AgentWorkspaceResult],
    ) -> List[Path]:
        output_files: List[Path] = []

        for result in results:
            target = result.target
            workspace = (
                result.workspace
                if result.workspace and result.workspace.exists()
                else None
            )

            exported: List[Path] = []
            if workspace is not None:
                exported = self._export_workspace_markdown(target, workspace)

            if exported:
                output_files.extend(exported)
                self._mark_task_complete(target, len(exported))
                continue

            error_detail = result.error or "Markdown outputs were empty or missing."
            logger.warning(
                "%s produced no usable markdown; retrying with reinforced instructions | detail=%s",
                target.path,
                error_detail,
            )
            retry_workspace = self._retry_target_workspace(target)
            if retry_workspace is None:
                self._mark_task_attention(
                    target,
                    f"Retry failed to produce markdown. {error_detail}",
                )
                continue

            exported_retry = self._export_workspace_markdown(target, retry_workspace)
            if exported_retry:
                output_files.extend(exported_retry)
                self._mark_task_complete(target, len(exported_retry))
            else:
                self._mark_task_attention(
                    target,
                    f"Markdown outputs were empty even after retry. {error_detail}",
                )

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

        if not workspaces:
            logger.warning(
                "Analyzer agent for %s did not produce a workspace.", target.path
            )
            return None

        return workspaces[0]

    def _write_overview(
        self, targets: Sequence[DocumentationTarget], output_files: Sequence[Path]
    ) -> Path:
        overview_path = self.output_root / "overview.md"
        lines = [
            "# Codebase Overview",
            "",
            "This knowledge base was generated automatically.",
            "",
        ]
        lines.append("## Covered Areas")
        for target in targets:
            lines.append(f"- `{target.path.as_posix()}` → `{target.identifier}.md`")
        lines.append("")
        if output_files:
            lines.append("## Artifact Index")
            for path in output_files:
                lines.append(f"- `{path.name}`")
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

    def _export_workspace_markdown(
        self, target: DocumentationTarget, workspace: Path
    ) -> List[Path]:
        markdown_files = sorted(workspace.rglob("*.md"))
        if not markdown_files:
            return []

        exported: List[Path] = []
        for index, file_path in enumerate(markdown_files):
            content = file_path.read_text(encoding="utf-8")
            if not self._has_meaningful_content(content):
                logger.warning(
                    "Discarding empty markdown output for %s from %s",
                    target.path,
                    file_path,
                )
                continue

            suffix = f"_{index}" if index else ""
            base_name = target.identifier
            if base_name.lower().endswith(".md"):
                base_name = base_name[:-3]
            output_name = f"{base_name}{suffix}.md"
            output_path = self.output_root / output_name
            output_path.write_text(content, encoding="utf-8")
            exported.append(output_path)

        return exported

    def _retry_target_workspace(self, target: DocumentationTarget) -> Path | None:
        retry_root = self.sub_agents_root / f"retry_{target.identifier}"
        self._reset_directory(retry_root)

        augmented_description = (
            f"{self._build_task_description(target)}\n\n"
            "Previous attempt produced empty or placeholder output. "
            "Regenerate the summary with concrete analysis: provide detailed paragraphs, "
            "specific file references, and actionable insights under every required heading. "
            "If information is limited, explicitly describe the limitations instead of leaving sections blank."
        )

        specs = [
            SubAgentTaskSpec(
                description=augmented_description,
                role=SubAgentRole.ANALYZER,
            )
        ]

        workspaces = run_typed_sub_agent_tasks(
            specs,
            codebase_root=self.codebase_root,
            sub_agents_root=retry_root,
        )

        if not workspaces:
            logger.warning(
                "Retry sub-agent for %s did not yield any workspace.", target.path
            )
            return None

        return workspaces[0]

    def _run_summary_agent(self, artifact_paths: Sequence[Path]) -> Path | None:
        if not artifact_paths:
            logger.warning("Skipping summarizer agent because there are no artifacts.")
            return None

        summary_root = self.sub_agents_root / "summary_agent"
        self._reset_directory(summary_root)

        description = self._build_summary_task_description(artifact_paths)
        summary_spec = SubAgentTaskSpec(
            description=description, role=SubAgentRole.SUMMARIZER
        )
        workspaces = run_typed_sub_agent_tasks(
            [summary_spec],
            codebase_root=self.output_root,
            sub_agents_root=summary_root,
        )

        if not workspaces:
            logger.warning("Summarizer agent did not produce a workspace.")
            return None

        workspace = workspaces[0]
        summary_file = workspace / "summary.md"
        if not summary_file.exists():
            logger.warning(
                "Summarizer agent workspace at {} is missing summary.md.", workspace
            )
            return None

        destination = self.output_root / "executive_summary.md"
        content = summary_file.read_text(encoding="utf-8")
        destination.write_text(content, encoding="utf-8")

        logger.info("Summarizer agent produced {}", destination)
        return destination

    def _build_summary_task_description(self, artifact_paths: Sequence[Path]) -> str:
        relative_paths: List[str] = []
        for path in artifact_paths:
            try:
                relative_paths.append(path.relative_to(self.output_root).as_posix())
            except ValueError:
                relative_paths.append(path.name)
        artifact_listing = "\n".join(f"- {name}" for name in sorted(relative_paths))

        return (
            "You are preparing the final executive summary for the completed knowledge base.\n"
            "Review the following markdown artifacts located in the knowledge base directory:\n"
            f"{artifact_listing}\n\n"
            "Identify the most important takeaways, diagrams, risks, and recommended actions."
        )

    def _initialize_plan(self, targets: Sequence[DocumentationTarget]) -> None:
        self._plan_state.clear()
        for target in targets:
            self._plan_state[target.identifier] = {
                "path": target.path.as_posix(),
                "label": target.label,
                "status": " ",
                "note": "",
            }
        self._write_plan_file()

    def _mark_task_complete(self, target: DocumentationTarget, artifacts: int) -> None:
        entry = self._plan_state.get(target.identifier)
        if not entry:
            return
        entry["status"] = "x"
        entry["note"] = f"Completed with {artifacts} artifact(s)."
        self._write_plan_file()

    def _mark_task_attention(self, target: DocumentationTarget, note: str) -> None:
        entry = self._plan_state.get(target.identifier)
        if not entry:
            return
        entry["status"] = "!"
        entry["note"] = note
        self._write_plan_file()

    def _write_plan_file(self) -> None:
        lines = [
            "# Knowledge Base TODO",
            "",
            "Checklist maintained automatically while building the knowledge base.",
            "Legend: [ ] pending / [x] completed / [!] needs follow-up.",
            "",
        ]

        for identifier, data in self._plan_state.items():
            description = data["path"] or "."
            label = data["label"]
            if label and label != description:
                description = f"{description} ({label})"
            note = f" — {data['note']}" if data.get("note") else ""
            lines.append(f"- [{data['status']}] `{identifier}` — {description}{note}")

        self.plan_path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _reset_directory(path: Path) -> None:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            return
        for entry in path.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()

    @staticmethod
    def _has_meaningful_content(content: str) -> bool:
        stripped = content.strip()
        if not stripped:
            return False
        non_empty_lines = [line for line in stripped.splitlines() if line.strip()]
        if len(non_empty_lines) <= 1:
            return False
        if all(line.startswith("#") for line in non_empty_lines):
            return False
        return True

    @staticmethod
    def _resolve_target_identifiers() -> List[str]:
        env_value = os.getenv(TARGET_WHITELIST_ENV)
        if env_value:
            configured = [part.strip() for part in env_value.split(",") if part.strip()]
            if configured:
                logger.info(
                    "Using knowledge base target whitelist from %s with %d entries",
                    TARGET_WHITELIST_ENV,
                    len(configured),
                )
                return configured
        
        # Return empty list to signal dynamic discovery should be used
        return []

    def _build_directory_tree(self, root: Path, max_depth: int = 2) -> str:
        def tree(directory: Path, prefix: str = "", depth: int = 0) -> List[str]:
            if depth > max_depth:
                return []
            entries = sorted(
                child
                for child in directory.iterdir()
                if not child.name.startswith(".") and child.name != "__pycache__"
            )
            lines: List[str] = []
            for index, entry in enumerate(entries):
                connector = "└── " if index == len(entries) - 1 else "├── "
                child_prefix = "    " if index == len(entries) - 1 else "│   "
                label = entry.name + ("/" if entry.is_dir() else "")
                lines.append(f"{prefix}{connector}{label}")
                if entry.is_dir():
                    lines.extend(tree(entry, prefix + child_prefix, depth=depth + 1))
            return lines

        lines = ["."] + tree(root)
        return "\n".join(lines)

    def _summarize_top_level_directories(self) -> List[str]:
        src_root = self.codebase_root / "src"
        if not src_root.exists() or not src_root.is_dir():
            return []
        entries = []
        for child in sorted(src_root.iterdir()):
            if child.name.startswith(".") or child.name == "__pycache__":
                continue
            label = child.name + ("/" if child.is_dir() else "")
            entries.append(label)
        return entries

    @staticmethod
    def _read_file_excerpt(path: Path, max_chars: int = 2000) -> str | None:
        if not path.exists() or not path.is_file():
            return None
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):  # pragma: no cover - defensive logging
            return None
        snippet = content.strip()
        if len(snippet) > max_chars:
            snippet = snippet[: max_chars - 3].rstrip() + "..."
        return snippet


__all__ = ["KnowledgeBaseBuilder"]
