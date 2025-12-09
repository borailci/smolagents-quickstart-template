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
    os.environ["LITELLM_NUM_RETRIES"] = "10"
    
    logger.debug(f"Initializing model {mid}")
    return LiteLLMModel(model_id=mid, api_key=key)
