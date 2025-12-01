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
from toolkits.sub_agent_toolkit import (
    SubAgentRole,
    SubAgentTaskSpec,
    run_typed_sub_agent_tasks,
)
from toolkits.tutorial_toolkit import build_tutorial_tools
from utils.path_utils import ensure_directory

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
KNOWLEDGE_BASE_OUTPUT_PATH = os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
TUTORIAL_OUTPUT_PATH = os.getenv("TUTORIAL_OUTPUT_PATH")
SUB_AGENTS_ROOT_PATH = os.getenv("SUB_AGENTS_ROOT_PATH")
DEFAULT_REQUESTS_PER_MINUTE = 15.0 
DEFAULT_AGENT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 5.0

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


# NOTE: Default outline removed to force dynamic, project-specific generation.

_MIN_UNIQUE_SECOND_LEVEL_HEADINGS = 2
MIN_DYNAMIC_TUTORIALS = 3
MAX_DYNAMIC_TUTORIALS = 8  # Increased max slightly since the agent is in control


def _slugify(value: str) -> str:
    import unicodedata
    value = unicodedata.normalize("NFKD", value)
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


def _validate_tutorial_content(content: str, tutorial_path: Path) -> List[str]:
    """Validate tutorial content for quality requirements."""
    errors = []
    
    # Check 1: Duplicate headers
    headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
    if len(headers) != len(set(headers)):
        errors.append(f"{tutorial_path.name}: Contains duplicate headers")
    
    # Check 2: Empty/malformed code blocks
    code_blocks = re.findall(r'```[\s\S]*?```', content)
    for i, block in enumerate(code_blocks):
        lines = block.strip().split('\n')
        if len(lines) <= 2:
            errors.append(f"{tutorial_path.name}: Empty code block #{i+1}")
    
    # Check 3: Code blocks without language hints
    code_blocks_no_lang = re.findall(r'```\n', content)
    if code_blocks_no_lang:
        errors.append(f"{tutorial_path.name}: {len(code_blocks_no_lang)} blocks missing lang hints")
    
    # Check 4: Mermaid Diagrams
    mermaid_blocks = re.findall(r'```mermaid[\s\S]*?```', content, re.IGNORECASE)
    if not mermaid_blocks:
        errors.append(f"{tutorial_path.name}: ❌ MISSING REQUIRED Mermaid diagram")
    
    # Check 5: Generic code examples (print hello)
    if re.search(r'print\([\'"]Hello[\'"]', content, re.IGNORECASE):
        errors.append(f"{tutorial_path.name}: ⚠️  Contains generic 'Hello' example - use real code!")
    
    # Check 6: File paths with line numbers
    has_line_numbers = re.search(r'\(lines?\s+\d+', content, re.IGNORECASE)
    if not has_line_numbers:
        errors.append(f"{tutorial_path.name}: ⚠️  No file paths with line numbers found")
    
    # Check 7: Executable bash commands
    bash_blocks = re.findall(r'```bash[\s\S]*?```', content)
    if len(bash_blocks) < 1:
        errors.append(f"{tutorial_path.name}: ⚠️  Needs more bash command examples")

    # Check 8: Broken code strings (split across lines)
    if re.search(r'f"[\s\S]*?\n"', content):
        errors.append(f"{tutorial_path.name}: ❌ Broken f-string detected (newline before closing quote)")

    # Check 9: Mermaid syntax (nested parens)
    if re.search(r'\[.*?\(.*?\).*?\]', content):
        errors.append(f"{tutorial_path.name}: ⚠️  Potential Mermaid syntax error (nested parens in node label)")
    
    return errors


