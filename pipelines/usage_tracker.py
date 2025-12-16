"""Proactive rate limiting with usage tracking for Vertex AI API calls."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger


@dataclass
class UsageTracker:
    """
    Track API usage and proactively throttle to stay under rate limits.
    
    Vertex AI limits (typical for Gemini):
    - RPM (Requests Per Minute): 60-100
    - TPM (Tokens Per Minute): 2-4 million
    
    This tracker monitors usage and adds delays BEFORE hitting limits.
    """
    
    # Configurable limits (conservative defaults)
    max_rpm: int = 40  # Stay under typical 60 RPM limit
    max_tpm: int = 80000  # Stay under typical 100K TPM limit
    
    # Internal tracking
    requests_this_minute: int = 0
    tokens_this_minute: int = 0
    minute_start: float = field(default_factory=time.time)
    
    # Thread safety
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def _reset_if_new_minute(self) -> None:
        """Reset counters if a new minute has started."""
        now = time.time()
        elapsed = now - self.minute_start
        if elapsed >= 60:
            self.requests_this_minute = 0
            self.tokens_this_minute = 0
            self.minute_start = now
            logger.debug("Usage tracker reset for new minute")
    
    def record_request(self, tokens: int = 0) -> None:
        """Record a completed API request."""
        with self._lock:
            self._reset_if_new_minute()
            self.requests_this_minute += 1
            self.tokens_this_minute += tokens
            logger.debug(
                f"Usage: {self.requests_this_minute}/{self.max_rpm} RPM, "
                f"{self.tokens_this_minute}/{self.max_tpm} TPM"
            )
    
    def wait_if_needed(self, estimated_tokens: int = 5000) -> float:
        """
        Wait if we're approaching rate limits.
        
        Args:
            estimated_tokens: Estimated tokens for the upcoming request
            
        Returns:
            Seconds waited (0 if no wait needed)
        """
        with self._lock:
            self._reset_if_new_minute()
            
            wait_time = 0.0
            
            # Check RPM limit
            if self.requests_this_minute >= self.max_rpm:
                wait_time = max(wait_time, 60 - (time.time() - self.minute_start))
                logger.info(f"RPM limit ({self.max_rpm}) reached, waiting {wait_time:.1f}s")
            
            # Check TPM limit
            if self.tokens_this_minute + estimated_tokens >= self.max_tpm:
                wait_time = max(wait_time, 60 - (time.time() - self.minute_start))
                logger.info(f"TPM limit ({self.max_tpm}) approaching, waiting {wait_time:.1f}s")
            
            if wait_time > 0:
                # Release lock while sleeping
                self._lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self._lock.acquire()
                # Reset after waiting
                self._reset_if_new_minute()
            
            return wait_time
    
    def get_stats(self) -> dict:
        """Get current usage statistics."""
        with self._lock:
            self._reset_if_new_minute()
            elapsed = time.time() - self.minute_start
            return {
                "requests_this_minute": self.requests_this_minute,
                "tokens_this_minute": self.tokens_this_minute,
                "rpm_usage_pct": (self.requests_this_minute / self.max_rpm) * 100,
                "tpm_usage_pct": (self.tokens_this_minute / self.max_tpm) * 100,
                "seconds_in_minute": elapsed,
                "seconds_remaining": max(0, 60 - elapsed),
            }


# Global singleton tracker
_global_tracker: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """Get or create the global usage tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = UsageTracker()
    return _global_tracker


def throttled_api_call(func, *args, estimated_tokens: int = 5000, **kwargs):
    """
    Wrapper for API calls that enforces rate limiting.
    
    Usage:
        result = throttled_api_call(model.generate, prompt, estimated_tokens=10000)
    """
    tracker = get_usage_tracker()
    
    # Wait if we're near limits
    tracker.wait_if_needed(estimated_tokens)
    
    # Make the call
    result = func(*args, **kwargs)
    
    # Record usage (estimate tokens if actual not available)
    tracker.record_request(tokens=estimated_tokens)
    
    return result
