"""Unified content validation for tutorials and documentation.

Single source of truth for validation logic used by:
- evaluate_output_quality (supervisor tool)
- validate_tutorial_structure (generator function)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

__all__ = [
    "ValidationResult",
    "validate_content",
    "validate_mermaid_blocks",
    "validate_markdown_formatting",
    "sanitize_content",
]



def sanitize_content(content: str) -> str:
    """
    Auto-fix common tutorial quality issues.
    
    Fixes:
    - Removes "This is a generated document" banner
    - Fixes nested backticks in bold/italic (e.g., **`code`** -> **code**)
    - Fixes Mermaid |label[ -> |label|
    - Removes excessive whitespace
    
    Returns sanitized content.
    """
    result = content
    
    # 1. Remove "generated document" banner variations
    generated_patterns = [
        r"^\*{1,3}This is a generated document\.?\*{1,3}\s*\n*",
        r"^>\s*\*{1,3}This is a generated document\.?\*{1,3}\s*\n*",
        r"^>\s*This is a generated document\.?\s*\n*",
        r"^_+This is a generated document\.?_+\s*\n*",
    ]
    for pattern in generated_patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE | re.MULTILINE)
    
    # 2. Fix nested backticks in bold/italic: **`code`** -> **code**
    # Pattern matches: **`text`** or *`text`* or ***`text`***
    result = re.sub(r'\*{1,3}`([^`]+)`\*{1,3}', r'**\1**', result)
    
    # 3. Fix Mermaid |label[ -> |label|
    def fix_mermaid_labels(match):
        block = match.group(1)
        # Fix |label[ pattern
        fixed = re.sub(r'\|([^|\]]+)\[', r'|\1|', block)
        return f"```mermaid\n{fixed}\n```"
    
    result = re.sub(r'```mermaid\n(.*?)\n```', fix_mermaid_labels, result, flags=re.DOTALL)
    
    # 4. Remove excessive leading/trailing whitespace per line
    lines = result.split('\n')
    cleaned_lines = [line.rstrip() for line in lines]
    result = '\n'.join(cleaned_lines)
    
    # 5. Remove multiple consecutive blank lines (keep max 2)
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    
    return result.strip()


@dataclass
class ValidationResult:
    """Result of content validation."""
    
    is_valid: bool = True
    char_count: int = 0
    has_headers: bool = False
    has_code: bool = False
    balanced_code_blocks: bool = True
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "valid": self.is_valid,
            "char_count": self.char_count,
            "has_headers": self.has_headers,
            "has_code": self.has_code,
            "balanced_code_blocks": self.balanced_code_blocks,
            "issues": self.issues,
            "warnings": self.warnings,
        }


# Fallback patterns from LLM failures
FALLBACK_PATTERNS = (
    "_no response_",
    "no response",
    "_no response was received",
    "no response was received from the model",
)

# Truncation detection patterns (document starts mid-code)
MID_CODE_PATTERNS = [
    (r"^\s*\)", "closing parenthesis"),
    (r"^\s*\]", "closing bracket"),
    (r"^\s*\}", "closing brace"),
    (r'^\s*"""', "docstring"),
    (r"^\s*(return|continue|break|pass|raise)\b", "control statement"),
    (r"^\s*(else|elif|except|finally):", "branch statement"),
]

# Trailing garbage patterns
TRAILING_GARBAGE = ["))", "]]", "}}", "``", ";;", ",,"]


