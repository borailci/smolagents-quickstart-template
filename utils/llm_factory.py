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
    """Wrapper around LiteLLMModel that enforces rate limits and tracks metrics."""
    
    def __init__(self, *args, metrics=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._metrics = metrics  # PhaseMetrics object for recording
    
    def set_metrics(self, metrics):
        """Set the metrics object for token tracking."""
        self._metrics = metrics
    
    def _fix_thinking_mode_tool_calls(self, response: Any) -> Any:
        """
        Fix Gemini 2.5 thinking mode issue where tool call arguments are empty/malformed
        but the actual content is in 'reasoning_content' field (LiteLLM's thinking output).
        
        LiteLLM maps Gemini's thinking output to: message.reasoning_content
        """
        import json
        import re
        
        if not response or not hasattr(response, 'choices') or not response.choices:
            return response
        
        try:
            choice = response.choices[0]
            msg = getattr(choice, 'message', None)
            if not msg:
                return response
            
            # Get reasoning_content (thinking output) - this is where Gemini puts the actual content
            reasoning_content = getattr(msg, 'reasoning_content', '') or ''
            content = getattr(msg, 'content', '') or ''
            tool_calls = getattr(msg, 'tool_calls', [])
            
            # Use reasoning_content if available, otherwise fallback to content
            thinking_output = reasoning_content if reasoning_content else content
            
            if not tool_calls or not thinking_output:
                return response
            
            # Check each tool call for malformed arguments
            for tc in tool_calls:
                fn = getattr(tc, 'function', None)
                if not fn:
                    continue
                
                args_str = getattr(fn, 'arguments', '') or ''
                
                # Check if arguments are empty or malformed
                if self._is_malformed_args(args_str, fn.name):
                    # Try to extract content from thinking (reasoning_content)
                    fixed_args = self._extract_content_from_thinking(thinking_output, fn.name)
                    if fixed_args:
                        fn.arguments = fixed_args
                        logger.info(f"[THINKING FIX] Fixed malformed args for {fn.name}")
            
            return response
            
        except Exception as e:
            logger.debug(f"[THINKING FIX] Error: {e}")
            return response
    
    def _is_malformed_args(self, args_str: str, tool_name: str) -> bool:
        """Check if tool call arguments are malformed."""
        if not args_str or len(args_str.strip()) < 10:
            return True
        
        # Check for common malformed patterns
        stripped = args_str.strip()
        malformed = [
            '{"content": ""}',
            '{"content": " "}',
            '{"content": "   "}',
            '"content="',
            'content=',
        ]
        
        for pattern in malformed:
            if pattern in stripped:
                return True
        
        # For write_workspace_file, check if content is too short
        if tool_name == "write_workspace_file":
            try:
                import json
                parsed = json.loads(args_str)
                content_val = parsed.get("content", "")
                if len(content_val.strip()) < 50:
                    return True
            except:
                pass
        
        return False
    
    def _extract_content_from_thinking(self, thinking_content: str, tool_name: str) -> str | None:
        """Extract actual content from thinking output for a specific tool."""
        import json
        import re
        
        if not thinking_content or len(thinking_content) < 50:
            return None
        
        # For write_workspace_file, look for markdown content
        if tool_name == "write_workspace_file":
            # Try to find markdown blocks
            md_match = re.search(r'```markdown\n(.*?)\n```', thinking_content, re.DOTALL)
            if md_match:
                content = md_match.group(1).strip()
                if len(content) >= 50:
                    return json.dumps({"file_path": "compilation_plan.md", "content": content})
            
            # Try to find plan content directly
            if "# Knowledge Base Plan" in thinking_content or "## Tasks" in thinking_content:
                # Extract the plan section
                plan_start = thinking_content.find("# Knowledge Base Plan")
                if plan_start == -1:
                    plan_start = thinking_content.find("## Tasks")
                
                if plan_start >= 0:
                    plan_content = thinking_content[plan_start:].strip()
                    # Find the end of the plan
                    end_markers = ["\n\n\n", "```", "Now I will"]
                    for marker in end_markers:
                        end_idx = plan_content.find(marker)
                        if end_idx > 50:
                            plan_content = plan_content[:end_idx].strip()
                            break
                    
                    if len(plan_content) >= 50:
                        return json.dumps({"file_path": "compilation_plan.md", "content": plan_content})
        
        return None
    
    def __call__(self, messages: List[Dict[str, Any]], *args, **kwargs) -> Any:
        # Estimate input tokens (rough approximation)
        est_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4
        # Add basic throttling for high-frequency calls
        time.sleep(1.0) 
        
        try:
            response = throttled_api_call(
                super().__call__, 
                messages, 
                *args, 
                estimated_tokens=est_tokens, 
                metrics=self._metrics,
                **kwargs
            )
            
            # Fix Gemini 2.5 thinking mode: Extract content from thinking if tool call args are empty
            response = self._fix_thinking_mode_tool_calls(response)
            
            # DEBUG: Log raw response for tool call issues
            if response:
                try:
                    if hasattr(response, 'choices') and response.choices:
                        choice = response.choices[0]
                        msg = getattr(choice, 'message', None)
                        if msg:
                            content = getattr(msg, 'content', '')
                            tool_calls = getattr(msg, 'tool_calls', [])
                            logger.debug(f"[LLM DEBUG] Content length: {len(content) if content else 0}")
                            logger.debug(f"[LLM DEBUG] Tool calls: {len(tool_calls) if tool_calls else 0}")
                            if tool_calls:
                                for tc in tool_calls[:2]:
                                    fn = getattr(tc, 'function', None)
                                    if fn:
                                        args_str = getattr(fn, 'arguments', '')[:200]
                                        logger.debug(f"[LLM DEBUG] Tool: {fn.name}, Args: {args_str}...")
                except Exception as e:
                    logger.debug(f"[LLM DEBUG] Error logging response: {e}")
            
            # Extract token usage from response if available
            if self._metrics and response:
                try:
                    # LiteLLM returns a ModelResponse with usage attribute
                    usage = getattr(response, 'usage', None)
                    if usage:
                        input_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                        output_tokens = getattr(usage, 'completion_tokens', 0) or 0
                        self._metrics.record_tokens(input_tokens, output_tokens)
                except Exception:
                    pass  # Silently ignore if usage extraction fails
            
            return response
            
        except Exception as e:
            # Detect context overflow errors
            error_msg = str(e).lower()
            if self._metrics:
                is_overflow = (
                    "context length" in error_msg or 
                    "maximum context" in error_msg or 
                    "token limit" in error_msg or
                    "too long" in error_msg
                )
                self._metrics.record_error(str(e), is_overflow=is_overflow)
            raise

load_dotenv()

# Import config for model IDs
from config import settings

# API key still from env (security)
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")

# Role type for type hints
ModelRole = Literal["supervisor", "sub_agent", "tutorial", "judge", "default"]


def get_model_for_role(role: ModelRole) -> str:
    """Get the appropriate model ID for a given role."""
    role_map = {
        "supervisor": settings.SUPERVISOR_MODEL_ID,
        "sub_agent": settings.SUB_AGENT_MODEL_ID,
        "tutorial": settings.MODEL_ID,
        "judge": settings.MODEL_ID,
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
    
    key = api_key or LITELLM_API_KEY
    
    if not mid:
        raise ValueError("Model ID must be configured in config.py or passed explicitly.")

    # Configure automatic retries via environment variable (Resilience for 429)
    os.environ["LITELLM_NUM_RETRIES"] = "5"
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
