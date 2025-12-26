
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path.cwd()))

# pipelines.types import removed
from utils.llm_factory import RateLimitedLiteLLMModel, create_model

def test_create_model_returns_rate_limited_wrapper():
    """Verify factory returns wrapped model."""
    with patch("utils.llm_factory.os.getenv", return_value="dummy"):
        model = create_model(model_id="gemini-test", api_key="key")
        assert isinstance(model, RateLimitedLiteLLMModel)
