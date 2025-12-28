"""Factory for initializing LiteLLM models with standardized configuration."""
import os
import re
from typing import List, Dict, Any, Optional, Literal
from loguru import logger
from smolagents import LiteLLMModel
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Robust API Throttling & Retry Logic
# ---------------------------------------------------------------------------
import time
import random
import litellm
from config import settings

# Rate limit error detection pattern (more robust than string matching)
RATE_LIMIT_PATTERN = re.compile(
    r'(429|rate.?limit|quota|resource.?exhaust|too.?many.?requests)',
    re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Global Token Tracking via litellm Callbacks
# ---------------------------------------------------------------------------
import threading

# Thread-local storage for last API response usage
_last_usage = threading.local()

def _litellm_success_callback(kwargs, completion_response, start_time, end_time):
    """Callback to capture token usage from litellm responses."""
    try:
        # Handle both dict and object responses
        if hasattr(completion_response, 'usage'):
            usage = completion_response.usage
            _last_usage.input_tokens = getattr(usage, 'prompt_tokens', 0) or 0
            _last_usage.output_tokens = getattr(usage, 'completion_tokens', 0) or 0
        elif isinstance(completion_response, dict):
            usage = completion_response.get("usage", {})
            _last_usage.input_tokens = usage.get("prompt_tokens", 0) or 0
            _last_usage.output_tokens = usage.get("completion_tokens", 0) or 0
        else:
            _last_usage.input_tokens = 0
            _last_usage.output_tokens = 0
    except Exception as e:
        logger.debug(f"Failed to capture token usage in callback: {e}")
        _last_usage.input_tokens = 0
        _last_usage.output_tokens = 0

# Register the callback globally
litellm.success_callback = [_litellm_success_callback]



class RateLimitedLiteLLMModel(LiteLLMModel):
    """Wrapper around LiteLLMModel that enforces rate limits and tracks metrics."""
    
    def __init__(self, *args, metrics=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._metrics = metrics  # PhaseMetrics object for recording
    
    def set_metrics(self, metrics):
        """Set the metrics object for token tracking."""
        self._metrics = metrics

    
    def __call__(self, messages: List[Dict[str, Any]], *args, **kwargs) -> Any:
        # 1. HARD DELAY: Always wait 2 seconds between steps
        time.sleep(2.0)

        # 2. Estimate input tokens (rough approximation)
        est_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4
        
        # Exponential backoff parameters
        current_wait = 30.0
        max_wait = 120.0
        
        while True:
            try:
                # Call litellm.completion directly to get full response with usage
                print("Calling LLM...")
                full_response = litellm.completion(
                    model=self.model_id,
                    messages=messages,
                    *args,
                    **kwargs
                )
                
                # Extract tokens from full response
                # Log to file for debugging
                try:
                    with open('/tmp/token_debug.log', 'a') as f:
                        f.write(f"\n=== LLM CALL ===\n")
                        f.write(f"metrics: {self._metrics}\n")
                        f.write(f"response type: {type(full_response)}\n")
                        f.write(f"has usage: {hasattr(full_response, 'usage')}\n")
                except:
                    pass
                
                if self._metrics:
                    try:
                        input_tokens = 0
                        output_tokens = 0
                        
                        # Debug: Print response structure
                        print(f"DEBUG: Response type: {type(full_response)}")
                        print(f"DEBUG: Has usage attr: {hasattr(full_response, 'usage')}")
                        if hasattr(full_response, 'usage'):
                            print(f"DEBUG: Usage value: {full_response.usage}")
                        print(f"DEBUG: Response dir: {[x for x in dir(full_response) if not x.startswith('_')][:10]}")
                        
                        # Extract from response.usage
                        if hasattr(full_response, 'usage') and full_response.usage:
                            usage = full_response.usage
                            input_tokens = getattr(usage, 'prompt_tokens', 0) or getattr(usage, 'input_tokens', 0) or 0
                            output_tokens = getattr(usage, 'completion_tokens', 0) or getattr(usage, 'output_tokens', 0) or 0
                            print(f"DEBUG: Extracted tokens - in:{input_tokens}, out:{output_tokens}")
                        
                        if input_tokens > 0 or output_tokens > 0:
                            self._metrics.record_tokens(input_tokens, output_tokens)
                            logger.info(f"📊 Recorded tokens: in={input_tokens}, out={output_tokens}")
                            try:
                                with open('/tmp/token_debug.log', 'a') as f:
                                    f.write(f"✅ RECORDED: in={input_tokens}, out={output_tokens}\n")
                            except:
                                pass
                        else:
                            msg = f"⚠️ No usage info in response. Response type: {type(full_response)}, has usage: {hasattr(full_response, 'usage')}"
                            logger.warning(msg)
                            print(msg)
                    except Exception as e:
                        msg = f"Failed to extract token usage: {e}"
                        logger.warning(msg)
                        print(f"ERROR: {msg}")
                
                # Extract the text content to return (matching LiteLLMModel behavior)
                if hasattr(full_response, 'choices') and full_response.choices:
                    response_text = full_response.choices[0].message.content
                else:
                    response_text = str(full_response)
                
                return response_text

            except Exception as e:
                # Robust Rate Limit Detection
                error_str = str(e).lower()
                is_rate_limit = (
                    "rate limit" in error_str
                    or "429" in error_str
                    or "resource exhausted" in error_str
                    or "quota" in error_str
                    or isinstance(e, getattr(litellm, "RateLimitError", type(None)))
                )

                if is_rate_limit:
                    sleep_time = min(current_wait, max_wait) # Use current_wait as retry_delay
                    logger.warning(f"⚠️ API Rate Limit (429). Blocking execution for {sleep_time}s... (Backoff: {sleep_time}/{max_wait}). Error: {str(e)[:100]}...")
                    time.sleep(sleep_time)
                    current_wait = min(current_wait * 1.5, max_wait)  # Slower exponential backoff
                    continue
                
                # For non-rate-limit errors, we might want to retry a few times too, 
                # but for now let's re-raise to be safe unless it's a known transient error
                logger.error(f"LLM Call failed with non-rate-limit error: {e}")
                
                # Detect context overflow errors for metrics
                if self._metrics:
                    is_overflow = (
                        "context length" in error_str or 
                        "maximum context" in error_str or 
                        "token limit" in error_str or
                        "too long" in error_str
                    )
                    self._metrics.record_error(str(e), is_overflow=is_overflow)
                
                # Re-raise other errors immediately
                raise

load_dotenv()

# Import config for model IDs
from config import settings

# Role type for type hints
ModelRole = Literal["supervisor", "sub_agent", "tutorial", "judge", "default"]

def get_model_for_role(role: ModelRole) -> str:
    """Get the appropriate model ID for a given role."""
    role_map = {
        "supervisor": settings.SUPERVISOR_MODEL_ID,
        "sub_agent": settings.SUB_AGENT_MODEL_ID,
        "tutorial": settings.MODEL_ID,
        "judge": "openai/gpt-oss-20b-maas",
        "default": settings.MODEL_ID,
    }
    return role_map.get(role, settings.MODEL_ID)

def create_model(
    model_id: str | None = None, 
    api_key: str | None = None,
    role: ModelRole | None = None,
    metrics=None,
) -> LiteLLMModel:
    """Create and configure a LiteLLMModel instance.
    
    Args:
        model_id: Explicit model ID (overrides role-based selection).
        api_key: API key for the model.
        role: Role for automatic model selection (supervisor, sub_agent, tutorial, judge).
        metrics: Optional PhaseMetrics object for tracking token usage and errors.
    
    Automatically configures LITELLM_NUM_RETRIES to 10 for robustness.
    """
    # Priority: explicit model_id > role-based > config default
    if model_id:
        mid = model_id
    elif role:
        mid = get_model_for_role(role)
    else:
        mid = settings.MODEL_ID
    
    key = os.getenv("VERTEX_API_KEY")
    
    if not mid:
        raise ValueError("Model ID must be configured in config.py or passed explicitly.")

    # Configure LiteLLM settings
    # Disable LiteLLM's internal retries to prevent double-retry with our custom loop
    os.environ["LITELLM_NUM_RETRIES"] = "0"
    os.environ["LITELLM_REQUEST_TIMEOUT"] = "120"
    
    logger.info(f"Creating model: {mid} (role: {role or 'default'})")
    
    # Configure arguments for LiteLLMModel
    kwargs = {}
    
    # For Gemini 2.5 models: Configure thinking mode
    # Note: 2.5-pro doesn't support thinking_budget=0, so we use "low" instead
    # We handle malformed tool calls in _fix_thinking_mode_tool_calls using reasoning_content
    if "gemini-2.5-pro" in mid:
        kwargs["reasoning_effort"] = "low"  # Minimal thinking for 2.5-pro
        kwargs["max_tokens"] = 16384
        logger.info(f"Using reasoning_effort='low' for {mid}")
    elif "gemini-2.5-flash" in mid:
        kwargs["reasoning_effort"] = "disable"  # Flash supports disable
        kwargs["max_tokens"] = 16384
        logger.info(f"Using reasoning_effort='disable' for {mid}")

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
        metrics=metrics,
        **kwargs
    )
