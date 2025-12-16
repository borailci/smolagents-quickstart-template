
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load env vars from .env file
load_dotenv()

class Settings:
    # --- Paths ---
    PROJECT_ROOT: Path = Path(__file__).parent.resolve()
    CODEBASE_ROOT: Path = Path(os.getenv("CODEBASE_ROOT_PATH", "data/agent_workspace")).resolve()
    KNOWLEDGE_BASE_OUTPUT: Path = Path(os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH", "data/agent_workspace/knowledge_base")).resolve()
    SUB_AGENTS_ROOT: Path = Path(os.getenv("SUB_AGENTS_ROOT_PATH", "data/agent_workspace/sub_agents_workspace")).resolve()
    TUTORIAL_OUTPUT: Path = Path(os.getenv("TUTORIAL_OUTPUT_PATH", "data/agent_workspace/tutorials")).resolve()

    # --- Output Roots ---
    BASELINE_OUTPUT_ROOT: Path = Path(os.getenv("BASELINE_OUTPUT_ROOT", "data/baseline-tutorials")).resolve()
    DEEP_AGENT_OUTPUT_ROOT: Path = Path(os.getenv("DEEP_AGENT_OUTPUT_ROOT", "data/deepagent-tutorials")).resolve()

    # --- Models ---
    LITELLM_MODEL_ID: str = os.getenv("LITELLM_MODEL_ID", "gemini/gemini-1.5-pro-latest")
    LITELLM_API_KEY: Optional[str] = os.getenv("LITELLM_API_KEY")
    
    # RAG Embedding
    EMBEDDING_MODEL_ID: str = os.getenv("LITELLM_EMBEDDING_MODEL_ID", 
                                       "gemini/text-embedding-004" if "gemini" in LITELLM_MODEL_ID.lower() else "text-embedding-3-small")
    
    # --- RAG Settings ---
    # CRITICAL FIX: Lower batch size to avoid ResourceExhausted
    RAG_EMBED_BATCH_SIZE: int = int(os.getenv("RAG_EMBED_BATCH_SIZE", "10"))
    RAG_EMBED_REQUEST_PAUSE_SECONDS: float = float(os.getenv("RAG_EMBED_REQUEST_PAUSE_SECONDS", "1.0"))
    RAG_EMBED_MAX_RETRIES: int = int(os.getenv("RAG_EMBED_MAX_RETRIES", "10"))
    RAG_EMBED_RETRY_BACKOFF_SECONDS: float = float(os.getenv("RAG_EMBED_RETRY_BACKOFF_SECONDS", "5.0"))

    # --- Sub-Agent Settings ---
    SUB_AGENT_RPM: float = float(os.getenv("SUB_AGENT_REQUESTS_PER_MINUTE", "4.0"))
    SUB_AGENT_MAX_RETRIES: int = int(os.getenv("SUB_AGENT_MAX_RETRIES", "10"))
    SUB_AGENT_TOOL_CALL_BUDGET: int = 6

    # --- File Reading Limits ---
    MAX_READ_LINES: int = int(os.getenv("MAX_READ_LINES", "250"))  # Reduced from 350
    MAX_TREE_DEPTH: int = int(os.getenv("MAX_TREE_DEPTH", "5"))
    MAX_TREE_ITEMS: int = int(os.getenv("MAX_TREE_ITEMS", "200"))
    MIN_WRITE_CHARS: int = int(os.getenv("MIN_WRITE_CHARS", "50"))
    MAX_PRELOAD_FILES: int = int(os.getenv("MAX_PRELOAD_FILES", "5"))  # Limit files pre-loaded per spawn

    # --- Rate Limiting ---
    RATE_LIMIT_WINDOW_SECONDS: float = float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "90.0"))
    RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "4"))
    RATE_LIMIT_MIN_INTERVAL: float = float(os.getenv("RATE_LIMIT_MIN_INTERVAL", "5.0"))

settings = Settings()