def validate_content(
    content: str,
    *,
    min_chars: int = 100,
    expected_title: str | None = None,
    check_mermaid: bool = True,
    strict_heading_start: bool = False,
) -> ValidationResult:
    """
    Unified content validation.
    
    Args:
        content: The markdown content to validate.
        min_chars: Minimum character count.
        expected_title: Expected title text (optional).
        check_mermaid: Whether to validate Mermaid syntax.
        strict_heading_start: If True, require doc to start with #.
    
    Returns:
        ValidationResult with issues and warnings.
    """
    result = ValidationResult()
    stripped = content.strip()
    result.char_count = len(stripped)
    
    # === CRITICAL ISSUES (make valid=False) ===
    
    # Empty content
    if not stripped:
        result.issues.append("Content is empty")
        result.is_valid = False
        return result
    
    # Placeholder/fallback text
    if any(pattern in stripped.lower() for pattern in FALLBACK_PATTERNS):
        result.issues.append("Content is placeholder/fallback text from model failure")
        result.is_valid = False
        return result
    
    # Minimum length
    if len(stripped) < min_chars:
        result.issues.append(f"Content too short ({len(stripped)} chars, need {min_chars})")
    
    # Check headers
    result.has_headers = any(line.startswith("#") for line in content.split("\n"))
    if not result.has_headers:
        result.issues.append("Missing markdown headers")
    
    # Check code blocks
    result.has_code = "```" in content
    if not result.has_code:
        result.issues.append("No code snippets included")
    
    # Balanced code blocks
    backtick_count = content.count("```")
    result.balanced_code_blocks = backtick_count % 2 == 0
    if not result.balanced_code_blocks:
        result.issues.append(f"Unbalanced code blocks ({backtick_count} ```) - likely truncated")
    
    # === STRUCTURAL CHECKS ===
    
    first_line = stripped.split("\n")[0].strip()
    
    # Document start check
    if strict_heading_start:
        if not first_line.startswith("#"):
            result.issues.append(f"Document doesn't start with heading. First: '{first_line[:40]}...'")
            # Check mid-code truncation
            for pattern, desc in MID_CODE_PATTERNS:
                if re.match(pattern, stripped):
                    result.issues.append(f"Document appears truncated (starts with {desc})")
                    break
    else:
        # Lenient: allow blockquotes, but warn if neither # nor >
        if not first_line.startswith("#") and not first_line.startswith(">"):
            result.warnings.append(f"Document doesn't start with heading: '{first_line[:40]}...'")
    
    # Expected title check
    if expected_title:
        title_lower = expected_title.lower()
        header_region = content[:500].lower()
        if title_lower not in header_region:
            title_words = [w for w in title_lower.split() if len(w) > 3]
            if not any(w in header_region for w in title_words[:2]):
                result.warnings.append(f"Expected title '{expected_title}' not found in header")
    
    # Trailing garbage
    content_end = stripped[-10:] if len(stripped) >= 10 else stripped
    for pattern in TRAILING_GARBAGE:
        if content_end.endswith(pattern):
            result.warnings.append(f"Document ends with garbage: '{pattern}'")
            break
    
    # Mermaid validation
    if check_mermaid and "```mermaid" in content:
        mermaid_issues = validate_mermaid_blocks(content)
        result.issues.extend(mermaid_issues)
    
    # Markdown formatting validation (bold/italic balance, truncation)
    markdown_issues = validate_markdown_formatting(content)
    for issue in markdown_issues:
        # Only truncation is critical; formatting balance is a warning (to avoid false positive retries)
        if "truncation" in issue.lower():
            result.issues.append(issue)
        else:
            result.warnings.append(issue)
    
    # Set validity based on issues
    result.is_valid = len(result.issues) == 0
    return result



def validate_mermaid_blocks(content: str) -> List[str]:
    """Validate Mermaid diagram syntax."""
    issues = []
    mermaid_pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
    
    for match in mermaid_pattern.finditer(content):
        block = match.group(1)
        block_start = content[:match.start()].count("\n") + 1
        
        # Check bracket balance
        for open_char, close_char, name in [("[", "]", "bracket"), ("{", "}", "brace"), ("(", ")", "paren")]:
            if block.count(open_char) != block.count(close_char):
                issues.append(f"Mermaid (line {block_start}): unbalanced {name}s")
        
        # Check pipe balance for edge labels
        pipe_count = block.count("|")
        if pipe_count % 2 != 0:
            issues.append(f"Mermaid (line {block_start}): unbalanced pipe labels ({pipe_count} |)")
        
        # Check for common syntax errors
        if re.search(r"\|[^\|]+\[", block):
            issues.append(f"Mermaid (line {block_start}): invalid |label[ pattern, should be |label|")
        
        # Check subgraph - nodes in subgraph must be referenced in main graph or have edges
        if "subgraph" in block:
            subgraph_match = re.search(r"subgraph\s+(\w+)", block)
            if subgraph_match:
                subgraph_name = subgraph_match.group(1)
                # Check if subgraph nodes have any edges to outside
                subgraph_content = re.search(r"subgraph.*?\n(.*?)\n\s*end", block, re.DOTALL)
                if subgraph_content:
                    inner = subgraph_content.group(1)
                    # Find nodes defined inside subgraph
                    inner_nodes = re.findall(r"(\w+)[\[\({]", inner)
                    # Check if any connect to outer graph
                    main_edges = re.sub(r"subgraph.*?end", "", block, flags=re.DOTALL)
                    has_connection = any(node in main_edges for node in inner_nodes)
                    if not has_connection and inner_nodes:
                        issues.append(
                            f"Mermaid (line {block_start}): subgraph '{subgraph_name}' nodes "
                            f"are not connected to main graph"
                        )
        
        # Check for empty graph (only comments or whitespace)
        graph_lines = [l for l in block.split("\n") if l.strip() and not l.strip().startswith("%%")]
        if len(graph_lines) < 2:
            issues.append(f"Mermaid (line {block_start}): diagram appears empty or minimal")
    
    return issues


