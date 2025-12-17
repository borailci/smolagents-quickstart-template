"""
Unified Deep Agent Pipeline.

Orchestrates the entire documentation journey:
1. Knowledge Base Generation (using KB Supervisor)
2. Tutorial Generation (using Tutorial Supervisor)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from loguru import logger
import shutil

from pipelines.knowledge_base_builder import KnowledgeBaseBuilder
from pipelines.tutorial_generator import TutorialGenerator
@dataclass
class DeepAgentConfig:
    codebase_root: Path
    output_root: Path
    
    # Sub-paths
    kb_output_path: Path
    kb_sub_agents_path: Path
    tutorial_output_path: Path
    tutorial_sub_agents_path: Path
    
    # Flags
    dry_run: bool = False
    force_rebuild_kb: bool = False
    force_rebuild_tutorials: bool = False
    
    # RAG
    rag_codebase_cache_path: Optional[Path] = None

class DeepAgent:
    def __init__(self, config: DeepAgentConfig):
        self.config = config
        # Ensure roots exist
        self.config.output_root.mkdir(parents=True, exist_ok=True)

        # Initialize components with config
        
        if self.config.force_rebuild_kb:
            logger.info("Force rebuilding Knowledge Base...")
            if self.config.kb_sub_agents_path.exists():
                logger.info(f"Cleaning KB sub-agents directory: {self.config.kb_sub_agents_path}")
                shutil.rmtree(self.config.kb_sub_agents_path)
            
            # CLEAR CHECKPOINT on force rebuild
            from utils.checkpoint import TaskCheckpoint
            checkpoint_path = self.config.output_root / "analysis_checkpoint.json"
            if checkpoint_path.exists():
                 logger.info(f"Clearing task checkpoint: {checkpoint_path}")
                 TaskCheckpoint(checkpoint_path).clear()
                 
            self.config.kb_sub_agents_path.mkdir(parents=True, exist_ok=True)
        
        # KB Builder
        self.kb_builder = KnowledgeBaseBuilder(
            codebase_root=config.codebase_root,
            output_root=config.kb_output_path,
            sub_agents_root=config.kb_sub_agents_path,
            dry_run=config.dry_run,
            force_rebuild=config.force_rebuild_kb,
        )

        # Tutorial Generator
        self.tutorial_generator = TutorialGenerator(
            codebase_root=config.codebase_root,
            knowledge_base_root=config.kb_output_path,
            output_root=config.tutorial_output_path,
            sub_agents_root=config.tutorial_sub_agents_path,
            dry_run=config.dry_run,
        )
        
    def run(self) -> Dict[str, Any]:
        from utils.metrics import RunMetrics
        from utils.llm_factory import get_model_for_role
        
        # Initialize metrics
        metrics = RunMetrics(
            codebase_name=self.config.codebase_root.name,
            model_id=get_model_for_role("supervisor"),
        )
        
        logger.info("🚀 Starting Deep Agent Pipeline")
        logger.info(f"Target: {self.config.codebase_root}")
        logger.info(f"Output: {self.config.output_root}")
        
        # Phase 1: Knowledge Base
        logger.info("=== Phase 1: Knowledge Base Generation ===")
        kb_metrics = metrics.start_kb_phase()
        
        kb_files = self.kb_builder.generate(metrics=kb_metrics)
        
        kb_metrics.finish()
        logger.info(f"KB Phase completed in {kb_metrics.duration_seconds:.1f}s")
        
        if not kb_files:
            existing = list(self.config.kb_output_path.glob("*.md"))
            if not existing:
                logger.error("KB Generation failed or produced no files.")
                metrics.finish()
                self._save_metrics(metrics)
                return {"error": "KB Generation failed", "metrics": metrics.to_dict()}
            else:
                logger.warning("KB Generation returned no new files, but previous content exists. Proceeding.")
        
        # Phase 2: Tutorial Generation
        logger.info("=== Phase 2: Tutorial Generation ===")
        tutorial_metrics = metrics.start_tutorial_phase()

        tutorial_files = self.tutorial_generator.generate()

        tutorial_metrics.finish()
        logger.info(f"Tutorial Phase completed in {tutorial_metrics.duration_seconds:.1f}s")
        
        # Finalize metrics
        metrics.finish()
        self._save_metrics(metrics)
        
        logger.info("✅ Deep Agent Pipeline Complete")
        logger.info(f"Total duration: {metrics.duration_seconds:.1f}s ({metrics.duration_seconds/60:.1f}m)")
        
        return {
            "kb_files": [str(p) for p in kb_files],
            "tutorial_files": [str(p) for p in tutorial_files],
            "metrics": metrics.to_dict(),
        }
    
    def _save_metrics(self, metrics) -> None:
        """Save metrics to JSON and Markdown files."""
        try:
            json_path = self.config.output_root / "metrics.json"
            md_path = self.config.output_root / "metrics.md"
            
            metrics.save_json(json_path)
            metrics.save_markdown_summary(md_path)
            
            logger.info(f"📊 Metrics saved to {json_path}")
        except Exception as e:
            logger.warning(f"Failed to save metrics: {e}")

