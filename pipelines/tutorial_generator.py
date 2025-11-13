"""Generate tutorial markdown files from the knowledge base."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, cast

from dotenv import load_dotenv
from loguru import logger
from smolagents import LiteLLMModel
from smolagents.agents import ToolCallingAgent
from smolagents.utils import AgentGenerationError
from smolagents.models import ChatMessage, MessageRole

from prompts import prompts
from pipelines.tutorial_site_builder import TutorialSiteBuilder
from toolkits.tutorial_toolkit import build_tutorial_tools
from utils.path_utils import ensure_directory

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
KNOWLEDGE_BASE_OUTPUT_PATH = os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
TUTORIAL_OUTPUT_PATH = os.getenv("TUTORIAL_OUTPUT_PATH")
DEFAULT_REQUESTS_PER_MINUTE = 9.0
DEFAULT_AGENT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 10.0
STRICT_TOOL_CALL_REMINDER = (
    "\n\nSTRICT TOOL-CALL FORMAT REMINDER:\n"
    "- Every tool interaction must be through the provided tools (especially write_tutorial_file).\n"
    "- Do not emit narration or markdown unless a tool explicitly writes it.\n"
    '- When invoking a tool, respond with ONLY the JSON arguments (e.g., {"file_path": "docs/guide.md", "content": "..."}).\n'
    "- Do not wrap JSON in backticks or add commentary before/after tool calls."
)

TUTORIAL_ENABLE_CODE_SEARCH_ENV = "TUTORIAL_ENABLE_CODE_SEARCH"
TUTORIAL_ENABLE_RAG_ENV = "TUTORIAL_ENABLE_RAG"
TUTORIAL_RAG_MAX_SNIPPETS_ENV = "TUTORIAL_RAG_MAX_SNIPPETS"
DEFAULT_RAG_MAX_SNIPPETS = 5


@dataclass(frozen=True)
class TutorialOutlineItem:
    filename: str
    title: str
    description: str


DEFAULT_OUTLINE: Sequence[TutorialOutlineItem] = (
    TutorialOutlineItem(
        filename="01_getting_started.md",
        title="Getting Started",
        description="Design an onboarding experience that surfaces the repository's most important entry points.",
    ),
    TutorialOutlineItem(
        filename="02_architecture_overview.md",
        title="Architecture Overview",
        description="Explain how the architecture hangs together, emphasizing flows that are distinctive to this codebase.",
    ),
    TutorialOutlineItem(
        filename="03_working_with_api.md",
        title="Working with the API",
        description="Spotlight the most impactful interfaces or workflows collaborators will rely on when interacting with the system.",
    ),
    TutorialOutlineItem(
        filename="04_extending_the_system.md",
        title="Extending the System",
        description="Guide contributors on extending the project by reflecting its real conventions, testing expectations, and tooling.",
    ),
)

TUTORIAL_TEMPLATE_HEADINGS: Sequence[str] = (
    "## Overview",
    "## Learning Objectives",
    "## Prerequisites",
    "## Knowledge Base Links",
    "## Guided Walkthrough",
    "## Practice & Reflection",
    "## Design Pattern Spotlight",
    "## Next Steps",
)

OPTIONAL_DIAGRAM_HEADING = "## Diagram"
DIAGRAM_HEADINGS: tuple[str, ...] = (OPTIONAL_DIAGRAM_HEADING, "## Diagrams")

MIN_DYNAMIC_TUTORIALS = 3
MAX_DYNAMIC_TUTORIALS = 6


def _slugify(value: str) -> str:
    ascii_only = value.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_only).strip("_")
    return slug or "tutorial"


def _title_from_filename(stem: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", stem).strip()
    if not cleaned:
        return stem.title() or "Untitled"
    words = [word.capitalize() for word in cleaned.split() if word]
    return " ".join(words) if words else stem.title()


def _require_env(var_name: str, value: Optional[str]) -> str:
    if not value:
        raise RuntimeError(f"{var_name} must be configured.")
    return value


def _build_outline_text(items: Sequence[TutorialOutlineItem]) -> str:
    lines = [
        "Tutorial outline scaffold (adapt the emphasis, examples, and depth to match this repository):"
    ]
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
        enable_code_search: bool | None = None,
        enable_rag: bool | None = None,
        rag_max_snippets: int | None = None,
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
        self._outline_override = tuple(outline) if outline else None
        self.outline: Sequence[TutorialOutlineItem] | None = None

        self.enable_code_search = self._resolve_bool_option(
            enable_code_search,
            TUTORIAL_ENABLE_CODE_SEARCH_ENV,
            default=False,
        )
        self.enable_rag = self._resolve_bool_option(
            enable_rag,
            TUTORIAL_ENABLE_RAG_ENV,
            default=False,
        )
        self.rag_max_snippets = self._resolve_int_option(
            rag_max_snippets,
            TUTORIAL_RAG_MAX_SNIPPETS_ENV,
            default=DEFAULT_RAG_MAX_SNIPPETS,
            minimum=1,
        )

        requests_per_minute = self._resolve_requests_per_minute()
        self._min_interval = 60.0 / requests_per_minute
        self._max_retries = self._resolve_retry_attempts()
        self._retry_backoff_seconds = self._resolve_retry_backoff()
        self.model = LiteLLMModel(
            model_id=model_id,
            api_key=api_key,
            requests_per_minute=requests_per_minute,
        )

    def generate(self) -> List[Path]:
        if not self.knowledge_base_root.exists():
            raise FileNotFoundError(
                f"Knowledge base directory not found: {self.knowledge_base_root}. Generate it before tutorials."
            )

        tutorial_state: Dict[str, Any] = {}
        prepared = self._prepare_tutorial_state(tutorial_state)

        outline = prepared.get("outline")
        tools = prepared.get("tools")
        kb_summary = prepared.get("kb_summary", "")
        template_guidance = prepared.get("template_guidance", "")
        outline_brief = prepared.get("outline_brief", "")

        if outline is None or tools is None:
            raise RuntimeError(
                "Tutorial preparation failed to supply outline or tools."
            )

        tutorial_paths = self._render_tutorials(
            outline=outline,
            tools=tools,
            kb_summary=kb_summary,
            template_guidance=template_guidance,
            outline_brief=outline_brief,
        )

        if not tutorial_paths:
            raise RuntimeError("Tutorial generation produced no markdown files.")

        finalized_paths = self._finalize_outputs(tutorial_paths)

        logger.info(
            "Tutorial generation completed with {} files",
            len(finalized_paths),
        )
        return finalized_paths

    def _summarize_knowledge_base(self, max_entries: int = 30) -> str:
        entries = sorted(self.knowledge_base_root.glob("*.md"))
        if not entries:
            return "No knowledge base markdown files found."
        lines = ["Available knowledge base files:"]
        for entry in entries[:max_entries]:
            lines.append(f"- {entry.name}")
        remaining = len(entries) - max_entries
        if remaining > 0:
            lines.append(f"- … plus {remaining} additional file(s) not listed here")
        toc_path = self.knowledge_base_root / "toc.md"
        if toc_path.exists():
            lines.append("toc.md is available for cross references.")
        return "\n".join(lines)

    def _prepare_tutorial_state(self, base_state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Preparing tutorial output directory at {}", self.output_root)
        self._reset_directory(self.output_root)

        tools = build_tutorial_tools(
            codebase_root=str(self.codebase_root),
            knowledge_base_root=str(self.knowledge_base_root),
            tutorial_output_root=str(self.output_root),
            enable_code_search=self.enable_code_search,
            enable_rag=self.enable_rag,
            rag_max_snippets=self.rag_max_snippets,
        )

        kb_summary = self._summarize_knowledge_base()
        outline = self._resolve_outline(kb_summary)
        self.outline = outline
        template_guidance = self._build_template_guidance()
        outline_brief = self._build_outline_brief(outline)

        logger.info(
            "Prepared tutorial generation context for %d outline entries",
            len(outline),
        )

        prepared = {
            "kb_summary": kb_summary,
            "outline": outline,
            "tools": tools,
            "template_guidance": template_guidance,
            "outline_brief": outline_brief,
            "feature_flags": {
                "code_search": self.enable_code_search,
                "rag": self.enable_rag,
                "rag_max_snippets": self.rag_max_snippets,
            },
        }
        base_state.update(prepared)
        return prepared

    def _render_tutorials(
        self,
        *,
        outline: Sequence[TutorialOutlineItem],
        tools: Sequence[Any],
        kb_summary: str,
        template_guidance: str,
        outline_brief: str,
    ) -> List[Path]:
        if not isinstance(outline, Sequence):
            raise TypeError(
                "Outline must be a sequence of TutorialOutlineItem instances."
            )

        tutorial_paths: List[Path] = []

        for item in outline:
            if not isinstance(item, TutorialOutlineItem):
                raise TypeError("Outline entries must be TutorialOutlineItem objects.")

            def _agent_factory(instructions: str) -> ToolCallingAgent:
                return ToolCallingAgent(
                    name=f"tutorial_generator_{_slugify(item.title)}",
                    description=f"Generates the tutorial '{item.title}'.",
                    tools=list(tools),
                    model=self.model,
                    instructions=instructions,
                )

            task = self._build_tutorial_task(
                item,
                kb_summary=kb_summary,
                template_guidance=template_guidance,
                outline_brief=outline_brief,
            )

            logger.info(
                "Generating tutorial '%s' with target file %s",
                item.title,
                item.filename,
            )
            self._run_agent_with_retries(
                _agent_factory,
                task,
                prompts.TUTORIAL_AGENT_PROMPT,
            )

            produced_path = self.output_root / item.filename
            if produced_path.exists():
                tutorial_paths.append(produced_path)
            else:
                logger.warning(
                    "Expected tutorial output %s was not created by the agent.",
                    produced_path,
                )

        return sorted(tutorial_paths)

    @staticmethod
    def _build_outline_brief(items: Sequence[TutorialOutlineItem]) -> str:
        if not items:
            return "(outline empty)"
        lines = ["Planned tutorials:"]
        for item in items:
            lines.append(f"- {item.filename}: {item.title}")
        return "\n".join(lines)

    def _build_tutorial_task(
        self,
        item: TutorialOutlineItem,
        *,
        kb_summary: str,
        template_guidance: str,
        outline_brief: str,
    ) -> str:
        return (
            f"Create a single tutorial markdown file named '{item.filename}' using the write_tutorial_file tool.\n"
            f"Focus on the topic '{item.title}'.\n"
            f"Tutorial goal: {item.description}\n\n"
            f"Context of other tutorials:\n{outline_brief}\n\n"
            f"Follow the mandatory section template:\n{template_guidance}\n\n"
            f"Relevant knowledge base files:\n{kb_summary}\n\n"
            "Cite knowledge base filenames in the Knowledge Base Links section. Keep narration specific to this repository and avoid generic boilerplate."
            f"{self._optional_tool_guidance()}"
        )

    def _run_agent_with_retries(
        self,
        agent_factory: Callable[[str], ToolCallingAgent],
        task: str,
        base_instructions: str,
    ) -> None:
        instructions = base_instructions
        agent = agent_factory(instructions)
        last_error: AgentGenerationError | None = None
        for attempt in range(1, self._max_retries + 1):
            step_start = time.monotonic()
            self._respect_rate_limit()
            try:
                agent.run(task)
                last_error = None
                elapsed = time.monotonic() - step_start
                self._enforce_min_step_duration(elapsed)
                break
            except AgentGenerationError as error:
                last_error = error
                elapsed = time.monotonic() - step_start
                self._enforce_min_step_duration(elapsed)

                message = str(error)
                parse_error = (
                    "Message contains no content" in message
                    or "Message contains no tool calls" in message
                )
                if parse_error:
                    if STRICT_TOOL_CALL_REMINDER not in instructions:
                        instructions = base_instructions + STRICT_TOOL_CALL_REMINDER
                        logger.warning(
                            "Tutorial agent output malformed; reinforcing tool-call instructions and retrying.",
                        )
                        agent = agent_factory(instructions)
                        continue
                    logger.warning(
                        "Tutorial agent still returning malformed output after reinforcement: %s",
                        message,
                    )

                if attempt >= self._max_retries:
                    logger.error(
                        "Tutorial agent failed after {} attempts", self._max_retries
                    )
                    break
                wait_seconds = self._retry_backoff_seconds * attempt
                logger.warning(
                    "Tutorial agent attempt {}/{} failed: {}. Retrying in {:.1f}s",
                    attempt,
                    self._max_retries,
                    error,
                    wait_seconds,
                )
                time.sleep(wait_seconds)

        if last_error is not None:
            raise last_error

    def _enforce_min_step_duration(self, elapsed: float) -> None:
        minimum = max(self._min_interval, 6.0)
        if elapsed >= minimum:
            return
        remaining = minimum - elapsed
        time.sleep(remaining)

    def _finalize_outputs(self, tutorial_paths: Iterable[Path]) -> List[Path]:
        paths = list(tutorial_paths)
        if not paths:
            raise RuntimeError("No tutorial outputs to finalize.")
        self._sanitize_tutorial_outputs(paths)
        self._validate_tutorials(paths)
        self._build_html_site(paths)
        return paths

    def _resolve_outline(self, kb_summary: str) -> Sequence[TutorialOutlineItem]:
        if self._outline_override is not None:
            logger.info(
                "Using user-provided tutorial outline with %d entries",
                len(self._outline_override),
            )
            return self._outline_override

        dynamic_outline = self._generate_dynamic_outline(kb_summary)
        if dynamic_outline:
            logger.info(
                "Generated dynamic tutorial outline with %d entries",
                len(dynamic_outline),
            )
            return dynamic_outline

        heuristic_outline = self._build_outline_from_knowledge_base()
        if heuristic_outline:
            logger.warning(
                "Using knowledge-base derived outline with %d entries",
                len(heuristic_outline),
            )
            return heuristic_outline

        logger.warning(
            "Falling back to default tutorial outline with %d entries",
            len(DEFAULT_OUTLINE),
        )
        return DEFAULT_OUTLINE

    def _generate_dynamic_outline(
        self, kb_summary: str
    ) -> Sequence[TutorialOutlineItem]:
        system_prompt = (
            "You are a senior technical educator designing hands-on tutorials for a repository. "
            "Craft an outline that feels specific to the project while staying teacherly and approachable. "
            "Return a raw JSON array (no markdown fences, no commentary) where each item has keys 'filename', 'title', and 'description'. "
            f"Produce between {MIN_DYNAMIC_TUTORIALS} and {MAX_DYNAMIC_TUTORIALS} tutorials. "
            "Keep descriptions to one or two sentences highlighting distinctive aspects of the codebase. "
            "Filenames must be zero-padded (e.g., 01_intro.md) and reflect the topic."
        )

        repo_name = self.codebase_root.name
        user_prompt = (
            f"Repository name: {repo_name}\n"
            "Use the knowledge base summary to infer which concepts deserve focused tutorials.\n\n"
            f"Knowledge base summary:\n{kb_summary}\n\n"
            "Only respond with the JSON array."
        )

        messages: list[dict[str, Any]] = [
            {"role": MessageRole.SYSTEM.value, "content": system_prompt},
            {"role": MessageRole.USER.value, "content": user_prompt},
        ]

        try:
            response = self.model.generate(messages=cast(List[Any], messages))
        except Exception as error:  # pragma: no cover - defensive logging
            logger.warning("Dynamic outline generation failed: %s", error)
            return ()

        outline_text = self._message_content_to_text(response)

        payload: Any | None = None
        for candidate in self._candidate_json_strings(outline_text):
            try:
                payload = json.loads(candidate)
                if candidate != outline_text:
                    logger.debug(
                        "Dynamic outline response required sanitization before parsing: %r",
                        candidate,
                    )
                break
            except json.JSONDecodeError:
                continue

        if payload is None:
            logger.warning(
                "Dynamic outline JSON parsing failed: unable to extract JSON | content=%r",
                outline_text,
            )
            return ()

        items = self._coerce_outline_items(payload)
        if len(items) < MIN_DYNAMIC_TUTORIALS:
            logger.warning(
                "Dynamic outline only produced %d item(s); need at least %d.",
                len(items),
                MIN_DYNAMIC_TUTORIALS,
            )
            return ()

        if len(items) > MAX_DYNAMIC_TUTORIALS:
            items = items[:MAX_DYNAMIC_TUTORIALS]
        return tuple(items)

    def _build_outline_from_knowledge_base(self) -> Sequence[TutorialOutlineItem]:
        docs = [
            path
            for path in sorted(self.knowledge_base_root.glob("*.md"))
            if path.name.lower() != "toc.md"
        ]

        if len(docs) < MIN_DYNAMIC_TUTORIALS:
            return ()

        items: list[TutorialOutlineItem] = []
        for index, doc in enumerate(docs[:MAX_DYNAMIC_TUTORIALS], start=1):
            stem = doc.stem
            title = _title_from_filename(stem)
            description = (
                f"Ground the tutorial in insights from '{doc.name}' and related code sections,"
                " highlighting why they matter for new contributors."
            )
            filename = f"{index:02d}_{_slugify(title)}.md"
            items.append(
                TutorialOutlineItem(
                    filename=filename,
                    title=title,
                    description=description,
                )
            )

        return tuple(items)

    @staticmethod
    def _message_content_to_text(message: ChatMessage) -> str:
        content = message.content
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        parts: list[str] = []
        for chunk in content:
            if isinstance(chunk, dict):
                text_value = chunk.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
        return "".join(parts)

    @staticmethod
    def _candidate_json_strings(raw_text: str) -> list[str]:
        candidates: list[str] = []
        stripped = raw_text.strip()
        if stripped:
            candidates.append(stripped)

        for match in re.finditer(r"```(?:json)?\s*(.*?)```", raw_text, re.DOTALL):
            snippet = match.group(1).strip()
            if snippet:
                candidates.append(snippet)

        start = raw_text.find("[")
        end = raw_text.rfind("]")
        if 0 <= start < end:
            snippet = raw_text[start : end + 1].strip()
            if snippet:
                candidates.append(snippet)

        unique: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                unique.append(candidate)
        return unique

    def _coerce_outline_items(self, payload: Any) -> list[TutorialOutlineItem]:
        if not isinstance(payload, list):
            return []

        items: list[TutorialOutlineItem] = []
        seen_filenames: set[str] = set()
        for index, entry in enumerate(payload, start=1):
            if not isinstance(entry, dict):
                continue

            raw_title = entry.get("title")
            raw_description = entry.get("description")
            if not isinstance(raw_title, str) or not isinstance(raw_description, str):
                continue

            title = raw_title.strip()
            description = raw_description.strip()
            if not title or not description:
                continue

            raw_filename = entry.get("filename")
            filename = raw_filename.strip() if isinstance(raw_filename, str) else ""
            if not filename:
                filename = f"{index:02d}_{_slugify(title)}.md"
            else:
                normalized = filename.replace(" ", "_")
                if not normalized.lower().endswith(".md"):
                    normalized = f"{normalized}.md"
                filename = normalized.lower()

            if filename in seen_filenames:
                base = filename[:-3] if filename.endswith(".md") else filename
                suffix = 1
                while f"{base}_{suffix:02d}.md" in seen_filenames:
                    suffix += 1
                filename = f"{base}_{suffix:02d}.md"

            seen_filenames.add(filename)
            items.append(
                TutorialOutlineItem(
                    filename=filename,
                    title=title,
                    description=description,
                )
            )

        return items

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

    def _respect_rate_limit(self) -> None:
        time.sleep(self._min_interval)

    def _resolve_requests_per_minute(self) -> float:
        raw_value = os.getenv("LITELLM_REQUESTS_PER_MINUTE")
        if raw_value is None:
            return DEFAULT_REQUESTS_PER_MINUTE
        try:
            parsed = float(raw_value)
        except ValueError:
            logger.warning(
                "Invalid LITELLM_REQUESTS_PER_MINUTE value '%s'; using default %.1f",
                raw_value,
                DEFAULT_REQUESTS_PER_MINUTE,
            )
            return DEFAULT_REQUESTS_PER_MINUTE
        if parsed <= 0:
            logger.warning(
                "Non-positive LITELLM_REQUESTS_PER_MINUTE value '%s'; using default %.1f",
                raw_value,
                DEFAULT_REQUESTS_PER_MINUTE,
            )
            return DEFAULT_REQUESTS_PER_MINUTE
        return parsed

    def _resolve_retry_attempts(self) -> int:
        raw_value = os.getenv("TUTORIAL_AGENT_MAX_RETRIES")
        if raw_value is None:
            return DEFAULT_AGENT_MAX_RETRIES
        try:
            parsed = int(raw_value)
        except ValueError:
            logger.warning(
                "Invalid TUTORIAL_AGENT_MAX_RETRIES value '%s'; using default %d",
                raw_value,
                DEFAULT_AGENT_MAX_RETRIES,
            )
            return DEFAULT_AGENT_MAX_RETRIES
        if parsed < 1:
            logger.warning(
                "Non-positive TUTORIAL_AGENT_MAX_RETRIES value '%s'; using default %d",
                raw_value,
                DEFAULT_AGENT_MAX_RETRIES,
            )
            return DEFAULT_AGENT_MAX_RETRIES
        return parsed

    def _resolve_retry_backoff(self) -> float:
        raw_value = os.getenv("TUTORIAL_AGENT_RETRY_BACKOFF_SECONDS")
        if raw_value is None:
            return DEFAULT_RETRY_BACKOFF_SECONDS
        try:
            parsed = float(raw_value)
        except ValueError:
            logger.warning(
                "Invalid TUTORIAL_AGENT_RETRY_BACKOFF_SECONDS value '%s'; using default %.1f",
                raw_value,
                DEFAULT_RETRY_BACKOFF_SECONDS,
            )
            return DEFAULT_RETRY_BACKOFF_SECONDS
        if parsed <= 0:
            logger.warning(
                "Non-positive TUTORIAL_AGENT_RETRY_BACKOFF_SECONDS value '%s'; using default %.1f",
                raw_value,
                DEFAULT_RETRY_BACKOFF_SECONDS,
            )
            return DEFAULT_RETRY_BACKOFF_SECONDS
        return parsed

    @staticmethod
    def _resolve_bool_option(
        override: bool | None, env_var: str, *, default: bool
    ) -> bool:
        if override is not None:
            return override

        raw_value = os.getenv(env_var)
        if raw_value is None:
            return default

        normalized = raw_value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False

        logger.warning(
            "Unrecognized boolean value '%s' for %s; using default %s",
            raw_value,
            env_var,
            default,
        )
        return default

    @staticmethod
    def _resolve_int_option(
        override: int | None,
        env_var: str,
        *,
        default: int,
        minimum: int = 1,
    ) -> int:
        baseline = max(minimum, default)
        if override is not None:
            return max(minimum, override)

        raw_value = os.getenv(env_var)
        if raw_value is None:
            return baseline

        try:
            parsed = int(raw_value)
        except ValueError:
            logger.warning(
                "Invalid integer value '%s' for %s; using default %d",
                raw_value,
                env_var,
                baseline,
            )
            return baseline

        if parsed < minimum:
            logger.warning(
                "%s value '%s' below minimum %d; using %d",
                env_var,
                raw_value,
                minimum,
                minimum,
            )
            return minimum

        return parsed

    def _optional_tool_guidance(self) -> str:
        hints: list[str] = []
        if self.enable_code_search:
            hints.append(
                "Use `grep_codebase` to locate APIs or patterns across the repository when you need additional code excerpts."
            )
        if self.enable_rag:
            hints.append(
                "Call `retrieve_relevant_context` to pull supporting snippets from the knowledge base or source files when clarification is needed."
            )
        if not hints:
            return ""

        lines = ["", "", "Optional helper tools available:"]
        lines.extend(f"- {hint}" for hint in hints)
        return "\n".join(lines)

    def _build_template_guidance(self) -> str:
        lines = [
            "Follow this section order for every tutorial:",
            "- # <Title from the outline>",
        ]
        lines.extend(f"- {heading}" for heading in TUTORIAL_TEMPLATE_HEADINGS)
        lines.append(
            f"- Optionally include '{OPTIONAL_DIAGRAM_HEADING}' immediately after code examples when you add a Mermaid diagram."
        )
        lines.append(
            "Include content under each heading; never remove or rename these sections."
        )
        return "\n".join(lines)

    def _validate_tutorials(self, tutorial_paths: Iterable[Path]) -> None:
        for path in tutorial_paths:
            content = path.read_text(encoding="utf-8")
            errors: List[str] = []

            stripped = content.lstrip()
            if not stripped.startswith("# "):
                errors.append("missing top-level title starting with '# '")

            for heading in TUTORIAL_TEMPLATE_HEADINGS:
                if heading not in content:
                    errors.append(f"missing heading '{heading}'")

            for diagram_heading in DIAGRAM_HEADINGS:
                if diagram_heading in content:
                    section_start = content.index(diagram_heading)
                    remainder = content[section_start + len(diagram_heading) :]
                    next_heading_index = remainder.find("\n## ")
                    section_body = (
                        remainder
                        if next_heading_index == -1
                        else remainder[:next_heading_index]
                    )
                    if "```mermaid" not in section_body:
                        errors.append(
                            "diagram heading present without a Mermaid diagram"
                        )
                    break

            if errors:
                raise RuntimeError(
                    f"Tutorial '{path.name}' failed template validation: {', '.join(errors)}"
                )

    def _sanitize_tutorial_outputs(self, tutorial_paths: Iterable[Path]) -> None:
        for path in tutorial_paths:
            content = path.read_text(encoding="utf-8")
            sanitized = self._sanitize_mermaid_blocks(content)
            sanitized = self._remove_empty_diagram_sections(sanitized)
            if sanitized != content:
                logger.debug("Sanitized Mermaid content in %s", path)
                path.write_text(sanitized, encoding="utf-8")

    def _build_html_site(self, tutorial_paths: Iterable[Path]) -> None:
        tutorials = list(tutorial_paths)
        if not tutorials:
            return
        try:
            TutorialSiteBuilder(self.output_root).build()
        except Exception as error:  # pragma: no cover - defensive logging
            logger.warning("Skipping tutorial site generation: %s", error)

    def _remove_empty_diagram_sections(self, content: str) -> str:
        pattern = re.compile(
            r"(^|\n)(## Diagram(?:s)?\s*\n)(.*?)(?=\n## |\Z)",
            re.DOTALL,
        )

        def _replacer(match: re.Match[str]) -> str:
            leading = match.group(1)
            heading = match.group(2)
            body = match.group(3)
            if "```mermaid" in body:
                return f"{leading}{heading}{body}"
            return leading if leading else ""

        cleaned = pattern.sub(_replacer, content)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned

    def _sanitize_mermaid_blocks(self, content: str) -> str:
        mermaid_pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)

        def sanitize_block(match: re.Match[str]) -> str:
            block = match.group(1)
            lines = block.splitlines()
            sanitized_lines: list[str] = []
            for line in lines:
                sanitized_lines.append(self._sanitize_mermaid_line(line))
            sanitized_block = "\n".join(sanitized_lines)
            return f"```mermaid\n{sanitized_block}\n```"

        return mermaid_pattern.sub(sanitize_block, content)

    @staticmethod
    def _sanitize_mermaid_line(line: str) -> str:
        stripped_line = line.rstrip()
        indent = stripped_line[: len(stripped_line) - len(stripped_line.lstrip())]
        core = stripped_line[len(indent) :]

        while core.endswith(";"):
            core = core[:-1].rstrip()

        core = re.sub(r"\{([^{}\n]*)\}", r"[\1]", core)
        subgraph_match = re.match(r"(subgraph\s+)(.+)", core, flags=re.IGNORECASE)
        if subgraph_match:
            prefix, name = subgraph_match.groups()
            name = name.strip()
            if not (name.startswith('"') and name.endswith('"')):
                core = f'{prefix}"{name}"'
            else:
                core = f"{prefix}{name}"

        def _quote_node_labels(line: str) -> str:
            node_pattern = re.compile(r"(?P<id>\b[\w]+)\[(?P<label>[^\]]+)\]")

            def _repl(match: re.Match[str]) -> str:
                node_id = match.group("id")
                label = match.group("label")
                cleaned = label.strip()
                if cleaned.startswith('"') and cleaned.endswith('"'):
                    return f"{node_id}[{cleaned}]"
                if re.search(r"[()/:]", cleaned):
                    return f'{node_id}["{cleaned}"]'
                return f"{node_id}[{cleaned}]"

            return node_pattern.sub(_repl, line)

        core = _quote_node_labels(core)

        edge_match = re.match(
            r"^(?P<lhs>[^-].*?)--(?P<label>[^|][^-]*?)-->(?P<rhs>.*)$",
            core,
        )
        if edge_match:
            lhs = edge_match.group("lhs").rstrip()
            label = edge_match.group("label").strip()
            rhs = edge_match.group("rhs").lstrip()
            if label:
                core = f"{lhs} --|{label}|--> {rhs}"
            else:
                core = f"{lhs} --> {rhs}"

        return f"{indent}{core}" if core else line


__all__ = ["TutorialGenerator", "TutorialOutlineItem", "DEFAULT_OUTLINE"]
