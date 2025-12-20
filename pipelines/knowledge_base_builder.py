"""Build the knowledge base for a codebase using sub-agents."""
from __future__ import annotations
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence
from dotenv import load_dotenv
from loguru import logger
from smolagents import ToolCallingAgent
from prompts import prompts
from config import settings

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
        self.output_root = Path(output_root).expanduser().resolve() if output_root else settings.KNOWLEDGE_BASE_OUTPUT
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.sub_agents_root = Path(sub_agents_root).expanduser().resolve() if sub_agents_root else settings.SUB_AGENTS_ROOT
        self.sub_agents_root.mkdir(parents=True, exist_ok=True)
        self.dry_run = dry_run
        self.force_rebuild = force_rebuild
        self.plan_path = self.output_root / "plan.md"

    def generate(self, metrics: Any = None) -> List[Path]:
        """Generate knowledge base using supervisor agent."""
        logger.info("Starting knowledge base generation...")
        
        results = self.generate_with_supervisor(metrics=metrics)
        if not results and not self.dry_run:
            raise RuntimeError("Supervisor agent failed to generate any knowledge base files. Check the logs for details.")
        return results

    def generate_with_simple_heuristic(self, metrics: Any = None) -> List[Path]:
        """
        Fallback method: Deterministic generation.
        Spawns one sub-agent for every first-level directory in src/ (or root).
        """
        logger.info("Running Simple Heuristic Generation...")
        
        if self.force_rebuild and not self.dry_run:
            self._reset_directory(self.sub_agents_root)
            self._reset_directory(self.output_root)
        
        # 1. Identify Targets
        src_path = self.codebase_root / "src"
        if not src_path.exists():
            src_path = self.codebase_root
            
        targets = []
        for item in src_path.iterdir():
            if item.is_dir() and not item.name.startswith(".") and item.name not in ("__pycache__", "tests", "docs", "node_modules"):
                targets.append(item)
                
        if not targets:
            logger.warning("No directories found to analyze.")
            return []
            
        logger.info(f"Identified {len(targets)} targets: {[t.name for t in targets]}")
        
        if self.dry_run:
            return []

        # 2. Spawn Sub-Agents
        from toolkits.sub_agent_toolkit import run_typed_sub_agent_tasks, SubAgentTaskSpec, SubAgentRole
        from prompts import prompts
        
        tasks = []
        for target in targets:
            # Create a task spec for each directory
            # We use the generic analyzer template but adapted for direct use
            
            # Simple heuristic: Use the directory name as the target path
            rel_path = target.relative_to(self.codebase_root)
            
            # Construct the task description
            # We use the ANALYZER logical Prompt (SUB_AGENT_KB_PROMPT) + a specific instruction
            task_desc = f"Analyze the directory '{rel_path}'. Document its purpose, key components, and data flow. Save as 'summary.md'."
            
            spec = SubAgentTaskSpec(
                description=task_desc,
                role=SubAgentRole.ANALYZER,
                instructions=prompts.SUB_AGENT_KB_PROMPT
            )
            tasks.append(spec)
            
        # Run them
        workspaces = run_typed_sub_agent_tasks(
            tasks,
            codebase_root=self.codebase_root,
            sub_agents_root=self.sub_agents_root,
            min_interval_seconds=2.0, # Slightly faster for heuristic
            metrics=metrics,
        )
        
        # 3. Collect & Finalize
        self._collect_from_sub_agents()
        
        output_files = list(self.output_root.glob("*.md"))
        if output_files:
            summary_path = self._run_summary_agent(output_files)
            if summary_path:
                output_files.append(summary_path)
            
            # Validator removed (Step 1336)
            # if not self.dry_run:
            #     self._run_validator_agent(output_files)
                
        return sorted(output_files, key=lambda p: p.name)

    def generate_with_supervisor(self, metrics: Any = None) -> List[Path]:
        """Generate knowledge base using the Supervisor Agent."""
        if self.force_rebuild and not self.dry_run:
            self._reset_directory(self.sub_agents_root)
            self._reset_directory(self.output_root)
            self._clear_rag_vector_store()
        
        if self.dry_run:
            logger.debug("[DRY RUN] Would run Supervisor Agent")
            return []
        
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.sub_agents_root.mkdir(parents=True, exist_ok=True)
        
        if self.dry_run:
            logger.debug("[DRY RUN] Would run Supervisor Agent")
            return []
            
        supervisor = self._create_supervisor_agent(metrics=metrics)
        
        base_task = prompts.KB_SUPERVISOR_TASK_TEMPLATE.format(codebase_root=self.codebase_root)
        
        max_retries = 10
        retry_delay = 5.0
        
        for attempt in range(1, max_retries + 1):
            try:
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
        
        # Validator removed per user request (Step Id 1336)
        # if not self.dry_run:
        #     self._run_validator_agent(output_files)
        
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

    def _create_supervisor_agent(self, metrics: Any = None):
        from toolkits.supervisor_toolkit import build_supervisor_tools
        from utils.llm_factory import create_model
        tools = build_supervisor_tools(
            codebase_root=str(self.codebase_root),
            sub_agents_root=str(self.sub_agents_root),
            output_root=str(self.output_root),
            metrics=metrics,
        )
        model = create_model(role="supervisor", metrics=metrics)
        return ToolCallingAgent(
            name="knowledge_base_supervisor",
            description="Supervises and coordinates knowledge base generation",
            tools=tools,
            model=model,
            instructions=prompts.SUPERVISOR_AGENT_PROMPT,
        )

    def _run_summary_agent(self, files: List[Path]) -> Path | None:
        """Run the Summarizer Agent to generate the Executive Summary."""
        summary_path = self.output_root / "executive_summary.md"
        
        # 1. Define Tools strictly for the output directory
        from smolagents import Tool
        
        class GetKBTreeTool(Tool):
            name = "get_kb_tree"
            description = "Get a tree view of the raw sub-agent knowledge base files."
            inputs = {}
            output_type = "string"
            
            def forward(self2) -> str:
                tree_str = ""
                # We want to see what's inside sub_agents_root
                # Structure: sub_agents_root / target_name / workspace / summary.md
                # We can iterate and build a nice tree
                if not self.sub_agents_root.exists():
                    return "Sub-agents root directory not found."
                
                for path in sorted(self.sub_agents_root.rglob("*.md")):
                    # Relativize path
                    try:
                        rel = path.relative_to(self.sub_agents_root)
                        tree_str += f"- {rel}\n"
                    except ValueError:
                        pass
                return tree_str if tree_str else "No markdown files found in sub-agents root."

        class ReadKBTool(Tool):
            name = "read_knowledge_base_file"
            description = "Read a knowledge base summary file from the sub-agents directory."
            inputs = {"filename": {"type": "string", "description": "Relative path to the file (from get_kb_tree)"}}
            output_type = "string"
            
            def forward(self2, filename: str) -> str:
                # Security check
                if ".." in filename or filename.startswith("/"):
                     return "Access denied for absolute or parent paths."
                
                # Check in sub_agents_root first (primary source now)
                path = self.sub_agents_root / filename
                if path.exists() and self.sub_agents_root in path.resolve().parents:
                    return path.read_text(encoding="utf-8")
                
                # Fallback to output_root for older files
                path_out = self.output_root / filename
                if path_out.exists() and self.output_root in path_out.resolve().parents:
                    return path_out.read_text(encoding="utf-8")

                return f"File '{filename}' not found."

        class WriteKBTool(Tool):
            name = "write_workspace_file"
            description = "Write the executive summary."
            inputs = {
                "file_path": {"type": "string", "description": "Must be 'executive_summary.md'"},
                "content": {"type": "string", "description": "Markdown content"}
            }
            output_type = "string"
            
            def forward(self2, file_path: str, content: str) -> str:
                if file_path != "executive_summary.md":
                    return "Error: You can only write to 'executive_summary.md'."
                
                (self.output_root / file_path).write_text(content, encoding="utf-8")
                return "Successfully wrote executive_summary.md"

        # 2. Build Agent
        from utils.llm_factory import create_model
        model = create_model(role="summarizer")
        
        agent = ToolCallingAgent(
            name="summarizer",
            description="Synthesizes knowledge base execution summary",
            tools=[GetKBTreeTool(), ReadKBTool(), WriteKBTool()],
            model=model,
            instructions=prompts.SUMMARIZER_KB_PROMPT,
        )
        
        logger.info("Starting Summarizer Agent...")
        try:
            agent.run("Generate the Executive Summary based on the available Knowledge Base files.")
            if summary_path.exists():
                return summary_path
        except Exception as e:
            logger.error(f"Summarizer Agent failed: {e}")
            
        return None

    def _run_validator_agent(self, paths: List[Path]):
        """Run the Validator Agent on generated files."""
        if not paths:
            return

        from toolkits.validator_toolkit import build_validator_tools
        from utils.llm_factory import create_model
        
        # Use Flash model for validation (cost-efficient)
        model = create_model(role="sub_agent") 
        
        tools = build_validator_tools(target_root=self.output_root)
        
        validator = ToolCallingAgent(
            name="markdown_validator",
            description="Validates and fixes markdown formatting.",
            tools=tools,
            model=model,
            instructions=prompts.VALIDATOR_AGENT_PROMPT,
        )

        for path in paths:
            # Skip plan files as per user request
            if "plan" in path.name.lower():
                logger.debug(f"Skipping validation for plan file: {path.name}")
                continue

            try:
                # Relative filename for the tool
                filename = path.name
                logger.info(f"🔍 Validating {filename}...")
                
                validator.run(f"Validate and fix formatting issues in '{filename}'.")
                
                logger.info(f"✅ Validation complete for {filename}")
            except Exception as e:
                logger.warning(f"Validator failed for {filename}: {e}")

    def _reset_directory(self, path: Path):
        if path.exists(): shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    def _clear_rag_vector_store(self):
        pass
