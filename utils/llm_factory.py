"""Factory for initializing LiteLLM models with standardized configuration."""
import os
from loguru import logger
from smolagents import LiteLLMModel
from dotenv import load_dotenv

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")

def create_model(model_id: str | None = None, api_key: str | None = None) -> LiteLLMModel:
    """Create and configure a LiteLLMModel instance.
    
    Automatically configures LITELLM_NUM_RETRIES to 10 for robustness.
    """
    mid = model_id or LITELLM_MODEL_ID
    key = api_key or LITELLM_API_KEY
    
    if not mid or not key:
        raise ValueError("LITELLM_MODEL_ID and LITELLM_API_KEY must be configured in environment or passed explicitly.")

    # Configure automatic retries via environment variable
    # This is a global side-effect for litellm, but consistent with our robustness goals
    # Infinite-ish retries to handle long blocks
    os.environ["LITELLM_NUM_RETRIES"] = "30" 
    # Add longer backoff to handle Vertex AI quotas
    os.environ["LITELLM_RETRY_MIN_WAIT"] = "1"
    os.environ["LITELLM_RETRY_MAX_WAIT"] = "60"
    
    logger.debug(f"Initializing model {mid}")
    
    # Special handling for Vertex AI Model Garden (Claude, Llama, etc.)
    # identifying via 'vertex_ai/' prefix
    if mid.startswith("vertex_ai/"):
        vertex_project = os.getenv("VERTEXAI_PROJECT")
        vertex_location = os.getenv("VERTEXAI_LOCATION")
        
        # If the user has these set, pass them explicitly. 
        # LiteLLM also looks for them in env, but explicit passing ensures smolagents usage.
        if vertex_project and vertex_location:
             return LiteLLMModel(
                 model_id=mid, 
                 api_key=key,
                 vertex_ai_project=vertex_project,
                 vertex_ai_location=vertex_location
             )

    return LiteLLMModel(model_id=mid, api_key=key)
