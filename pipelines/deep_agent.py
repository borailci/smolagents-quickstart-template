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

from pipelines.knowledge_base_builder import KnowledgeBaseBuilder
from pipelines.tutorial_generator import TutorialGenerator
from utils.path_utils import ensure_directory

load_dotenv()

@dataclass
class DeepAgentConfig:
    codebase_root: Path
    output_root: Path
    
    # Sub-paths (can be derived if not passed, but here we expect them)
    kb_output_path: Path
    tutorial_output_path: Path
    kb_sub_agents_path: Path
    tutorial_sub_agents_path: Path
    
    # Flags
    dry_run: bool = False
    force_rebuild_kb: bool = False
    force_rebuild_tutorials: bool = False
    
    # RAG
    enable_rag: bool = True
    rag_codebase_cache_path: Optional[Path] = None

class DeepAgent:
    def __init__(self, config: DeepAgentConfig):
        self.config = config
        
        # Ensure roots exist
        ensure_directory(self.config.output_root)

        # Initialize components with config
        
        # KB Builder
        self.kb_builder = KnowledgeBaseBuilder(
            codebase_root=config.codebase_root,
            output_root=config.kb_output_path,
            sub_agents_root=config.kb_sub_agents_path,
            dry_run=config.dry_run,
            force_rebuild=config.force_rebuild_kb,
        )
        
        # Tutorial Generator
        # Tutorial Generator needs "KB Root" which is kb_output_path
        self.tutorial_generator = TutorialGenerator(
            codebase_root=config.codebase_root,
            knowledge_base_root=config.kb_output_path,
            output_root=config.tutorial_output_path,
            sub_agents_root=config.tutorial_sub_agents_path,
            dry_run=config.dry_run,
            enable_rag=config.enable_rag,
            rag_codebase_cache_path=str(config.rag_codebase_cache_path) if config.rag_codebase_cache_path else None
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
        
        kb_files = self.kb_builder.generate_with_supervisor()
        
        kb_metrics.finish()
        logger.info(f"KB Phase completed in {kb_metrics.duration_seconds:.1f}s")
        
        if not kb_files:
            existing = list(self.config.kb_output_path.glob("*.md"))
            if not existing:
                logger.error("KB Generation failed or produced no files. Aborting phase 2.")
                metrics.finish()
                self._save_metrics(metrics)
                return {"error": "KB Generation failed", "metrics": metrics.to_dict()}
            else:
                logger.warning("KB Generation returned no new files, but previous content exists. Proceeding.")
        
        # Phase 1.5: RAG Generation
        if self.config.enable_rag and not self.config.rag_codebase_cache_path:
            logger.info("=== Phase 1.5: RAG Generation ===")
            try:
                from toolkits.rag_store import SimpleChromaRAGStore
                
                rag_path = self.config.output_root / "rag_store"
                logger.info(f"Building RAG index at {rag_path}...")
                
                store = SimpleChromaRAGStore(
                    codebase_root=self.config.codebase_root,
                    knowledge_base_root=self.config.kb_output_path,
                    persist_directory=rag_path,
                )
                
                store.ensure_index(
                    include_codebase=True,
                    include_knowledge_base=True,
                    force_rebuild=self.config.force_rebuild_tutorials
                )
                logger.info("✅ RAG Generation Complete")
                
            except Exception as e:
                logger.error(f"Failed to generate RAG index: {e}")
                logger.warning("Proceeding with tutorials (RAG might be degraded or empty).")

        # Phase 2: Tutorials
        logger.info("=== Phase 2: Tutorial Generation ===")
        tutorial_metrics = metrics.start_tutorial_phase()
        
        tutorials = self.tutorial_generator.generate_with_supervisor()
        
        tutorial_metrics.finish()
        logger.info(f"Tutorial Phase completed in {tutorial_metrics.duration_seconds:.1f}s")
        
        # Finalize metrics
        metrics.finish()
        self._save_metrics(metrics)
        
        logger.info("✅ Deep Agent Pipeline Complete")
        logger.info(f"Total duration: {metrics.duration_seconds:.1f}s ({metrics.duration_seconds/60:.1f}m)")
        
        return {
            "kb_files": [str(p) for p in kb_files],
            "tutorials": [str(p) for p in tutorials],
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

