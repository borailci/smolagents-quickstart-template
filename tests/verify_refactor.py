
import sys
import os
from pathlib import Path

# Add project root to path (insert at 0 to prioritize local modules over installed packages)
sys.path.insert(0, str(Path(__file__).parent.parent))

def verify():
    print("Verifying Refactoring...")
    
    # 1. Check Config
    try:
        from config import settings
        print(f"Config loaded. Batch size: {settings.RAG_EMBED_BATCH_SIZE}")
        assert settings.RAG_EMBED_BATCH_SIZE == 10
    except Exception as e:
        print(f"FAILED to load config: {e}")
        return

    # 2. Check RAG Store
    try:
        from toolkits.rag_store import SimpleChromaRAGStore
        print("RAG Store imported successfully.")
    except Exception as e:
        print(f"FAILED to import RAG Store: {e}")
        return

    # 3. Check Sub Agent Toolkit
    try:
        from toolkits.sub_agent_toolkit import run_sub_agent_tasks
        print("Sub Agent Toolkit imported successfully.")
    except Exception as e:
        print(f"FAILED to import Sub Agent Toolkit: {e}")
        return
        
    # 4. Check KB Builder
    try:
        from pipelines.knowledge_base_builder import KnowledgeBaseBuilder
        builder = KnowledgeBaseBuilder(dry_run=True)
        print("KnowledgeBaseBuilder instantiated successfully.")
    except Exception as e:
        print(f"FAILED to import/instantiate KB Builder: {e}")
        return

    print("VERIFICATION SUCCESSFUL: All modules loaded and config is active.")

if __name__ == "__main__":
    verify()