def _auto_fix_common_issues(content: str) -> str:
    """Automatically fix common tutorial quality issues without data loss."""
    lines = content.split('\n')
    fixed_lines = []
    seen_headers = set()
    
    for line in lines:
        if line.startswith('#'):
            if line in seen_headers and len(line) > 5:
                continue
            seen_headers.add(line)
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content


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
        dry_run: bool = False,
    ) -> None:
        model_id = _require_env("LITELLM_MODEL_ID", LITELLM_MODEL_ID)
        api_key = _require_env("LITELLM_API_KEY", LITELLM_API_KEY)

        self.dry_run = dry_run

        self.codebase_root = (
            Path(codebase_root or _require_env("CODEBASE_ROOT_PATH", CODEBASE_ROOT_PATH))
            .expanduser()
            .resolve()
        )
        self.knowledge_base_root = (
            Path(knowledge_base_root or _require_env("KNOWLEDGE_BASE_OUTPUT_PATH", KNOWLEDGE_BASE_OUTPUT_PATH))
            .expanduser()
            .resolve()
        )
        self.output_root = ensure_directory(
            output_root or _require_env("TUTORIAL_OUTPUT_PATH", TUTORIAL_OUTPUT_PATH)
        )
        
        if SUB_AGENTS_ROOT_PATH:
            polisher_root_base = Path(SUB_AGENTS_ROOT_PATH).expanduser().resolve() / "tutorial_polishers"
        else:
            polisher_root_base = self.output_root / "_polishers"
        self.polisher_root = ensure_directory(polisher_root_base)
        
        self._outline_override = tuple(outline) if outline else None
        self.outline: Sequence[TutorialOutlineItem] | None = None

        self.enable_code_search = self._resolve_bool_option(enable_code_search, TUTORIAL_ENABLE_CODE_SEARCH_ENV, default=False)
        self.enable_rag = self._resolve_bool_option(enable_rag, TUTORIAL_ENABLE_RAG_ENV, default=False)
        self.rag_max_snippets = self._resolve_int_option(rag_max_snippets, TUTORIAL_RAG_MAX_SNIPPETS_ENV, default=DEFAULT_RAG_MAX_SNIPPETS)

        requests_per_minute = self._resolve_requests_per_minute()
        self._min_interval = 60.0 / requests_per_minute
        self._last_request_time = 0.0
        
        self._max_retries = self._resolve_retry_attempts()
        self._retry_backoff_seconds = self._resolve_retry_backoff()
        
        self.model = LiteLLMModel(
            model_id=model_id,
            api_key=api_key,
            requests_per_minute=requests_per_minute,
        )

    def generate(self) -> List[Path]:
        if not self.knowledge_base_root.exists():
            raise FileNotFoundError(f"Knowledge base directory not found at {self.knowledge_base_root}.")

        tutorial_state: Dict[str, Any] = {}
        prepared = self._prepare_tutorial_state(tutorial_state)
        outline = prepared.get("outline")
        tools = prepared.get("tools")
        kb_summary = prepared.get("kb_summary", "")
        style_guidance = prepared.get("style_guidance", "")
        outline_brief = prepared.get("outline_brief", "")

        if not outline or not tools:
            raise RuntimeError("Tutorial preparation failed.")

        tutorial_paths = self._render_tutorials(
            outline=outline,
            tools=tools,
            kb_summary=kb_summary,
            style_guidance=style_guidance,
            outline_brief=outline_brief,
        )

        if not tutorial_paths:
            raise RuntimeError("No tutorials were generated.")

        if self.dry_run:
            logger.info("Dry run enabled; skipping finalization.")
            return tutorial_paths

        finalized_paths = self._finalize_outputs(tutorial_paths)
        logger.info("Tutorial generation completed with {} files", len(finalized_paths))
        return finalized_paths

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
        style_guidance = self._build_style_guidance()
        outline_brief = self._build_outline_brief(outline)

        prepared = {
            "kb_summary": kb_summary,
            "outline": outline,
            "tools": tools,
            "style_guidance": style_guidance,
            "outline_brief": outline_brief,
        }
        base_state.update(prepared)
        return prepared

    def _render_tutorials(
        self,
        *,
        outline: Sequence[TutorialOutlineItem],
        tools: Sequence[Any],
        kb_summary: str,
        style_guidance: str,
        outline_brief: str,
    ) -> List[Path]:
        tutorial_paths: List[Path] = []

        for item in outline:
            def _agent_factory(instructions: str) -> ToolCallingAgent:
                return ToolCallingAgent(
                    name=f"tutorial_generator_{_slugify(item.title)}",
                    description=f"Generates tutorial: {item.title}",
                    tools=list(tools),
                    model=self.model,
                    instructions=instructions,
                )

            task = self._build_tutorial_task(
                item,
                kb_summary=kb_summary,
                style_guidance=style_guidance,
                outline_brief=outline_brief,
            )

            logger.info("Generating tutorial '{}'...", item.title)
            self._run_agent_with_retries(_agent_factory, task, prompts.TUTORIAL_AGENT_PROMPT)

            produced_path = self.output_root / item.filename
            
            if self.dry_run:
                tutorial_paths.append(produced_path)
                continue

            if produced_path.exists():
                tutorial_paths.append(produced_path)
            else:
                logger.error("Agent claimed success but file {} was not created.", produced_path)

        return sorted(tutorial_paths)

    def _run_agent_with_retries(
        self,
        agent_factory: Callable[[str], ToolCallingAgent],
        task: str,
        base_instructions: str,
    ) -> None:
        instructions = base_instructions
        agent = agent_factory(instructions)
        last_error: Exception | None = None
        
        for attempt in range(1, self._max_retries + 1):
            self._respect_rate_limit()
            try:
                agent.run(task)
                self._record_request_timestamp()
                return
            except Exception as error:
                last_error = error
                self._record_request_timestamp()
                
                message = str(error)
                if "Message contains no content" in message:
                    if STRICT_TOOL_CALL_REMINDER not in instructions:
                        instructions += STRICT_TOOL_CALL_REMINDER
                        agent = agent_factory(instructions)
                        continue

                wait_seconds = self._retry_backoff_seconds * attempt
                if attempt < self._max_retries:
                    logger.warning(f"Attempt {attempt} failed: {error}. Waiting {wait_seconds}s...")
                    time.sleep(wait_seconds)

        if last_error:
            raise last_error

    def _respect_rate_limit(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

    def _record_request_timestamp(self) -> None:
        self._last_request_time = time.monotonic()

    def _finalize_outputs(self, tutorial_paths: Iterable[Path]) -> List[Path]:
        paths = list(tutorial_paths)
        
        self._auto_fix_tutorial_quality(paths)
        self._validate_and_report_tutorial_quality(paths)
        self._sanitize_tutorial_outputs(paths)
        self._run_tutorial_polishers(paths)
        self._sanitize_tutorial_outputs(paths)
        self._normalize_heading_tokens(paths)
        self._ensure_top_level_titles(paths)
        
        return paths

    def _run_tutorial_polishers(self, tutorial_paths: Iterable[Path]) -> None:
        tutorials = [path for path in tutorial_paths if path.exists()]
        if not tutorials:
            return

        logger.info("Running polishers for {} tutorials...", len(tutorials))
        self._reset_directory(self.polisher_root)

        specs = [
            SubAgentTaskSpec(
                description=self._build_polisher_task_description(path),
                role=SubAgentRole.ANALYZER,
                instructions=prompts.TUTORIAL_POLISHER_PROMPT,
            )
            for path in tutorials
        ]

        workspaces = run_typed_sub_agent_tasks(
            specs,
            codebase_root=self.output_root,
            sub_agents_root=self.polisher_root,
            role_prompts={SubAgentRole.ANALYZER: prompts.TUTORIAL_POLISHER_PROMPT},
        )

        for i, tutorial_path in enumerate(tutorials):
            if i >= len(workspaces): break
            
            workspace = workspaces[i]
            polished_file = workspace / tutorial_path.name
            
            if polished_file.exists() and polished_file.stat().st_size > 50:
                tutorial_path.write_text(polished_file.read_text("utf-8"), "utf-8")
                logger.info(f"Applied polish to {tutorial_path.name}")
            else:
                logger.warning(f"Polisher failed for {tutorial_path.name}, keeping original.")

    def _build_polisher_task_description(self, tutorial_path: Path) -> str:
        return (
            f"Review and polish the tutorial '{tutorial_path.name}'.\n"
            "1. Fix typos and grammar.\n"
            "2. Ensure all code blocks have language tags (e.g. ```python).\n"
            "3. Fix broken Markdown links.\n"
            "4. Write the FIXED content to your workspace with the SAME filename.\n"
        )

    def _summarize_knowledge_base(self, max_entries: int = 30) -> str:
        entries = sorted(self.knowledge_base_root.glob("*.md"))
        if not entries: return "No files."
        return "\n".join(f"- {e.name}" for e in entries[:max_entries])

    def _build_outline_brief(self, items: Sequence[TutorialOutlineItem]) -> str:
        return "\n".join(f"- {item.filename}: {item.title}" for item in items)

    def _build_tutorial_task(self, item: TutorialOutlineItem, *, kb_summary: str, style_guidance: str, outline_brief: str) -> str:
        return (
            f"Write a tutorial '{item.filename}' about '{item.title}'.\n"
            f"Goal: {item.description}\n"
            f"Reference these KB files if possible: {kb_summary}\n"
            f"Style: {style_guidance}\n"
            f"Full Outline Context: {outline_brief}\n"
            f"{self._optional_tool_guidance()}"
        )

    def _sanitize_mermaid_blocks(self, content: str) -> str:
        mermaid_pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
        def sanitize_block(match: re.Match[str]) -> str:
            block = match.group(1)
            lines = [self._sanitize_mermaid_line(line) for line in block.splitlines()]
            return f"```mermaid\n{'\n'.join(lines)}\n```"
        return mermaid_pattern.sub(sanitize_block, content)

    @staticmethod
    def _sanitize_mermaid_line(line: str) -> str:
        stripped = line.rstrip()
        indent = line[:len(line) - len(line.lstrip())]
        core = stripped.lstrip()
        if not core: return line
        return f"{indent}{core}"

    def _normalize_heading_tokens(self, tutorial_paths: Iterable[Path]) -> None:
        pattern = re.compile(r"^h(?P<level>[1-6])_(?P<body>.+?)h(?P=level)$", re.IGNORECASE)
        for path in tutorial_paths:
            original = path.read_text("utf-8")
            lines = []
            for line in original.splitlines():
                match = pattern.match(line.strip())
                if match:
                    level = int(match.group("level"))
                    body = match.group("body").replace("_", " ").title()
                    lines.append(f"{'#' * level} {body}")
                else:
                    lines.append(line)
            path.write_text("\n".join(lines) + "\n", "utf-8")

    def _auto_fix_tutorial_quality(self, paths: Iterable[Path]) -> None:
        for path in paths:
            c = path.read_text("utf-8")
            fixed = _auto_fix_common_issues(c)
            if fixed != c: path.write_text(fixed, "utf-8")

    def _validate_and_report_tutorial_quality(self, paths: Iterable[Path]) -> None:
        for path in paths:
            errors = _validate_tutorial_content(path.read_text("utf-8"), path)
            if errors: logger.warning(f"{path.name} issues: {errors}")

    def _ensure_top_level_titles(self, paths: Iterable[Path]) -> None:
        for path in paths:
            c = path.read_text("utf-8")
            if not c.strip().startswith("# "):
                title = _title_from_filename(path.stem)
                path.write_text(f"# {title}\n\n{c}", "utf-8")
    


    def _resolve_outline(self, kb_summary: str) -> Sequence[TutorialOutlineItem]:
        """
        Determines the tutorial plan.
        Strictly enforces AI generation to avoid 1:1 file mapping.
        """
        # Priority 1: User Override via CLI
        if self._outline_override:
            logger.info("Using user-provided outline override.")
            return self._outline_override

        # Priority 2: AI Planner (Dynamic)
        logger.info("Asking AI Planner to design the tutorial structure...")
        dynamic = self._generate_dynamic_outline(kb_summary)
        
        if dynamic:
            logger.info(f"AI Planner created {len(dynamic)} tutorials.")
            return dynamic
        
        # Priority 3: Hard Fail
        # We REMOVED the heuristic fallback here. 
        # If the AI fails, we do NOT want to auto-generate a tutorial for every file.
        raise RuntimeError(
            "The AI Planner failed to generate a valid outline JSON. "
            "Please check your API keys or try again. "
            "(Automatic 1:1 file mapping has been disabled to ensure quality)."
        )

    def _generate_dynamic_outline(self, kb_summary: str) -> Sequence[TutorialOutlineItem]:
        system_prompt = prompts.DYNAMIC_OUTLINE_SYSTEM_PROMPT.format(
            min_tutorials=MIN_DYNAMIC_TUTORIALS,
            max_tutorials=MAX_DYNAMIC_TUTORIALS,
        )

        repo_name = self.codebase_root.name
        user_prompt = prompts.DYNAMIC_OUTLINE_USER_PROMPT.format(
            repo_name=repo_name,
            kb_summary=kb_summary,
        )

        messages = [
            {"role": MessageRole.SYSTEM.value, "content": system_prompt},
            {"role": MessageRole.USER.value, "content": user_prompt},
        ]

        try:
            response = self.model.generate(messages=messages)
        except Exception as error:
            logger.warning("Dynamic outline generation failed: {}", error)
            return ()

        # Extract text from response
        outline_text = ""
        if response.content:
            if isinstance(response.content, str):
                outline_text = response.content
            elif isinstance(response.content, list):
                for chunk in response.content:
                     if isinstance(chunk, dict) and "text" in chunk:
                         outline_text += chunk["text"]

        # Parse JSON
        payload = None
        # Try raw
        try:
            payload = json.loads(outline_text)
        except json.JSONDecodeError:
            # Try finding regex blocks
            match = re.search(r"```(?:json)?\s*(.*?)```", outline_text, re.DOTALL)
            if match:
                try:
                    payload = json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    pass
            # Try finding raw array
            if not payload:
                start = outline_text.find("[")
                end = outline_text.rfind("]")
                if start >= 0 and end > start:
                    try:
                        payload = json.loads(outline_text[start:end+1])
                    except json.JSONDecodeError:
                        pass
        
        if not payload:
            logger.warning("Failed to parse JSON from outline response")
            return ()

        return tuple(self._coerce_outline_items(payload))

    def _coerce_outline_items(self, payload: Any) -> List[TutorialOutlineItem]:
        if not isinstance(payload, list): return []
        items = []
        for i, entry in enumerate(payload, 1):
            if not isinstance(entry, dict): continue
            title = entry.get("title", "").strip()
            desc = entry.get("description", "").strip()
            fname = entry.get("filename", "").strip()
            
            if not title or not desc: continue
            
            if not fname:
                fname = f"{i:02d}_{_slugify(title)}.md"
            elif not fname.endswith(".md"):
                fname += ".md"
            
            items.append(TutorialOutlineItem(filename=fname, title=title, description=desc))
        return items
    
    def _resolve_requests_per_minute(self) -> float:
        return DEFAULT_REQUESTS_PER_MINUTE
    
    def _resolve_retry_attempts(self) -> int:
        return DEFAULT_AGENT_MAX_RETRIES
    
    def _resolve_retry_backoff(self) -> float:
        return DEFAULT_RETRY_BACKOFF_SECONDS
    
    def _optional_tool_guidance(self) -> str:
        return ""
    
    def _build_style_guidance(self) -> str:
        return "Use clear headings."
    
    @staticmethod
    def _resolve_bool_option(override: bool | None, env_var: str, *, default: bool) -> bool:
        if override is not None:
            return override
        raw = os.getenv(env_var)
        if raw and raw.lower() in {"1", "true", "yes"}:
            return True
        return default
    
    @staticmethod
    def _resolve_int_option(override: int | None, env_var: str, *, default: int, minimum: int = 1) -> int:
        if override is not None:
            return max(minimum, override)
        raw = os.getenv(env_var)
        if raw:
            try:
                return max(minimum, int(raw))
            except ValueError:
                pass
        return max(minimum, default)
    
    @staticmethod
    def _reset_directory(path: Path) -> None:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
    
    def _sanitize_tutorial_outputs(self, paths: Iterable[Path]) -> None:
        for path in paths:
            c = path.read_text("utf-8")
            fixed = self._sanitize_mermaid_blocks(c)
            if fixed != c:
                path.write_text(fixed, "utf-8")


__all__ = ["TutorialGenerator", "TutorialOutlineItem"]