"""Build the knowledge base for a codebase using sub-agents."""
from __future__ import annotations
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Sequence
from dotenv import load_dotenv
from loguru import logger
from smolagents import ToolCallingAgent
from prompts import prompts
from utils.path_utils import ensure_directory
from config import settings
from pipelines.types import DocumentationTarget
from pipelines.checkpoint import CheckpointedPipelineRunner

__all__ = ["KnowledgeBaseBuilder"]

load_dotenv()

class KnowledgeBaseBuilder:
    def __init__(
        self,
        codebase_root: str | Path | None = None,
        output_root: str | Path | None = None,
        sub_agents_root: str | Path | None = None,
        dry_run: bool = False,
        force_rebuild: bool = False,
        step_delay_seconds: float | None = None,
        max_targets: int | None = None,
    ):
        self.codebase_root = Path(codebase_root).expanduser().resolve() if codebase_root else settings.CODEBASE_ROOT
        self.output_root = ensure_directory(Path(output_root).expanduser().resolve() if output_root else settings.KNOWLEDGE_BASE_OUTPUT)
        self.sub_agents_root = ensure_directory(Path(sub_agents_root).expanduser().resolve() if sub_agents_root else settings.SUB_AGENTS_ROOT)
        self.dry_run = dry_run
        self.force_rebuild = force_rebuild
        self.checkpoint = CheckpointedPipelineRunner(
            output_root=self.output_root,
            codebase_name=self.codebase_root.name,
            force_rebuild=force_rebuild
        )
        self.plan_path = self.output_root / "plan.md"

    def generate(self) -> List[Path]:
        """Generate knowledge base (delegates to supervisor)."""
        logger.info("Starting knowledge base generation via Supervisor...")
        return self.generate_with_supervisor()

    def generate_with_supervisor(self) -> List[Path]:
        """Generate knowledge base using the Supervisor Agent."""
        if self.checkpoint.checkpoint.phase == "kb_completed" and not self.force_rebuild:
            logger.info("Knowledge Base phase marked complete in checkpoint. returning existing files.")
            return sorted(list(self.output_root.glob("*.md")), key=lambda p: p.name)

        if self.force_rebuild and not self.dry_run:
            self._reset_directory(self.sub_agents_root)
            self._reset_directory(self.output_root)
            self._clear_rag_vector_store()
            self.checkpoint = CheckpointedPipelineRunner(
                output_root=self.output_root,
                codebase_name=self.codebase_root.name,
                force_rebuild=True
            )
        
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.sub_agents_root.mkdir(parents=True, exist_ok=True)
        
        if self.dry_run:
            logger.debug("[DRY RUN] Would run Supervisor Agent")
            return []
            
        self.checkpoint.set_phase("kb_generation")
        supervisor = self._create_supervisor_agent()
        
        base_task = prompts.KB_SUPERVISOR_TASK_TEMPLATE.format(codebase_root=self.codebase_root)
        completed_targets = self.checkpoint.checkpoint.kb_completed_targets
        if completed_targets:
             base_task += "\\n\\nPREVIOUSLY COMPLETED TARGETS (Skip these):"
             for t in completed_targets:
                 base_task += f"\\n- {t}"
        
        max_retries = 10
        retry_delay = 5.0
        
        for attempt in range(1, max_retries + 1):
            try:
                self.checkpoint.mark_kb_target_complete("processing_attempt")
                logger.info("Supervisor Task: Starting attempt {}/{}", attempt, max_retries)
                result = supervisor.run(base_task, max_steps=50)
                logger.info("Supervisor Agent completed: {}", str(result)[:200])
                break
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = "rate" in error_str or "429" in error_str or "quota" in error_str
                if is_rate_limit and attempt < max_retries:
                    logger.warning(f"Rate limit hit. Waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    logger.warning(f"Supervisor attempt failed: {e}")
                    break
        
        output_files = list(self.output_root.glob("*.md"))
        if not output_files:
            logger.info("No files in output_root, collecting from sub_agents_root...")
            self._collect_from_sub_agents()
            output_files = list(self.output_root.glob("*.md"))
        
        if output_files:
            summary_path = self._run_summary_agent(output_files)
            if summary_path:
                output_files.append(summary_path)
            self.checkpoint.set_phase("kb_completed")
        
        logger.info("Knowledge base generated with {} files", len(output_files))
        return sorted(output_files, key=lambda p: p.name)

    def _collect_from_sub_agents(self) -> int:
        collected = 0
        for workspace in self.sub_agents_root.rglob("sub_agent_*"):
            if not workspace.is_dir(): continue
            target_name = workspace.parent.name
            if target_name in ("sub_agents_kb", "sub_agents_workspace"): target_name = "unknown"
            for md_file in workspace.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if len(content.strip()) < 50: continue
                    out_name = f"{target_name}.md"
                    out_path = self.output_root / out_name
                    counter = 1
                    while out_path.exists():
                        out_name = f"{target_name}_{counter}.md"
                        out_path = self.output_root / out_name
                        counter += 1
                    out_path.write_text(content, encoding="utf-8")
                    collected += 1
                    logger.info(f"Collected {md_file.name} -> {out_name}")
                except Exception as e:
                    logger.warning(f"Failed to collect {md_file}: {e}")
        logger.info(f"Collected {collected} files from sub-agent workspaces")
        return collected

    def _create_supervisor_agent(self):
        from toolkits.supervisor_toolkit import build_supervisor_tools
        from utils.llm_factory import create_model
        tools = build_supervisor_tools(
            codebase_root=str(self.codebase_root),
            sub_agents_root=str(self.sub_agents_root),
            output_root=str(self.output_root),
        )
        model = create_model(role="supervisor")
        return ToolCallingAgent(
            name="knowledge_base_supervisor",
            description="Supervises and coordinates knowledge base generation",
            tools=tools,
            model=model,
            instructions=prompts.SUPERVISOR_AGENT_PROMPT,
        )

    def _run_summary_agent(self, files: List[Path]) -> Path | None:
        summary_path = self.output_root / "executive_summary.md"
        if not files:
            summary_path.write_text("# Executive Summary\\n\\nNo documentation files generated.", encoding="utf-8")
            return summary_path
        
        file_summaries = []
        for f in files:
            if f.exists() and f.suffix == ".md" and f.name != "executive_summary.md":
                try:
                    text = f.read_text(encoding="utf-8")
                    snippet = text[:500].strip() + ("..." if len(text) > 500 else "")
                    file_summaries.append(f"### {f.stem}\\n{snippet}\\n")
                except Exception: pass
        
        content = f"# Executive Summary\\n\\nDocumentation for **{self.codebase_root.name}**.\\n\\n## Files\\n\\n"
        content += "\\n".join(file_summaries) if file_summaries else "No files."
        content += f"\\n\\n*Generated from {len(files)} files.*"
        
        summary_path.write_text(content, encoding="utf-8")
        return summary_path

    def _reset_directory(self, path: Path):
        if path.exists(): shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    def _clear_rag_vector_store(self):
        pass
