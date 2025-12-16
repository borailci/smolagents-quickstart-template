"""Generate tutorial markdown files from the knowledge base."""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, cast

from dotenv import load_dotenv
from loguru import logger
from smolagents import LiteLLMModel
from smolagents.agents import ToolCallingAgent
from smolagents.utils import AgentGenerationError
from smolagents.models import ChatMessage, MessageRole

from prompts import prompts
from pipelines.types import TutorialOutlineItem, TutorialRunMetrics
from toolkits.sub_agent_toolkit import (
    SubAgentRole,
    SubAgentTaskSpec,
    run_typed_sub_agent_tasks,
)
from toolkits.tutorial_toolkit import build_tutorial_supervisor_tools
from utils.path_utils import ensure_directory, resolve_within_root, PathTraversalError

try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None

__all__ = ["TutorialGenerator", "TutorialOutlineItem", "TutorialValidationIssue"]

load_dotenv()

LITELLM_MODEL_ID = os.getenv("LITELLM_MODEL_ID")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
CODEBASE_ROOT_PATH = os.getenv("CODEBASE_ROOT_PATH")
KNOWLEDGE_BASE_OUTPUT_PATH = os.getenv("KNOWLEDGE_BASE_OUTPUT_PATH")
TUTORIAL_OUTPUT_PATH = os.getenv("TUTORIAL_OUTPUT_PATH")
SUB_AGENTS_ROOT_PATH = os.getenv("SUB_AGENTS_ROOT_PATH")
DEFAULT_BASE_ROOT = Path("data/agent_workspace").expanduser().resolve()
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


TUTORIAL_ENABLE_RAG_ENV = "TUTORIAL_ENABLE_RAG"
TUTORIAL_RAG_MAX_SNIPPETS_ENV = "TUTORIAL_RAG_MAX_SNIPPETS"
TUTORIAL_STEP_DELAY_SECONDS_ENV = "TUTORIAL_STEP_DELAY_SECONDS"
DEFAULT_RAG_MAX_SNIPPETS = 3  # keep RAG light to reduce cost
DEFAULT_STEP_DELAY_SECONDS = 0.0


@dataclass(frozen=True)
class TutorialOutlineItem:
    filename: str
    title: str
    description: str


@dataclass(frozen=True)
class TutorialValidationIssue:
    level: str  # "warning" or "error"
    message: str


@dataclass
class TutorialRunMetrics:
    tool_calls: int = 0
    tool_token_estimate: int = 0
    instructions_token_estimate: int = 0
    tutorial_token_estimate: int = 0
    context_overflow_events: int = 0
    model_errors: list[str] = field(default_factory=list)

    @property
    def total_estimated_tokens(self) -> int:
        return (
            self.tool_token_estimate
            + self.instructions_token_estimate
            + self.tutorial_token_estimate
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_calls": self.tool_calls,
            "tool_token_estimate": self.tool_token_estimate,
            "instructions_token_estimate": self.instructions_token_estimate,
            "tutorial_token_estimate": self.tutorial_token_estimate,
            "total_estimated_tokens": self.total_estimated_tokens,
            "context_overflow_events": self.context_overflow_events,
            "model_errors": list(self.model_errors),
        }


@dataclass(frozen=True)
class _CodeBlock:
    language: str
    body: str
    line: int


# NOTE: Default outline removed to force dynamic, project-specific generation.

_MIN_UNIQUE_SECOND_LEVEL_HEADINGS = 2
MIN_DYNAMIC_TUTORIALS = 5
MAX_DYNAMIC_TUTORIALS = 10  # Increased to ensure comprehensive coverage
CODEBASE_TREE_MAX_DEPTH = 2
CODEBASE_TREE_MAX_ENTRIES = 180
ANCHOR_FILES_PER_CATEGORY = 3


def _slugify(value: str) -> str:
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


_CODE_BLOCK_PATTERN = re.compile(r"```(?P<lang>[\w-]*)\n(?P<body>.*?)```", re.DOTALL)
_BACKTICK_PATTERN = re.compile(r"`([^`]+)`")
_MERMAID_STARTERS = {
    "graph",
    "sequencediagram",
    "statediagram",
    "classdiagram",
    "erdiagram",
}


def _line_number_from_index(text: str, index: int) -> int:
    return text[:index].count("\n") + 1


def _collect_code_blocks(content: str) -> List[_CodeBlock]:
    blocks: List[_CodeBlock] = []
    for match in _CODE_BLOCK_PATTERN.finditer(content):
        lang = (match.group("lang") or "").strip().lower()
        body = match.group("body").strip("\n")
        line = _line_number_from_index(content, match.start())
        blocks.append(_CodeBlock(language=lang, body=body, line=line))
    return blocks


def validate_tutorial_structure(
    content: str,
    expected_title: str | None = None,
    min_length: int = 300,
) -> tuple[bool, list[str]]:
    """
    Validate tutorial structural integrity.
    
    Returns (is_valid, list_of_errors).
    This catches broken tutorials from truncated output, bad concatenation, etc.
    
    Uses core validation from utils/validation.py with tutorial-specific settings.
    """
    from utils.validation import (
        validate_content,
        validate_heading_sequence,
        validate_code_block_completeness,
    )
    
    # Use core validation with strict settings for tutorials
    result = validate_content(
        content,
        min_chars=min_length,
        expected_title=expected_title,
        check_mermaid=True,
        strict_heading_start=True,  # Tutorials must start with #
    )
    
    # Combine issues and warnings for backward compatibility
    errors = list(result.issues)
    
    # Add tutorial-specific checks not in core
    heading_errors = validate_heading_sequence(content)
    errors.extend(heading_errors)
    
    truncation_errors = validate_code_block_completeness(content)
    errors.extend(truncation_errors)
    
    # Check for at least one H1 or H2 heading
    if not re.search(r"^#{1,2}\s+.+", content, re.MULTILINE):
        errors.append("Missing main heading (H1 or H2)")
    
    return (len(errors) == 0, errors)


