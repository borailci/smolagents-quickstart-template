"""Answer questions using the generated knowledge base."""

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
from toolkits.knowledge_base_reader_toolkit import build_knowledge_base_reader_tools
from utils.path_utils import ensure_directory

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
KNOWLEDGE_BASE_OUTPUT_PATH = os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
CHAT_TRANSCRIPTS_ROOT = os.getenv("CHAT_TRANSCRIPTS_ROOT")


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
        self.model_id = model_id
        self.api_key = api_key

    def answer(self, question: str, *, save_transcript: bool = False) -> str:
        if not question.strip():
            raise ValueError("Question must be a non-empty string.")

        agent = self._build_agent()
        self._respect_rate_limit()
        logger.info("Running knowledge base chat agent for question: {}", question)
        response = agent.run(question)
        response_text = str(response)

        if save_transcript and self.transcript_root:
            timestamp = int(time.time())
            transcript_path = self.transcript_root / f"chat_{timestamp}.md"
            transcript_content = (
                f"# Knowledge Base Chat\n\n"
                f"**Question:** {question.strip()}\n\n"
                f"**Answer:**\n\n{response_text}\n"
            )
            transcript_path.write_text(transcript_content, encoding="utf-8")
            logger.info("Saved transcript to {}", transcript_path)

        return response_text

    def _build_agent(self) -> ToolCallingAgent:
        tools = build_knowledge_base_reader_tools(
            knowledge_base_root=str(self.knowledge_base_root)
        )
        model = LiteLLMModel(model_id=self.model_id, api_key=self.api_key)
        return ToolCallingAgent(
            name="knowledge_base_chat",
            description="Answers questions by reading knowledge base markdown files.",
            tools=tools,
            model=model,
            instructions=prompts.KB_CHAT_AGENT_PROMPT,
        )

    @staticmethod
    def _respect_rate_limit(min_interval: float = 6.1) -> None:
        time.sleep(min_interval)


__all__ = ["KnowledgeBaseChat"]
