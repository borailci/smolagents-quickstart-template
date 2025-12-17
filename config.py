
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

    # --- Sub-Agent Settings ---
    # --- Sub-Agent Settings ---
    SUB_AGENT_MAX_RETRIES: int = int(os.getenv("SUB_AGENT_MAX_RETRIES", "10"))

    # --- File Reading Limits ---
    MAX_READ_LINES: int = int(os.getenv("MAX_READ_LINES", "300"))  # Reduced from 350
    MAX_TREE_DEPTH: int = int(os.getenv("MAX_TREE_DEPTH", "5"))
    MAX_TREE_ITEMS: int = int(os.getenv("MAX_TREE_ITEMS", "200"))
    MIN_WRITE_CHARS: int = int(os.getenv("MIN_WRITE_CHARS", "50"))

    # --- Rate Limiting ---
    RATE_LIMIT_WINDOW_SECONDS: float = float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60.0"))
    RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "30"))
    RATE_LIMIT_MIN_INTERVAL: float = float(os.getenv("RATE_LIMIT_MIN_INTERVAL", "5.0"))

settings = Settings()