# Legacy helper functions - now imported from utils/validation
def _validate_heading_sequence(content: str) -> list[str]:
    """Legacy wrapper - use utils.validation.validate_heading_sequence."""
    from utils.validation import validate_heading_sequence
    return validate_heading_sequence(content)


def _validate_code_block_completeness(content: str) -> list[str]:
    """Legacy wrapper - use utils.validation.validate_code_block_completeness."""
    from utils.validation import validate_code_block_completeness
    return validate_code_block_completeness(content)


def _validate_mermaid_blocks(content: str) -> list[str]:
    """Legacy wrapper - use utils.validation.validate_mermaid_blocks."""
    from utils.validation import validate_mermaid_blocks
    return validate_mermaid_blocks(content)


def _validate_tutorial_content(
    content: str, tutorial_path: Path, codebase_root: Path
) -> List[TutorialValidationIssue]:
    """Validate tutorial content for quality requirements."""

    issues: List[TutorialValidationIssue] = []

    # Duplicate headers
    headers = re.findall(r"^#+\s+(.+)$", content, re.MULTILINE)
    if len(headers) != len(set(headers)):
        issues.append(
            TutorialValidationIssue("warning", "Contains duplicate headings.")
        )

    code_blocks = _collect_code_blocks(content)

    # Empty or language-less code blocks
    for idx, block in enumerate(code_blocks, start=1):
        if len(block.body.strip().splitlines()) == 0:
            issues.append(
                TutorialValidationIssue("error", f"Code block #{idx} is empty.")
            )
    missing_lang = sum(1 for block in code_blocks if not block.language)
    if missing_lang:
        issues.append(
            TutorialValidationIssue(
                "warning", f"{missing_lang} code blocks missing language hints."
            )
        )

    # Mermaid diagrams
    mermaid_blocks = [block for block in code_blocks if block.language == "mermaid"]
    if not mermaid_blocks:
        issues.append(
            TutorialValidationIssue("error", "Missing required Mermaid diagram.")
        )
    else:
        for block in mermaid_blocks:
            lines = [ln.strip() for ln in block.body.splitlines() if ln.strip()]
            first_line = lines[0].lower() if lines else ""
            if not any(first_line.startswith(prefix) for prefix in _MERMAID_STARTERS):
                issues.append(
                    TutorialValidationIssue(
                        "error",
                        "Mermaid diagram must start with graph/sequence/state/class declaration.",
                    )
                )
            if all(token not in block.body for token in ("-->", "---", "-.->")):
                issues.append(
                    TutorialValidationIssue(
                        "warning", "Mermaid diagram has no connecting arrows."
                    )
                )
            # Check for unquoted nested parentheses in node labels ([], {}, ())
            # These often break Mermaid rendering if not quoted: id[Label (text)] vs id["Label (text)"]
            if re.search(r"(\[|\{|\()\s*(?![\"']).*?\(.*?\).*?(\]|\}|\))", block.body):
                issues.append(
                    TutorialValidationIssue(
                        "warning",
                        "Mermaid node labels with parentheses should be quoted (e.g., node[\"Label (Info)\"]).",
                    )
                )

    # Generic placeholder code
    if re.search(r"print\([\'\"]Hello[\'\"]", content, re.IGNORECASE):
        issues.append(
            TutorialValidationIssue(
                "warning", "Contains placeholder 'Hello' example instead of real code."
            )
        )

    # Bash presence
    if not any(block.language == "bash" for block in code_blocks):
        issues.append(
            TutorialValidationIssue(
                "warning",
                "At least one bash block with runnable commands is recommended.",
            )
        )

    # Broken f-strings
    if re.search(r'f"[\s\S]*?\n"', content):
        issues.append(
            TutorialValidationIssue(
                "error", "Detected broken f-string split across multiple lines."
            )
        )

    # Nested code fences & commentary inside blocks
    lines = content.split("\n")
    in_block = False
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_block:
                in_block = True
            else:
                if len(stripped) > 3:
                    issues.append(
                        TutorialValidationIssue(
                            "error",
                            f"Nested code fence detected at line {idx}: {stripped}",
                        )
                    )
                in_block = False
        elif in_block and ("**NOTE:**" in line or "@pytest.Mindtype" in line):
            issues.append(
                TutorialValidationIssue(
                    "warning",
                    f"Meta commentary detected inside code block at line {idx}.",
                )
            )

    issues.extend(_validate_code_block_syntax(code_blocks, tutorial_path))
    issues.extend(_validate_file_references(content, tutorial_path, codebase_root))

    # Encourage explicit line references
    if not re.search(r"#L\d+", content, re.IGNORECASE):
        issues.append(
            TutorialValidationIssue(
                "warning", "No file references with #L line anchors were found."
            )
        )

    return issues


def _validate_code_block_syntax(
    blocks: Sequence[_CodeBlock], tutorial_path: Path
) -> List[TutorialValidationIssue]:
    issues: List[TutorialValidationIssue] = []
    for block in blocks:
        lang = block.language
        body = block.body.strip()
        if not body:
            continue
        if lang in {"python", "py"}:
            try:
                ast.parse(body)
            except SyntaxError as exc:
                issues.append(
                    TutorialValidationIssue(
                        "error",
                        f"Python block near line {block.line} is invalid: {exc.msg}.",
                    )
                )
        elif lang == "json":
            try:
                json.loads(body)
            except json.JSONDecodeError as exc:
                issues.append(
                    TutorialValidationIssue(
                        "error",
                        f"JSON block near line {block.line} is invalid: {exc.msg}.",
                    )
                )
    return issues


def _clean_reference_token(token: str) -> str | None:
    if not token:
        return None
    stripped = token.strip()
    if not stripped:
        return None
    candidate = stripped.split()[0]
    candidate = candidate.strip("`\"'()[]{}.,")
    if not candidate:
        return None
    candidate = candidate.replace("\\", "/")
    if candidate.startswith("./"):
        candidate = candidate[2:]
    if candidate.startswith("/"):
        candidate = candidate[1:]
    if "/" not in candidate:
        return None
    return candidate


