
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path.cwd()))

from pipelines.types import DocumentationTarget
from utils.llm_factory import RateLimitedLiteLLMModel, create_model

def test_documentation_target_identifier_sanitization():
    """Verify paths are sanitized into valid identifiers."""
    t1 = DocumentationTarget(path=Path("src/api/routes.py"), label="test")
    assert t1.identifier == "src_api_routes.py"
    
    t2 = DocumentationTarget(path=Path("tests"), label="test")
    assert t2.identifier == "tests"
    
    t3 = DocumentationTarget(path=Path("/abs/path/to/file"), label="test")
    assert "abs_path_to_file" in t3.identifier 

def test_rate_limited_model_calls_throttler():
    """Verify that RateLimitedLiteLLMModel delegates to throttled_api_call."""
    
    mock_tracker = MagicMock()
    with patch("utils.llm_factory.throttled_api_call") as mock_throttle:
        # Create model instance manually to bypass factory env checks if needed
        model = RateLimitedLiteLLMModel(model_id="test", api_key="test")
        
        messages = [{"role": "user", "content": "hello"}]
        
        # Mock super call isn't easily possible with class inheritance without more complex mocking
        # Instead, we just check if throttled_api_call is invoked
        
        # We need to mock the super().__call__ or just trust that throttled_api_call is called with it.
        # Since throttled_api_call takes a func as first arg.
        
        model(messages)
        
        mock_throttle.assert_called_once()
        args, kwargs = mock_throttle.call_args
        # First arg should be the bound super().call method
        assert callable(args[0]) 
        # Second arg should be messages
        assert args[1] == messages
        # estimated_tokens should be present
        assert "estimated_tokens" in kwargs
        assert kwargs["estimated_tokens"] > 0

def test_create_model_returns_rate_limited_wrapper():
    """Verify factory returns wrapped model."""
    with patch("utils.llm_factory.os.getenv", return_value="dummy"):
        model = create_model(model_id="gemini-test", api_key="key")
        assert isinstance(model, RateLimitedLiteLLMModel)
