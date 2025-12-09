"""
Unified Deep Agent Pipeline.

Orchestrates the entire documentation journey:
1. Knowledge Base Generation (using KB Supervisor)
2. Tutorial Generation (using Tutorial Supervisor)
"""
import shutil
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

from loguru import logger
from dotenv import load_dotenv

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
        logger.info("🚀 Starting Deep Agent Pipeline")
        logger.info(f"Target: {self.config.codebase_root}")
        logger.info(f"Output: {self.config.output_root}")
        
        # Phase 1: Knowledge Base
        logger.info("=== Phase 1: Knowledge Base Generation ===")
        kb_files = self.kb_builder.generate_with_supervisor()
        
        if not kb_files:
            # Check if files already exist (incremental) or if it truly failed
            existing = list(self.config.kb_output_path.glob("*.md"))
            if not existing:
                logger.error("KB Generation failed or produced no files. Aborting phase 2.")
                return {"error": "KB Generation failed"}
            else:
                logger.warning("KB Generation returned no new files, but previous content exists. Proceeding.")
        
        # Phase 2: Tutorials
        logger.info("=== Phase 2: Tutorial Generation ===")
        tutorials = self.tutorial_generator.generate_with_supervisor()
        
        logger.info("✅ Deep Agent Pipeline Complete")
        return {
            "kb_files": [str(p) for p in kb_files],
            "tutorials": [str(p) for p in tutorials]
        }
