
import time
from typing import Callable, TypeVar, Any
from loguru import logger

T = TypeVar("T")

def run_with_rate_limit_retry(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 10,
    retry_delay: float = 5.0,
    **kwargs: Any
) -> T:
    """
    Run a function (usually agent.run) with automatic rate limit retries.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            # Broad rate limit detection
            is_rate_limit = (
                "rate" in error_str 
                or "429" in error_str 
                or "exhausted" in error_str
                or "quota" in error_str
                or "too many requests" in error_str
            )
            
            if is_rate_limit and attempt < max_retries:
                logger.warning(
                    f"Rate limit hit (attempt {attempt}/{max_retries}). Waiting {retry_delay}s...",
                )
                time.sleep(retry_delay)
            else:
                if attempt == max_retries and is_rate_limit:
                    logger.error("Max retries reached for rate limit.")
                # Pass through non-rate-limit errors or max retries
                raise e
    raise RuntimeError("Unreachable")
