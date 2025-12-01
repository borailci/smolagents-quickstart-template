"""Answer questions using the generated knowledge base with conversation memory."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger
from smolagents import LiteLLMModel
from smolagents.agents import ToolCallingAgent

from prompts import prompts
# Ensure this import matches your actual file structure
from toolkits.knowledge_base_reader_toolkit import build_knowledge_base_reader_tools
from utils.path_utils import ensure_directory

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
KNOWLEDGE_BASE_OUTPUT_PATH = os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
CHAT_TRANSCRIPTS_ROOT = os.getenv("CHAT_TRANSCRIPTS_ROOT")
DEFAULT_REQUESTS_PER_MINUTE = 15.0  # Increased for chat responsiveness


def _require_env(name: str, value: Optional[str]) -> str:
    if not value:
        raise RuntimeError(f"{name} must be configured.")
    return value


class KnowledgeBaseChat:
    """Tool-driven Q&A over knowledge base markdown files."""

    def __init__(
        self,
        *,
        knowledge_base_root: str | Path | None = None,
        transcript_root: str | Path | None = None,
    ) -> None:
        model_id = _require_env("LITELLM_MODEL_ID", LITELLM_MODEL_ID)
        api_key = _require_env("LITELLM_API_KEY", LITELLM_API_KEY)

        self.knowledge_base_root = (
            Path(
                knowledge_base_root
                or _require_env(
                    "KNOWLEDGE_BASE_OUTPUT_PATH", KNOWLEDGE_BASE_OUTPUT_PATH
                )
            )
            .expanduser()
            .resolve()
        )
        if not self.knowledge_base_root.exists():
            raise FileNotFoundError(
                f"Knowledge base directory not found at {self.knowledge_base_root}."
            )

        transcript_value = transcript_root or CHAT_TRANSCRIPTS_ROOT
        self.transcript_root = (
            ensure_directory(transcript_value) if transcript_value else None
        )
        
        # Rate limiting state
        self._last_request_time = 0.0
        self._min_interval = 60.0 / DEFAULT_REQUESTS_PER_MINUTE

        # Initialize Model and Agent ONCE to preserve memory
        self.model = LiteLLMModel(
            model_id=model_id, 
            api_key=api_key,
            requests_per_minute=int(DEFAULT_REQUESTS_PER_MINUTE)
        )
        self.agent = self._build_agent()

    def answer(self, question: str, *, save_transcript: bool = False) -> str:
        """
        Ask a question to the Knowledge Base agent.
        The agent maintains history from previous calls within this instance.
        """
        if not question.strip():
            raise ValueError("Question must be a non-empty string.")

        self._respect_rate_limit()
        
        logger.info("Thinking...")
        start_time = time.monotonic()
        
        try:
            # The agent instance is reused, so it remembers previous turns
            response = self.agent.run(question)
        except Exception as e:
            logger.error(f"Agent failed to generate answer: {e}")
            return f"Error: {str(e)}"
        
        self._last_request_time = time.monotonic()
        response_text = str(response)

        if save_transcript and self.transcript_root:
            self._save_transcript(question, response_text)

        elapsed = time.monotonic() - start_time
        logger.info(f"Answered in {elapsed:.2f}s")
        
        return response_text

    def clear_memory(self) -> None:
        """Resets the agent's conversation history."""
        logger.info("Clearing chat history.")
        self.agent = self._build_agent()

    def _build_agent(self) -> ToolCallingAgent:
        tools = build_knowledge_base_reader_tools(
            knowledge_base_root=str(self.knowledge_base_root)
        )
        return ToolCallingAgent(
            name="knowledge_base_chat",
            description="Answers questions by reading knowledge base markdown files.",
            tools=tools,
            model=self.model,
            instructions=prompts.KB_CHAT_AGENT_PROMPT,
        )

    def _save_transcript(self, question: str, answer: str) -> None:
        """Saves the interaction to a timestamped file."""
        if not self.transcript_root:
            return
            
        timestamp = int(time.time())
        # Use a short hash or safe filename to prevent overwrites
        safe_q = "".join(c for c in question[:20] if c.isalnum() or c == " ").strip().replace(" ", "_")
        transcript_path = self.transcript_root / f"chat_{timestamp}_{safe_q}.md"
        
        transcript_content = (
            f"# Knowledge Base Chat Interaction\n\n"
            f"**Time:** {time.ctime()}\n\n"
            f"## Question\n{question.strip()}\n\n"
            f"## Answer\n{answer}\n"
        )
        
        try:
            transcript_path.write_text(transcript_content, encoding="utf-8")
            logger.info("Saved transcript to {}", transcript_path.name)
        except Exception as e:
            logger.warning(f"Failed to save transcript: {e}")

    def _respect_rate_limit(self) -> None:
        """Sleeps only if the previous request was too recent."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            wait_time = self._min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {wait_time:.2f}s")
            time.sleep(wait_time)


__all__ = ["KnowledgeBaseChat"]