def _parse_line_anchor(anchor: str) -> tuple[int | None, int | None]:
    match = re.match(r"l(?P<start>\d+)(?:-l?(?P<end>\d+))?", anchor.lower())
    if not match:
        return None, None
    start = int(match.group("start")) if match.group("start") else None
    end = int(match.group("end")) if match.group("end") else None
    return start, end


def _validate_file_references(
    content: str, tutorial_path: Path, codebase_root: Path
) -> List[TutorialValidationIssue]:
    issues: List[TutorialValidationIssue] = []
    refs: List[str] = []
    for match in _BACKTICK_PATTERN.finditer(content):
        cleaned = _clean_reference_token(match.group(1))
        if cleaned:
            refs.append(cleaned)

    if not refs:
        issues.append(
            TutorialValidationIssue(
                "warning",
                "Tutorial does not reference specific codebase files; consider citing modules like app/api/...",
            )
        )
        return issues

    valid_refs = 0
    for ref in sorted(set(refs)):
        path_part, _, anchor = ref.partition("#")
        try:
            resolved = resolve_within_root(codebase_root, path_part)
        except PathTraversalError:
            issues.append(
                TutorialValidationIssue(
                    "error", f"Reference `{ref}` escapes the codebase root."
                )
            )
            continue

        if not resolved.exists():
            issues.append(
                TutorialValidationIssue(
                    "error",
                    f"Reference `{ref}` points to a file or directory that does not exist.",
                )
            )
            continue

        valid_refs += 1

        if anchor:
            start, end = _parse_line_anchor(anchor)
            if start or end:
                try:
                    total_lines = sum(1 for _ in resolved.open("r", encoding="utf-8"))
                except OSError:
                    continue
                if start and start > total_lines:
                    issues.append(
                        TutorialValidationIssue(
                            "error",
                            f"Reference `{ref}` exceeds file length ({total_lines} lines).",
                        )
                    )
                if end and end > total_lines:
                    issues.append(
                        TutorialValidationIssue(
                            "error",
                            f"Reference `{ref}` end line exceeds file length ({total_lines} lines).",
                        )
                    )

    if valid_refs == 0:
        issues.append(
            TutorialValidationIssue(
                "error",
                "All referenced file paths are invalid; descriptions may not match the codebase.",
            )
        )

    return issues


def _auto_fix_common_issues(content: str) -> str:
    """Automatically fix common tutorial quality issues without data loss."""
    lines = content.split("\n")
    fixed_lines = []
    seen_headers = set()

    for line in lines:
        if line.startswith("#"):
            if line in seen_headers and len(line) > 5:
                continue
            seen_headers.add(line)
        fixed_lines.append(line)

    content = "\n".join(fixed_lines)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content


