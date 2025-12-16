
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from toolkits.rag_store import SimpleChromaRAGStore

def test_rag_generation():
    load_dotenv()
    
    codebase_root = Path(os.getcwd())
    # Use a temporary or specific test output directory for the RAG store
    rag_output_path = codebase_root / "data" / "rag_test_codebase_only"
    
    logger.info(f"Target Codebase: {codebase_root}")
    logger.info(f"RAG Output: {rag_output_path}")
    
    try:
        store = SimpleChromaRAGStore(
            codebase_root=codebase_root,
            # KB root is required by init, but we won't index it. 
            # Pointing to a dummy or existing path is fine.
            knowledge_base_root=codebase_root / "data" / "dummy_kb", 
            persist_directory=rag_output_path,
        )
        
        logger.info("Starting RAG generation (Codebase Only)...")
        store.ensure_index(
            include_codebase=True,
            include_knowledge_base=False,
            force_rebuild=True
        )
        
        logger.info("✅ RAG Generation Successful!")
        
        # Quick Verification
        collection = store.client.get_collection(store.collection_name)
        count = collection.count()
        logger.info(f"Feature check: Collection '{store.collection_name}' contains {count} items.")
        
    except Exception as e:
        logger.error(f"❌ RAG Generation Failed: {e}")
        raise

if __name__ == "__main__":
    test_rag_generation()
