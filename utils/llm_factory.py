"""Factory for initializing LiteLLM models with standardized configuration."""
import os
from typing import List, Dict, Any, Optional, Literal
from loguru import logger
from smolagents import LiteLLMModel
from dotenv import load_dotenv



# ---------------------------------------------------------------------------
# Robust API Throttling & Retry Logic
# ---------------------------------------------------------------------------
import time
import random

def throttled_api_call(func, *args, estimated_tokens=0, **kwargs):
    """
    Executes an API call with robust retry logic for 429/Resource Exhausted errors.
    Uses exponential backoff with jitter.
    """
    max_retries = 15  # Very high retry count for resilience
    base_delay = 5.0
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
            
        except Exception as e:
            error_msg = str(e).lower()
            # Detect Rate Limit / Resource Exhausted errors
            if "429" in error_msg or "resource exhausted" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                if attempt == max_retries - 1:
                    logger.error(f"❌ Max retries ({max_retries}) exhausted for API call. Error: {e}")
                    raise
                
                # Exponential backoff: 5s, 10s, 20s, 40s...
                delay = (base_delay * (2 ** attempt)) + (random.random() * 2.0)
                # Cap delay at 60 seconds
                delay = min(delay, 60.0)
                
                logger.warning(f"⚠️ API Rate Limit (429). Retry {attempt+1}/{max_retries} in {delay:.1f}s...")
                time.sleep(delay)
            else:
                # Re-raise other errors immediately
                raise

class RateLimitedLiteLLMModel(LiteLLMModel):
    """Wrapper around LiteLLMModel that enforces rate limits."""
    
    def __call__(self, messages: List[Dict[str, Any]], *args, **kwargs) -> Any:
        # Estimate input tokens (rough approximation)
        est_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4
        # Add basic throttling for high-frequency calls
        time.sleep(1.0) 
        
        return throttled_api_call(
            super().__call__, 
            messages, 
            *args, 
            estimated_tokens=est_tokens, 
            **kwargs
        )

load_dotenv()

# Default model (fallback)
LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")

# Role-specific models for hybrid strategy
# Pro for quality-critical tasks, Flash for high-volume tasks
SUPERVISOR_MODEL_ID = os.getenv("SUPERVISOR_MODEL_ID", "vertex_ai/gemini-2.5-pro")
SUB_AGENT_MODEL_ID = os.getenv("SUB_AGENT_MODEL_ID", "vertex_ai/gemini-2.5-flash")
TUTORIAL_MODEL_ID = os.getenv("TUTORIAL_MODEL_ID", "vertex_ai/gemini-2.5-pro")
JUDGE_MODEL_ID = os.getenv("JUDGE_MODEL_ID", "vertex_ai/gemini-2.5-pro")

# Role type for type hints
ModelRole = Literal["supervisor", "sub_agent", "tutorial", "judge", "default"]


def get_model_for_role(role: ModelRole) -> str:
    """Get the appropriate model ID for a given role."""
    role_map = {
        "supervisor": SUPERVISOR_MODEL_ID,
        "sub_agent": SUB_AGENT_MODEL_ID,
        "tutorial": TUTORIAL_MODEL_ID,
        "judge": JUDGE_MODEL_ID,
        "default": LITELLM_MODEL_ID or SUB_AGENT_MODEL_ID,
    }
    return role_map.get(role, LITELLM_MODEL_ID or SUB_AGENT_MODEL_ID)


def create_model(
    model_id: str | None = None, 
    api_key: str | None = None,
    role: ModelRole | None = None,
) -> LiteLLMModel:
    """Create and configure a LiteLLMModel instance.
    
    Args:
        model_id: Explicit model ID (overrides role-based selection).
        api_key: API key for the model.
        role: Role for automatic model selection (supervisor, sub_agent, tutorial, judge).
    
    Automatically configures LITELLM_NUM_RETRIES to 10 for robustness.
    """
    # Priority: explicit model_id > role-based > default env var
    if model_id:
        mid = model_id
    elif role:
        mid = get_model_for_role(role)
    else:
        mid = LITELLM_MODEL_ID
    
    key = api_key or LITELLM_API_KEY
    
    if not mid or not key:
        raise ValueError("LITELLM_MODEL_ID and LITELLM_API_KEY must be configured in environment or passed explicitly.")

    # Configure automatic retries via environment variable (Resilience for 429)
    os.environ["LITELLM_NUM_RETRIES"] = "5"
    os.environ["LITELLM_REQUEST_TIMEOUT"] = "120"
    
    logger.info(f"Creating model: {mid} (role: {role or 'default'})")
    
    # Configure arguments for LiteLLMModel
    kwargs = {}
    
    # Enable reasoning for 2.5-pro models
    if "gemini-2.5-pro" in mid:
        # Revert thinking parameter to avoid tool call issues
        # kwargs["thinking"] = {"type": "enabled", "budget_tokens": -1}
        # Increase token limit for large file generation
        kwargs["max_tokens"] = 16384
        logger.debug("Disabled explicit thinking/reasoning for Pro model to fix empty tool args")

    # Enable thinking for 2.5-flash (Sub-agents)
    if "gemini-2.5-flash" in mid:
        # thinkingBudget=-1 enables dynamic thinking
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": -1}
        logger.debug("Enabled dynamic thinking (budget=-1) for Flash model")

    # Support for explicit Vertex credentials (ADC workaround)
    vertex_creds_path = os.getenv("VERTEX_CREDENTIALS")
    if vertex_creds_path:
        try:
            import json
            with open(vertex_creds_path, 'r') as f:
                creds_json = json.load(f)
            kwargs["vertex_credentials"] = json.dumps(creds_json)
            logger.debug("Loaded Vertex credentials from {}", vertex_creds_path)
        except Exception as e:
            logger.warning("Failed to load VERTEX_CREDENTIALS: {}", e)

    return RateLimitedLiteLLMModel(
        model_id=mid, 
        api_key=key,
        **kwargs
    )
