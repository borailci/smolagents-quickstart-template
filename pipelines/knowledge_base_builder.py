"""Build the knowledge base for a codebase using sub-agents."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, cast

from dotenv import load_dotenv
from loguru import logger

from toolkits.sub_agent_toolkit import run_sub_agent_tasks
from utils.path_utils import ensure_directory

load_dotenv()

CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
KNOWLEDGE_BASE_OUTPUT_PATH = os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
SUB_AGENTS_ROOT_PATH = os.getenv("SUB_AGENTS_ROOT_PATH")


@dataclass(frozen=True)
class DocumentationTarget:
    path: Path
    label: str

    @property
    def identifier(self) -> str:
        safe = str(self.path).replace("/", "_")
        return safe if safe else "root"


class KnowledgeBaseBuilder:
    def __init__(
        self,
        codebase_root: str | Path | None = None,
        output_root: str | Path | None = None,
        sub_agents_root: str | Path | None = None,
    ):
        if not (codebase_root or CODEBASE_ROOT_PATH):
            raise RuntimeError("CODEBASE_ROOT_PATH is not configured.")
        if not (output_root or KNOWLEDGE_BASE_OUTPUT_PATH):
            raise RuntimeError("KNOWLEDGE_BASE_OUTPUT_PATH is not configured.")
        if not (sub_agents_root or SUB_AGENTS_ROOT_PATH):
            raise RuntimeError("SUB_AGENTS_ROOT_PATH is not configured.")

        root_value = cast(str | Path, codebase_root or CODEBASE_ROOT_PATH)
        output_value = cast(str | Path, output_root or KNOWLEDGE_BASE_OUTPUT_PATH)
        sub_agents_value = cast(str | Path, sub_agents_root or SUB_AGENTS_ROOT_PATH)

        self.codebase_root = Path(root_value).expanduser().resolve()
        self.output_root = ensure_directory(output_value)
        self.sub_agents_root = ensure_directory(sub_agents_value)

    def generate(self) -> List[Path]:
        logger.info("Starting knowledge base generation from %s", self.codebase_root)

        self._reset_directory(self.sub_agents_root)
        self._reset_directory(self.output_root)

        targets = self._discover_targets()
        if not targets:
            raise RuntimeError("No documentation targets found in the codebase.")

        task_descriptions = [self._build_task_description(target) for target in targets]
        workspaces = run_sub_agent_tasks(
            task_descriptions,
            codebase_root=self.codebase_root,
            sub_agents_root=self.sub_agents_root,
        )

        if not workspaces:
            raise RuntimeError("Sub-agents did not produce any workspaces.")

        output_files = self._collect_outputs(targets, workspaces)
        self._write_overview(targets, output_files)
        self._write_table_of_contents(output_files)

        logger.info("Knowledge base generated with %s files", len(output_files) + 2)
        return output_files

    # ----- Target discovery -------------------------------------------------

    def _discover_targets(self) -> List[DocumentationTarget]:
        src_dir = self.codebase_root / "src"
        targets: List[DocumentationTarget] = []

        if src_dir.is_dir():
            targets.extend(self._targets_from_directory(src_dir, prefix="src"))
        else:
            targets.extend(self._targets_from_directory(self.codebase_root))

        # Prioritise important top-level files if they exist
        special_files = ["README.md", "pyproject.toml", "requirements.txt"]
        for name in special_files:
            file_path = self.codebase_root / name
            if file_path.exists():
                targets.insert(0, DocumentationTarget(path=Path(name), label=name))

        # Include tests directory if present and not already included
        tests_path = Path("tests")
        if (self.codebase_root / tests_path).is_dir():
            targets.append(DocumentationTarget(path=tests_path, label="tests"))

        # Deduplicate while preserving order
        seen = set()
        unique_targets: List[DocumentationTarget] = []
        for target in targets:
            key = target.path.as_posix()
            if key not in seen:
                seen.add(key)
                unique_targets.append(target)

        return unique_targets

    def _targets_from_directory(
        self, directory: Path, prefix: str | None = None
    ) -> List[DocumentationTarget]:
        base = []
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith("."):
                continue
            relative = entry.relative_to(self.codebase_root)
            if prefix and not str(relative).startswith(f"{prefix}/"):
                relative = Path(prefix) / entry.relative_to(directory)

            if entry.is_dir():
                base.append(DocumentationTarget(path=relative, label=relative.name))
            elif entry.suffix in {".py", ".md", ".json", ".yaml", ".yml"}:
                base.append(DocumentationTarget(path=relative, label=relative.name))
        return base

    # ----- Task construction ------------------------------------------------

    def _build_task_description(self, target: DocumentationTarget) -> str:
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
            f"Checklist:\n{instructions}"
        )

    # ----- Aggregation ------------------------------------------------------

    def _collect_outputs(
        self,
        targets: Sequence[DocumentationTarget],
        workspaces: Sequence[Path],
    ) -> List[Path]:
        output_files: List[Path] = []

        for target, workspace in zip(targets, workspaces):
            markdown_files = sorted(workspace.rglob("*.md"))
            if not markdown_files:
                logger.warning("No markdown outputs found for %s", target.path)
                continue

            for index, file_path in enumerate(markdown_files):
                content = file_path.read_text(encoding="utf-8")
                suffix = f"_{index}" if index else ""
                output_name = f"{target.identifier}{suffix}.md"
                output_path = self.output_root / output_name
                output_path.write_text(content, encoding="utf-8")
                output_files.append(output_path)

        return output_files

    def _write_overview(
        self, targets: Sequence[DocumentationTarget], output_files: Sequence[Path]
    ) -> None:
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

    def _write_table_of_contents(self, output_files: Sequence[Path]) -> None:
        toc_path = self.output_root / "toc.md"
        lines = ["# Knowledge Base Table of Contents", ""]
        for file_path in sorted(output_files, key=lambda p: p.name):
            lines.append(f"- [{file_path.stem}]({file_path.name})")
        toc_path.write_text("\n".join(lines), encoding="utf-8")

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


__all__ = ["KnowledgeBaseBuilder"]