def validate_markdown_formatting(content: str) -> List[str]:
    """Validate markdown bold/italic balance and detect truncated sentences."""
    issues = []
    
    # 1. Check bold/italic balance (** and *)
    # Count unescaped ** pairs
    bold_matches = re.findall(r'(?<!\*)\*\*(?!\*)', content)
    if len(bold_matches) % 2 != 0:
        issues.append(f"Unbalanced bold markers (**) - {len(bold_matches)} found, should be even")
    
    # Count unescaped * (not part of **)
    content_no_bold = re.sub(r'\*\*', '', content)
    # Remove bullet points (e.g. "* Item" or "  * Item") to avoid false positives
    content_no_bullets = re.sub(r'^\s*\*\s', '', content_no_bold, flags=re.MULTILINE)
    italic_matches = re.findall(r'(?<!\*)\*(?!\*)', content_no_bullets)
    if len(italic_matches) % 2 != 0:
        issues.append(f"Unbalanced italic markers (*) - {len(italic_matches)} found, should be even")
    
    # 2. Detect truncated sentences ending with backtick
    truncated_patterns = [
        (r'`\s*$', "ends with unclosed backtick"),
        # (r'`\s*\n\s*#{1,6}\s+', "backtick followed directly by heading (truncated)"), # REMOVED: False positive
        (r'\*\*\s*\n\s*#{1,6}\s+', "bold followed directly by heading (truncated)"),
        # (r':\s*`\s*\n', "colon-backtick-newline (truncated sentence)"), # REMOVED: False positive
    ]
    
    for pattern, desc in truncated_patterns:
        if re.search(pattern, content):
            issues.append(f"Possible truncation: {desc}")
    
    # 3. Detect "(excerpt):" pattern without closing **
    excerpt_issues = re.findall(r'\*\*[^*]+\(excerpt\):?\s*\n', content)
    if excerpt_issues:
        issues.append(f"Found {len(excerpt_issues)} unclosed bold labels ending with (excerpt):")
    
    # 4. Check for code blocks with unclosed leading line (missing ```)
    # Pattern: **Output: followed by code-like content without proper ```
    code_after_label = re.findall(r'\*\*[^*]+:\s*\n```\w*\n', content)
    label_without_wrapper = re.findall(r'\*\*[^*]+:\s*\n[^`\n]+\n', content)
    # This is a heuristic - check if there's a label followed by code-ish content without ```
    
    return issues



def validate_heading_sequence(content: str) -> List[str]:
    """Check that numbered headings follow logical sequence."""
    issues = []
    heading_pattern = re.compile(r"^(#{1,6})\s+(\d+\.?\s+)?(.+)$", re.MULTILINE)
    
    prev_level = 0
    for match in heading_pattern.finditer(content):
        level = len(match.group(1))
        # Skip if jumping more than 1 level down
        if level > prev_level + 1 and prev_level > 0:
            issues.append(f"Heading level jump: H{prev_level} -> H{level} (skipped H{prev_level + 1})")
        prev_level = level
    
    return issues


def validate_code_block_completeness(content: str) -> List[str]:
    """Check for truncated code blocks."""
    issues = []
    code_pattern = re.compile(r"```(\w*)\n(.*?)\n```", re.DOTALL)
    
    for match in code_pattern.finditer(content):
        lang = match.group(1).lower()
        code = match.group(2)
        
        if lang in ("python", "py"):
            # Check for unclosed structures
            if code.count("def ") > code.count("return") + code.count("pass") + code.count("..."):
                issues.append("Python code may be truncated (more defs than returns)")
            if code.rstrip().endswith(":"):
                issues.append("Python code ends with ':' - likely truncated")
    
    return issues