class TutorialGenerator:
    def __init__(
        self,
        *,
        codebase_root: str | Path | None = None,
        knowledge_base_root: str | Path | None = None,
        output_root: str | Path | None = None,
        sub_agents_root: str | Path | None = None,
        outline: Sequence[TutorialOutlineItem] | None = None,
        enable_rag: bool | None = None,
        rag_max_snippets: int | None = None,
        step_delay_seconds: float | None = None,
        rag_force_rebuild: bool = False,
        rag_codebase_cache_path: str | Path | None = None,
        dry_run: bool = False,
    ) -> None:
        model_id = _require_env("LITELLM_MODEL_ID", LITELLM_MODEL_ID)
        api_key = _require_env("LITELLM_API_KEY", LITELLM_API_KEY)

        self.dry_run = dry_run
        self.metrics = TutorialRunMetrics()

        base_root = DEFAULT_BASE_ROOT
        self.codebase_root = (
            Path(codebase_root or CODEBASE_ROOT_PATH or base_root)
            .expanduser()
            .resolve()
        )
        self.knowledge_base_root = (
            Path(
                knowledge_base_root
                or KNOWLEDGE_BASE_OUTPUT_PATH
                or (base_root / "knowledge_base")
            )
            .expanduser()
            .resolve()
        )
        self.output_root = ensure_directory(
            output_root or TUTORIAL_OUTPUT_PATH or (base_root / "tutorials")
        )

        if sub_agents_root:
            self.sub_agents_root = Path(sub_agents_root).expanduser().resolve()
        else:
            # Default for standalone usage
            self.sub_agents_root = ensure_directory(
                base_root / "sub_agents_tutorials"
            )

        if sub_agents_root:
            polisher_root_base = self.sub_agents_root
        elif SUB_AGENTS_ROOT_PATH:
            polisher_root_base = (
                Path(SUB_AGENTS_ROOT_PATH).expanduser().resolve() / "tutorial_polishers"
            )
        else:
            polisher_root_base = self.output_root / "_polishers"
        self.polisher_root = ensure_directory(polisher_root_base)

        self._outline_override = tuple(outline) if outline else None
        self.outline: Sequence[TutorialOutlineItem] | None = None
        self.enable_rag = self._resolve_bool_option(
            enable_rag, TUTORIAL_ENABLE_RAG_ENV, default=True
        )
        self.rag_max_snippets = self._resolve_int_option(
            rag_max_snippets,
            TUTORIAL_RAG_MAX_SNIPPETS_ENV,
            default=DEFAULT_RAG_MAX_SNIPPETS,
        )
        self.rag_force_rebuild = rag_force_rebuild
        
        # Check for RAG cache path (arg takes precedence, then env)
        self.rag_codebase_cache_path = None
        if self.enable_rag:
            if rag_codebase_cache_path:
                 self.rag_codebase_cache_path = str(rag_codebase_cache_path)
            else:
                 env_cache = os.environ.get("RAG_CODEBASE_CACHE_DIR")
                 if env_cache:
                      self.rag_codebase_cache_path = env_cache

        self._token_encoder = self._build_token_encoder(model_id)

        requests_per_minute = self._resolve_requests_per_minute()
        self._min_interval = 60.0 / requests_per_minute
        self._last_request_time = 0.0

        self._max_retries = self._resolve_retry_attempts()
        self._retry_backoff_seconds = self._resolve_retry_backoff()
        self._step_delay_seconds = self._resolve_float_option(
            step_delay_seconds,
            TUTORIAL_STEP_DELAY_SECONDS_ENV,
            default=DEFAULT_STEP_DELAY_SECONDS,
            minimum=0.0,
        )

        self.model = LiteLLMModel(
            model_id=model_id,
            api_key=api_key,
            requests_per_minute=requests_per_minute,
        )

    # ----- Metrics helpers -------------------------------------------------

    def _build_token_encoder(self, model_id: str) -> Callable[[str], int]:
        if tiktoken is None:
            return lambda text: max(1, len(text) // 4)

        try:
            encoding = tiktoken.encoding_for_model(model_id)
        except Exception:
            encoding = tiktoken.get_encoding("cl100k_base")

        def _encode(text: str) -> int:
            try:
                return len(encoding.encode(text))
            except Exception:
                return max(1, len(text) // 4)

        return _encode

    def _count_tokens(self, text: str) -> int:
        return self._token_encoder(text)

    def _record_tool_usage(self, tool_name: str, content: Any = None) -> None:
        self.metrics.tool_calls += 1
        if content:
            try:
                as_text = content if isinstance(content, str) else json.dumps(content)
            except Exception:
                as_text = str(content)
            self.metrics.tool_token_estimate += self._count_tokens(as_text)

    def _record_instruction_tokens(self, *chunks: str) -> None:
        for chunk in chunks:
            if chunk:
                self.metrics.instructions_token_estimate += self._count_tokens(chunk)

    def _record_tutorial_tokens(self, path: Path) -> None:
        try:
            content = path.read_text("utf-8")
        except OSError:
            return
        self.metrics.tutorial_token_estimate += self._count_tokens(content)

    @staticmethod
    def _is_context_overflow(message: str) -> bool:
        lowered = message.lower()
        return (
            "context length" in lowered
            or "maximum context" in lowered
            or "token limit" in lowered
            or "too long" in lowered
        )

    @staticmethod
    def _is_rate_limit_error(message: str) -> bool:
        lowered = message.lower()
        return (
            "resource exhausted" in lowered
            or "rate limit" in lowered
            or "quota" in lowered
            or "too many requests" in lowered
            or "429" in message
        )

    def generate(self) -> List[Path]:
        """Generate tutorials using supervisor mode (default).
        
        This method now always delegates to generate_with_supervisor()
        for consistent, autonomous tutorial generation.
        """
        return self.generate_with_supervisor()


    def _prepare_tutorial_state(self, base_state: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("Preparing tutorial output directory at {}", self.output_root)
        self._reset_directory(self.output_root)

        tools = build_tutorial_tools(
            codebase_root=str(self.codebase_root),
            knowledge_base_root=str(self.knowledge_base_root),
            tutorial_output_root=str(self.output_root),
            enable_rag=self.enable_rag,
            rag_max_snippets=self.rag_max_snippets,
            rag_force_rebuild=self.rag_force_rebuild,
            rag_codebase_cache_path=self.rag_codebase_cache_path,
            usage_callback=self._record_tool_usage,
        )

        kb_summary = self._summarize_knowledge_base()
        outline = self._resolve_outline(kb_summary)
        self.outline = outline
        style_guidance = self._build_style_guidance()
        outline_brief = self._build_outline_brief(outline)
        codebase_context = self._build_codebase_context()

        prepared = {
            "kb_summary": kb_summary,
            "outline": outline,
            "tools": tools,
            "style_guidance": style_guidance,
            "outline_brief": outline_brief,
            "codebase_context": codebase_context,
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
        codebase_context: str,
    ) -> List[Path]:
        tutorial_paths: List[Path] = []
        max_validation_retries = 2  # Maximum retries for validation failures

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
                codebase_context=codebase_context,
            )

            produced_path = self.output_root / item.filename
            validation_attempt = 0
            
            while validation_attempt <= max_validation_retries:
                logger.debug(
                    "Generating tutorial '{}' (validation attempt {}/{})...",
                    item.title,
                    validation_attempt + 1,
                    max_validation_retries + 1,
                )
                
                # Build task with validation feedback if this is a retry
                current_task = task
                if validation_attempt > 0 and produced_path.exists():
                    # Read the previously generated content
                    try:
                        prev_content = produced_path.read_text(encoding="utf-8")
                        is_valid, errors = validate_tutorial_structure(prev_content, item.title)
                        if errors:
                            error_feedback = "\n".join(f"- {e}" for e in errors)
                            current_task = (
                                f"IMPORTANT: Your previous tutorial output had validation errors. "
                                f"You MUST fix these issues:\n{error_feedback}\n\n"
                                f"Re-generate the tutorial with corrections. Original task:\n\n{task}"
                            )
                            logger.warning(
                                "Tutorial '{}' validation failed, retrying with feedback: {}",
                                item.title,
                                errors,
                            )
                    except Exception as e:
                        logger.warning(f"Could not read previous content for validation: {e}")
                
                self._record_instruction_tokens(prompts.TUTORIAL_AGENT_PROMPT, current_task)
                self._run_agent_with_retries(
                    _agent_factory, current_task, prompts.TUTORIAL_AGENT_PROMPT
                )

                if self.dry_run:
                    tutorial_paths.append(produced_path)
                    break

                if not produced_path.exists():
                    logger.error(
                        "Agent claimed success but file {} was not created.", produced_path
                    )
                    validation_attempt += 1
                    continue

                # Validate the generated tutorial
                try:
                    content = produced_path.read_text(encoding="utf-8")
                    is_valid, errors = validate_tutorial_structure(content, item.title)
                    
                    if is_valid:
                        logger.info("Tutorial '{}' passed validation ✓", item.title)
                        tutorial_paths.append(produced_path)
                        break
                    else:
                        logger.warning(
                            "Tutorial '{}' validation failed with {} errors",
                            item.title,
                            len(errors),
                        )
                        validation_attempt += 1
                        if validation_attempt > max_validation_retries:
                            # Accept the tutorial with warnings after max retries
                            logger.warning(
                                "Max validation retries reached for '{}', accepting with issues: {}",
                                item.title,
                                errors,
                            )
                            tutorial_paths.append(produced_path)
                except Exception as e:
                    logger.error(f"Validation error for '{item.title}': {e}")
                    tutorial_paths.append(produced_path)
                    break

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
        attempt = 0

        while True:
            # Only increment attempts for non-quota failures to allow unlimited rate-limit retries
            counted_attempt = False
            if attempt >= self._max_retries:
                break

            attempt += 1
            counted_attempt = True
            self._respect_rate_limit()
            try:
                agent.run(task)
                self._record_request_timestamp()
                return
            except Exception as error:
                last_error = error
                self._record_request_timestamp()

                message = str(error)
                self.metrics.model_errors.append(message)
                if self._is_context_overflow(message):
                    self.metrics.context_overflow_events += 1

                # Broaden the empty response check
                is_parsing_error = (
                    "message contains no content" in message.lower()
                    or "parsing tool call" in message.lower()
                    or "malformed" in message.lower()
                )

                if is_parsing_error:
                    logger.warning(f"Empty/Malformed response from model (attempt {attempt}): {error}")
                    if STRICT_TOOL_CALL_REMINDER not in instructions:
                        instructions += STRICT_TOOL_CALL_REMINDER
                        agent = agent_factory(instructions)
                    time.sleep(2.0)
                    continue

                if self._is_rate_limit_error(message):
                    logger.warning(
                        "Rate limit encountered during tutorial generation; sleeping 5.0s before retrying."
                    )
                    time.sleep(5.0)
                    # Do not count this attempt against retry budget
                    attempt -= 1 if counted_attempt else 0
                    continue

                # Use a fixed, bounded wait (no exponential/linear growth)
                wait_seconds = min(5.0, self._retry_backoff_seconds)
                if attempt < self._max_retries:
                    logger.warning(
                        f"Attempt {attempt} failed: {error}. Waiting {wait_seconds}s..."
                    )
                    time.sleep(wait_seconds)

        if last_error:
            raise last_error

    def _respect_rate_limit(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_time
        wait_for_rpm = max(0.0, self._min_interval - elapsed)
        if wait_for_rpm > 0:
            time.sleep(wait_for_rpm)
        if self._step_delay_seconds > 0:
            time.sleep(self._step_delay_seconds)

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

        wiki_path = self._write_wiki_page(paths)
        if wiki_path:
            paths.append(wiki_path)

        for path in paths:
            if path.exists():
                self._record_tutorial_tokens(path)

        return paths

    def _run_tutorial_polishers(self, tutorial_paths: Iterable[Path]) -> None:
        tutorials = [path for path in tutorial_paths if path.exists()]
        if not tutorials:
            return

        logger.debug("Running polishers for {} tutorials...", len(tutorials))
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
            if i >= len(workspaces):
                break

            workspace = workspaces[i]
            polished_file = workspace / tutorial_path.name

            if polished_file.exists() and polished_file.stat().st_size > 50:
                tutorial_path.write_text(polished_file.read_text("utf-8"), "utf-8")
                logger.debug("Applied polish to %s", tutorial_path.name)
            else:
                logger.warning(
                    f"Polisher failed for {tutorial_path.name}, keeping original."
                )

    def _build_polisher_task_description(self, tutorial_path: Path) -> str:
        return (
            f"Review and polish the tutorial '{tutorial_path.name}'.\n"
            "1. Fix typos and grammar.\n"
            "2. Ensure every code block has a language tag (e.g. ```bash, ```python, ```json, ```mermaid).\n"
            "3. Close any unclosed fences and split/merged code sections correctly.\n"
            "4. Fix broken Markdown links.\n"
            "5. If the file is already perfect, still write it back unchanged to your workspace with the SAME filename; otherwise, write the corrected version.\n"
        )

    def _write_wiki_page(self, tutorial_paths: Iterable[Path]) -> Path | None:
        wiki_path = self.output_root / "wiki.md"
        entries: list[tuple[str, str, str]] = []

        for path in sorted(tutorial_paths, key=lambda p: p.name):
            if path == wiki_path or not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
            title = match.group(1).strip() if match else _title_from_filename(path.stem)
            anchor = _slugify(title)
            entries.append((title, anchor, text.strip()))

        if not entries:
            return None

        toc_anchor = _slugify("Tutorials Wiki")
        lines = [
            "# Tutorials Wiki",
            "",
            "> Compact, single-page view of all tutorials. Use the TOC below to jump around.",
            "",
            "## Table of Contents",
        ]
        for title, anchor, _ in entries:
            lines.append(f"- [{title}](#{anchor})")
        lines.extend(["", f'<a id="{toc_anchor}"></a>'])

        back_link = f"[↩ Back to top](#{toc_anchor})"
        for title, anchor, text in entries:
            lines.append("---")
            lines.append(f'<a id="{anchor}"></a>')
            lines.append(text)
            lines.append("")
            lines.append(back_link)
            lines.append("")

        wiki_path.write_text("\n".join(lines), encoding="utf-8")
        return wiki_path

    def _summarize_knowledge_base(
        self, max_entries: int = 30, max_chars_per_file: int = 800
    ) -> str:
        """Return a structured summary with actual KB content excerpts."""
        entries = sorted(self.knowledge_base_root.glob("*.md"))
        if not entries:
            return "No knowledge base files found."

        sections = []
        for entry in entries[:max_entries]:
            try:
                content = entry.read_text("utf-8")[:max_chars_per_file]
                if len(content) >= max_chars_per_file:
                    # Truncate at word boundary
                    content = content.rsplit(" ", 1)[0] + "..."
                sections.append(f"### {entry.stem}\n{content}")
            except Exception:
                sections.append(f"### {entry.stem}\n[Unable to read]")

        return "\n\n".join(sections)

    def _build_outline_brief(self, items: Sequence[TutorialOutlineItem]) -> str:
        return "\n".join(f"- {item.filename}: {item.title}" for item in items)

    def _build_codebase_context(self) -> str:
        target = self.codebase_root / "app"
        if not target.exists():
            target = self.codebase_root

        tree = self._build_directory_tree(
            target,
            max_depth=CODEBASE_TREE_MAX_DEPTH,
            max_entries=CODEBASE_TREE_MAX_ENTRIES,
        )

        anchors = self._collect_anchor_files()
        sections: List[str] = []

        if tree:
            sections.append("### Core Tree Snapshot")
            sections.append(f"```text\n{tree}\n```")

        if anchors:
            sections.append("### Anchor Files (start here)")
            sections.extend(anchors)

        sections.append(
            "Favor the paths above and the knowledge base before considering any RAG lookups."
        )

        return "\n\n".join(sections)

    def _build_directory_tree(
        self, root: Path, *, max_depth: int, max_entries: int
    ) -> str:
        lines: List[str] = []
        try:
            relative_root = root.relative_to(self.codebase_root).as_posix() or "."
        except ValueError:
            relative_root = root.name

        if root.is_dir():
            lines.append(f"{relative_root}/")
        else:
            lines.append(relative_root)

        total = 0

        def _walk(current: Path, prefix: str, depth: int) -> None:
            nonlocal total
            if depth > max_depth:
                return
            try:
                entries = sorted(
                    (
                        entry
                        for entry in current.iterdir()
                        if not entry.name.startswith(".")
                        and entry.name != "__pycache__"
                    ),
                    key=lambda entry: (not entry.is_dir(), entry.name.lower()),
                )
            except OSError:
                return

            for index, entry in enumerate(entries):
                if total >= max_entries:
                    lines.append(f"{prefix}└── ... (truncated)")
                    return

                connector = "└── " if index == len(entries) - 1 else "├── "
                child_prefix = "    " if index == len(entries) - 1 else "│   "
                name = entry.name + ("/" if entry.is_dir() else "")
                lines.append(f"{prefix}{connector}{name}")
                total += 1

                if entry.is_dir():
                    _walk(entry, prefix + child_prefix, depth + 1)

        _walk(root, "", 1)
        return "\n".join(lines)

    def _collect_anchor_files(self) -> List[str]:
        categories: Sequence[tuple[str, Path, str]] = (
            ("API Routes", self.codebase_root / "app" / "api" / "routes", "*.py"),
            ("Services", self.codebase_root / "app" / "services", "*.py"),
            (
                "Repositories",
                self.codebase_root / "app" / "db" / "repositories",
                "*.py",
            ),
            ("Schemas", self.codebase_root / "app" / "models" / "schemas", "*.py"),
            ("Tests", self.codebase_root / "tests", "test_*.py"),
        )

        anchors: List[str] = []
        for label, base, pattern in categories:
            if not base.exists():
                continue

            try:
                matches = sorted(
                    base.glob(pattern)
                    if pattern != "test_*.py"
                    else base.rglob(pattern)
                )
            except OSError:
                continue

            added = 0
            for path in matches:
                if path.name.startswith("__") or path.is_dir():
                    continue
                rel = path.relative_to(self.codebase_root).as_posix()
                anchors.append(f"- {label}: `{rel}`")
                added += 1
                if added >= ANCHOR_FILES_PER_CATEGORY:
                    break

        return anchors

    def _build_tutorial_task(
        self,
        item: TutorialOutlineItem,
        *,
        kb_summary: str,
        style_guidance: str,
        outline_brief: str,
        codebase_context: str,
    ) -> str:
        exec_summary = self._get_executive_summary()

        return f"""Write tutorial: `{item.filename}`
Title: {item.title}
Goal: {item.description}

KB SUMMARY (primary reference):
{exec_summary[:1500]}

CODEBASE SNAPSHOT:
{codebase_context[:500]}

STYLE: {style_guidance}
OUTLINE: {outline_brief}

INSTRUCTIONS:
1. Use KB as primary reference for architecture
2. Verify specific code with read_file tool
3. Include Mermaid diagram and bash examples
4. Cite file paths with #L line ranges
{self._optional_tool_guidance()}
"""

    def _get_executive_summary(self) -> str:
        """Load the executive summary or overview from KB."""
        priority_files = ["summary.md", "executive_summary.md", "overview.md"]
        for name in priority_files:
            path = self.knowledge_base_root / name
            if path.exists():
                try:
                    content = path.read_text("utf-8")[:2000]
                    if len(content) >= 2000:
                        content = content.rsplit(" ", 1)[0] + "..."
                    return content
                except Exception:
                    continue
        return "No executive summary available. Use list_knowledge_base and read_knowledge_base_file tools to explore the knowledge base."

    def _sanitize_mermaid_blocks(self, content: str) -> str:
        mermaid_pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)

        def sanitize_block(match: re.Match[str]) -> str:
            block = match.group(1)
            lines = [self._sanitize_mermaid_line(line) for line in block.splitlines()]
            return f"```mermaid\n{'\n'.join(lines)}\n```"

        return mermaid_pattern.sub(sanitize_block, content)

    @staticmethod
    def _sanitize_mermaid_line(line: str) -> str:
        """Fix common Mermaid syntax errors."""
        stripped = line.rstrip()
        indent = line[: len(line) - len(line.lstrip())]
        core = stripped.lstrip()
        
        if not core:
            return line
            
        # Fix pipe instead of bracket for nodes: A|Label] -> A[Label]
        # Regex to find ID|Label] or ID|Label| pattern common in some LLM halucinations
        # Pattern: Word char + | + text + ]
        core = re.sub(r'(\w+)\|([^\]|]+)\]', r'\1[\2]', core)
        
        # Pattern: Word char + | + text + |
        # Only do this if it looks like a node definition (start of line)
        if re.match(r'^\w+\|.*\|$', core):
             core = re.sub(r'^(\w+)\|([^|]+)\|$', r'\1[\2]', core)

        return f"{indent}{core}"

    def _normalize_heading_tokens(self, tutorial_paths: Iterable[Path]) -> None:
        pattern = re.compile(
            r"^h(?P<level>[1-6])_(?P<body>.+?)h(?P=level)$", re.IGNORECASE
        )
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
            if fixed != c:
                path.write_text(fixed, "utf-8")

    def _validate_and_report_tutorial_quality(self, paths: Iterable[Path]) -> None:
        for path in paths:
            issues = _validate_tutorial_content(
                path.read_text("utf-8"), path, self.codebase_root
            )
            for issue in issues:
                log_fn = logger.error if issue.level == "error" else logger.warning
                log_fn("%s: %s", path.name, issue.message)

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
            logger.debug("Using user-provided outline override.")
            return self._outline_override

        # Priority 2: AI Planner (Dynamic)
        logger.debug("Asking AI Planner to design the tutorial structure...")
        dynamic = self._generate_dynamic_outline(kb_summary)

        if dynamic:
            logger.debug("AI Planner created %d tutorials.", len(dynamic))
            return dynamic

        # Priority 3: Hard Fail
        # We REMOVED the heuristic fallback here.
        # If the AI fails, we do NOT want to auto-generate a tutorial for every file.
        raise RuntimeError(
            "The AI Planner failed to generate a valid outline JSON. "
            "Please check your API keys or try again. "
            "(Automatic 1:1 file mapping has been disabled to ensure quality)."
        )

    def _generate_dynamic_outline(
        self, kb_summary: str
    ) -> Sequence[TutorialOutlineItem]:
        system_prompt = prompts.DYNAMIC_OUTLINE_SYSTEM_PROMPT.format(
            min_tutorials=MIN_DYNAMIC_TUTORIALS,
            max_tutorials=MAX_DYNAMIC_TUTORIALS,
        )

        repo_name = self.codebase_root.name
        user_prompt = prompts.DYNAMIC_OUTLINE_USER_PROMPT.format(
            repo_name=repo_name,
            kb_summary=kb_summary,
        )

        messages: list[ChatMessage | dict[str, str]] = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_prompt),
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
                        payload = json.loads(outline_text[start : end + 1])
                    except json.JSONDecodeError:
                        pass

        if not payload:
            logger.warning("Failed to parse JSON from outline response")
            return ()

        items = self._coerce_outline_items(payload)
        if not items:
            return ()
        normalized = self._normalize_outline_filenames(items)
        return tuple(normalized)

    def _coerce_outline_items(self, payload: Any) -> List[TutorialOutlineItem]:
        if not isinstance(payload, list):
            return []
        items = []
        for i, entry in enumerate(payload, 1):
            if not isinstance(entry, dict):
                continue
            title = entry.get("title", "").strip()
            desc = entry.get("description", "").strip()
            fname = entry.get("filename", "").strip()

            if not title or not desc:
                continue

            if not fname:
                fname = f"{i:02d}_{_slugify(title)}.md"
            elif not fname.endswith(".md"):
                fname += ".md"

            items.append(
                TutorialOutlineItem(filename=fname, title=title, description=desc)
            )
        return items

    def _normalize_outline_filenames(
        self, items: Sequence[TutorialOutlineItem]
    ) -> List[TutorialOutlineItem]:
        """Ensure filenames follow a contiguous NN_slug.md pattern.

        The planner sometimes skips numbers (e.g., 01, 02, 04, 05). Renumbering keeps
        downstream polishers and documentation steps predictable without relying on
        heuristics elsewhere.
        """

        normalized: List[TutorialOutlineItem] = []
        for index, item in enumerate(items, start=1):
            stem = Path(item.filename).stem
            match = re.match(r"^\d+_(.+)$", stem)
            slug_source = match.group(1) if match else stem
            slug = _slugify(slug_source) or _slugify(item.title)
            new_name = f"{index:02d}_{slug}.md"
            normalized.append(
                TutorialOutlineItem(
                    filename=new_name,
                    title=item.title,
                    description=item.description,
                )
            )

        return normalized

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
    def _resolve_bool_option(
        override: bool | None, env_var: str, *, default: bool
    ) -> bool:
        if override is not None:
            return override
        raw = os.getenv(env_var)
        if raw and raw.lower() in {"1", "true", "yes"}:
            return True
        return default

    @staticmethod
    def _resolve_int_option(
        override: int | None, env_var: str, *, default: int, minimum: int = 1
    ) -> int:
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
    def _resolve_float_option(
        override: float | None,
        env_var: str,
        *,
        default: float,
        minimum: float = 0.0,
    ) -> float:
        if override is not None:
            return max(minimum, override)
        raw = os.getenv(env_var)
        if raw:
            try:
                return max(minimum, float(raw))
            except ValueError:
                pass
        return max(minimum, default)

    @staticmethod
    def _reset_directory(path: Path) -> None:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)

    def _sanitize_tutorial_outputs(self, paths: Iterable[Path]) -> None:
        """Post-process generated tutorials to fix common LLM formatting errors."""
        from utils.validation import sanitize_content
        
        for path in paths:
            try:
                c = path.read_text("utf-8")
                
                # 0. Core sanitization (generated doc banner, nested backticks, Mermaid |label[)
                c = sanitize_content(c)
                
                # 1. Clean LLM artifacts (wrapping quotes/backticks)
                c = self._clean_llm_artifacts(c)
                
                # 2. Fix broken code blocks (unclosed)
                c = self._fix_unclosed_code_blocks(c)
                
                # 3. Sanitize Mermaid (enhanced)
                c = self._sanitize_mermaid_blocks(c)
                
                path.write_text(c, "utf-8")
                logger.info(f"Sanitized {path.name}")
            except Exception as e:
                logger.warning(f"Failed to sanitize {path}: {e}")


    def _clean_llm_artifacts(self, content: str) -> str:
        s = content.strip()
        
        # Remove wrapping quote blocks (common artifact)
        if s.startswith("'''") and s.endswith("'''"):
             s = s[3:-3].strip()
        elif s.startswith('"""') and s.endswith('"""'):
             s = s[3:-3].strip()
        elif s.startswith("'") and s.endswith("'"):
             s = s[1:-1].strip()
             
        # Remove wrapping markdown code blocks if the entire content is wrapped
        # e.g. ```markdown ... ```
        if s.startswith("```") and s.endswith("```"):
            lines = s.splitlines()
            if len(lines) >= 2:
                # Check if the first line is just opening fence (maybe with language)
                if lines[0].strip().startswith("```") and " " not in lines[0].strip():
                    # Check if last line is just closing fence
                    if lines[-1].strip() == "```":
                        # Return everything in between
                        return "\n".join(lines[1:-1]).strip()

        # Remove literal "Observations:" prefix causing invalid markdown
        if s.startswith("Observations:"):
            s = s.replace("Observations:", "", 1).strip()
        
        # Remove random leading '"' if present (sometimes happens with JSON string dumps)
        if s.startswith('"') and s.endswith('"') and "\n" in s:
             s = s[1:-1].replace('\\"', '"').replace("\\n", "\n")

        return s

    def _fix_unclosed_code_blocks(self, content: str) -> str:
        # Count triple backticks
        count = content.count("```")
        if count % 2 != 0:
            logger.warning("Found unclosed code block, appending closing fence.")
            return content + "\n```"
        return content

    def _create_supervisor_agent(self):
        """Create the Tutorial Supervisor Agent."""
        from toolkits.tutorial_toolkit import build_tutorial_supervisor_tools
        from utils.llm_factory import create_model
        
        tools = build_tutorial_supervisor_tools(
            codebase_root=self.codebase_root,
            sub_agents_root=self.sub_agents_root,
            output_root=self.output_root,
            knowledge_base_root=self.knowledge_base_root,
        )
        
        # Supervisor uses Pro model for better planning (hybrid strategy)
        model = create_model(role="supervisor")

        
        return ToolCallingAgent(
            name="tutorial_supervisor",
            description="Plans and oversees tutorial generation",
            tools=tools,
            model=model,
            instructions=prompts.TUTORIAL_SUPERVISOR_PROMPT,
        )


    def _create_baseline_supervisor_agent(self):
        """Create the Baseline Tutorial Supervisor Agent."""
        from toolkits.tutorial_toolkit import build_tutorial_supervisor_tools
        from utils.llm_factory import create_model
        
        tools = build_tutorial_supervisor_tools(
            codebase_root=self.codebase_root,
            sub_agents_root=self.sub_agents_root,
            output_root=self.output_root,
            knowledge_base_root=self.knowledge_base_root, # Passed but unused by baseline tools
            baseline_mode=True,
        )

        
        model = create_model(role="supervisor")
        
        return ToolCallingAgent(
            name="baseline_supervisor",
            description="Plans and oversees baseline tutorial generation (No KB)",
            tools=tools,
            model=model,
            instructions=prompts.BASELINE_TUTORIAL_SUPERVISOR_PROMPT,
        )

    def generate_baseline_with_supervisor(self) -> List[Path]:
        """Generate tutorials using the Baseline Supervisor (No KB)."""
        logger.info("Starting BASELINE supervised tutorial generation (No KB)...")
        
        # Reset directories if not dry run
        if not self.dry_run:
            if self.sub_agents_root.exists():
                shutil.rmtree(self.sub_agents_root)
            self.sub_agents_root.mkdir(parents=True, exist_ok=True)
            
            if self.output_root.exists():
               shutil.rmtree(self.output_root)
            self.output_root.mkdir(parents=True, exist_ok=True)

        supervisor = self._create_baseline_supervisor_agent()
    
        # Use centralized rate limit retry wrapper
        from pipelines.checkpoint import run_with_rate_limit_retry
        
        try:
            run_with_rate_limit_retry(
                supervisor.run, 
                "Plan and generate the tutorial series based on CODEBASE EXPLORATION.", 
                max_steps=50
            )
        except Exception as e:
            logger.error(f"Baseline Supervisor failed: {e}")
            if not self.dry_run:
                 raise
        
        # Collect output
        output_files = list(self.output_root.glob("*.md"))
        logger.info(f"Generated {len(output_files)} baseline tutorials.")
        self._sanitize_tutorial_outputs(output_files)
        return sorted(output_files, key=lambda p: p.name)

    def generate_with_supervisor(self) -> List[Path]:
        """Generate tutorials using the Supervisor Agent."""
        logger.info("Starting supervised tutorial generation...")
        
        # Reset directories if not dry run (similar to KB builder)
        if not self.dry_run:
            if self.sub_agents_root.exists():
                shutil.rmtree(self.sub_agents_root)
            self.sub_agents_root.mkdir(parents=True, exist_ok=True)
            
            if self.output_root.exists():
               shutil.rmtree(self.output_root)
            self.output_root.mkdir(parents=True, exist_ok=True)

        supervisor = self._create_supervisor_agent()
    
        # Retry loop for rate limits
        max_retries = 10
        retry_delay = 5.0  # seconds

        for attempt in range(1, max_retries + 1):
            try:
                supervisor.run("Plan and generate the tutorial series.", max_steps=50)
                break
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = "rate" in error_str or "429" in error_str or "exhausted" in error_str
                
                if is_rate_limit and attempt < max_retries:
                    logger.warning(
                        "Rate limit hit (attempt {}/{}). Waiting {}s before retry...",
                        attempt, max_retries, retry_delay
                    )
                    time.sleep(retry_delay)
                    # retry_delay = min(retry_delay * 1.5, 60.0)  # Fixed delay as requested
                else:
                    logger.error(f"Tutorial Supervisor failed: {e}")
                    if not self.dry_run:
                         raise
        
        # Collect output
        output_files = list(self.output_root.glob("*.md"))
        logger.info(f"Generated {len(output_files)} tutorials.")
        self._sanitize_tutorial_outputs(output_files)
        return sorted(output_files, key=lambda p: p.name)


__all__ = ["TutorialGenerator", "TutorialOutlineItem", "TutorialRunMetrics"]
