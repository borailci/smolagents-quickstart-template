
import os
from pathlib import Path

class Settings:
    # --- Project Root ---
    PROJECT_ROOT: Path = Path(__file__).parent.resolve()
    
    # --- LLM Model Configuration ---
    # Vertex AI model IDs (used by LiteLLM)
    # NOTE: gemini-2.5-pro thinking mode causes empty content in tool calls
    # Using 2.0-flash for reliable tool calling
    MODEL_ID: str = "vertex_ai/gemini-2.5-pro"
    SUPERVISOR_MODEL_ID: str = "vertex_ai/gemini-2.5-pro"
    SUB_AGENT_MODEL_ID: str = "vertex_ai/gemini-2.5-flash"
    
    # --- Codebase to Analyze ---
    # Change this to point to the codebase you want to analyze
    CODEBASE_ROOT: Path = PROJECT_ROOT / "data" / "agent_workspace" / "instructor" 
    
    # --- Deep Agent Output Structure ---
    # data/deep_agent/
    #   ├── knowledge_base/
    #   ├── sub_agents_workspace/
    #   └── tutorials/
    DEEP_AGENT_ROOT: Path = PROJECT_ROOT / "data" / "deep_agent"
    DEEP_AGENT_KB: Path = DEEP_AGENT_ROOT / "knowledge_base"
    DEEP_AGENT_KB_SUB_AGENTS: Path = DEEP_AGENT_ROOT / "sub_agents_kb"
    DEEP_AGENT_SUB_AGENTS: Path = DEEP_AGENT_ROOT / "sub_agents_workspace" # Deprecated, keep for legacy
    DEEP_AGENT_TUTORIALS: Path = DEEP_AGENT_ROOT / "tutorials"
    DEEP_AGENT_TUTORIAL_SUB_AGENTS: Path = DEEP_AGENT_ROOT / "sub_agents_tutorials"
    
    # --- Baseline Output Structure ---
    # data/baseline/
    #   ├── knowledge_base/  (empty, not used in baseline)
    #   ├── sub_agents_workspace/
    #   └── tutorials/
    BASELINE_ROOT: Path = PROJECT_ROOT / "data" / "baseline"
    BASELINE_KB: Path = BASELINE_ROOT / "knowledge_base"
    BASELINE_SUB_AGENTS: Path = BASELINE_ROOT / "sub_agents_workspace"
    BASELINE_TUTORIALS: Path = BASELINE_ROOT / "tutorials"
    
    # --- Legacy Aliases (for backwards compatibility) ---
    KNOWLEDGE_BASE_OUTPUT: Path = DEEP_AGENT_KB
    SUB_AGENTS_ROOT: Path = DEEP_AGENT_SUB_AGENTS
    TUTORIAL_OUTPUT: Path = DEEP_AGENT_TUTORIALS
    DEEP_AGENT_OUTPUT_ROOT: Path = DEEP_AGENT_ROOT
    BASELINE_OUTPUT_ROOT: Path = BASELINE_ROOT
    
    # --- Sub-Agent Settings ---
    SUB_AGENT_MAX_RETRIES: int = 10

    # --- File Reading Limits ---
    MAX_READ_LINES: int = 500
    MAX_TREE_DEPTH: int = 5
    MAX_TREE_ITEMS: int = 200
    MIN_WRITE_CHARS: int = 50

    # --- Rate Limiting ---
    RATE_LIMIT_WINDOW_SECONDS: float = 60.0
    RATE_LIMIT_MAX_REQUESTS: int = 10
    RATE_LIMIT_MIN_INTERVAL: float = 2.0

settings = Settings()
