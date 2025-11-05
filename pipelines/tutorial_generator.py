"""Generate tutorial markdown files from the knowledge base."""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from dotenv import load_dotenv
from loguru import logger
from smolagents import LiteLLMModel
from smolagents.agents import ToolCallingAgent

from prompts import prompts
from toolkits.tutorial_toolkit import build_tutorial_tools
from utils.path_utils import ensure_directory

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
KNOWLEDGE_BASE_OUTPUT_PATH = os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
TUTORIAL_OUTPUT_PATH = os.getenv("TUTORIAL_OUTPUT_PATH")


@dataclass(frozen=True)
class TutorialOutlineItem:
    filename: str
    title: str
    description: str


DEFAULT_OUTLINE: Sequence[TutorialOutlineItem] = (
    TutorialOutlineItem(
        filename="01_getting_started.md",
        title="Getting Started",
        description="Introduce the project, installation, configuration, and how to run the main entry point.",
    ),
    TutorialOutlineItem(
        filename="02_architecture_overview.md",
        title="Architecture Overview",
        description="Explain the system architecture, major modules, and data flow diagrams.",
    ),
    TutorialOutlineItem(
        filename="03_working_with_api.md",
        title="Working with the API",
        description="Walk through the API layer, key endpoints, authentication, and example requests.",
    ),
    TutorialOutlineItem(
        filename="04_extending_the_system.md",
        title="Extending the System",
        description="Show how to add new features, tests, and follow best practices for contributions.",
    ),
)


def _require_env(var_name: str, value: Optional[str]) -> str:
    if not value:
        raise RuntimeError(f"{var_name} must be configured.")
    return value


def _build_outline_text(items: Sequence[TutorialOutlineItem]) -> str:
    lines = ["Tutorial outline:"]
    for item in items:
        lines.append(f"- {item.filename}: {item.title} — {item.description}")
    return "\n".join(lines)


class TutorialGenerator:
    def __init__(
        self,
        *,
        codebase_root: str | Path | None = None,
        knowledge_base_root: str | Path | None = None,
        output_root: str | Path | None = None,
        outline: Sequence[TutorialOutlineItem] | None = None,
    ) -> None:
        model_id = _require_env("LITELLM_MODEL_ID", LITELLM_MODEL_ID)
        api_key = _require_env("LITELLM_API_KEY", LITELLM_API_KEY)

        self.codebase_root = (
            Path(
                codebase_root or _require_env("CODEBASE_ROOT_PATH", CODEBASE_ROOT_PATH)
            )
            .expanduser()
            .resolve()
        )
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
        self.output_root = ensure_directory(
            output_root or _require_env("TUTORIAL_OUTPUT_PATH", TUTORIAL_OUTPUT_PATH)
        )
        self.outline = tuple(outline) if outline else tuple(DEFAULT_OUTLINE)

        self.model = LiteLLMModel(model_id=model_id, api_key=api_key)

    def generate(self) -> List[Path]:
        if not self.knowledge_base_root.exists():
            raise FileNotFoundError(
                f"Knowledge base directory not found: {self.knowledge_base_root}. Generate it before tutorials."
            )

        logger.info("Preparing tutorial output directory at %s", self.output_root)
        self._reset_directory(self.output_root)

        tools = build_tutorial_tools(
            codebase_root=str(self.codebase_root),
            knowledge_base_root=str(self.knowledge_base_root),
            tutorial_output_root=str(self.output_root),
        )

        agent = ToolCallingAgent(
            name="tutorial_generator",
            description="Generates beginner-friendly tutorials using the knowledge base and code snippets.",
            tools=tools,
            model=self.model,
            instructions=prompts.TUTORIAL_AGENT_PROMPT,
        )

        outline_text = _build_outline_text(self.outline)
        kb_summary = self._summarize_knowledge_base()
        task = (
            f"Use the knowledge base to create the tutorials described below. "
            f"Write one markdown file per entry using write_tutorial_file.\n\n"
            f"{outline_text}\n\nKnowledge base summary:\n{kb_summary}\n"
            "Ensure each tutorial references the knowledge base sections it draws from and includes at least one Mermaid diagram if applicable."
        )

        logger.info(
            "Running tutorial generator agent with outline of %s files",
            len(self.outline),
        )
        self._respect_rate_limit()
        agent.run(task)

        generated = sorted(self.output_root.glob("*.md"))
        logger.info("Tutorial generation completed with %s files", len(generated))
        return generated

    def _summarize_knowledge_base(self) -> str:
        entries = sorted(self.knowledge_base_root.glob("*.md"))
        if not entries:
            return "No knowledge base markdown files found."
        lines = ["Available knowledge base files:"]
        for entry in entries:
            lines.append(f"- {entry.name}")
        toc_path = self.knowledge_base_root / "toc.md"
        if toc_path.exists():
            lines.append("toc.md is available for cross references.")
        return "\n".join(lines)

    @staticmethod
    def _reset_directory(path: Path) -> None:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            return
        for entry in path.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()

    @staticmethod
    def _respect_rate_limit(min_interval: float = 6.1) -> None:
        time.sleep(min_interval)


__all__ = ["TutorialGenerator", "TutorialOutlineItem", "DEFAULT_OUTLINE"]
