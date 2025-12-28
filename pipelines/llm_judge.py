"""LLM-as-judge evaluator for tutorial quality assessment.

Usage:
  python -m pipelines.llm_judge --tutorials data/deep_agent_output/xyz/tutorials

This module evaluates tutorials using multiple LLM models in a blind fashion.
Each model scores tutorials on: Accuracy, Completeness, Clarity, Structure, Diagrams.
Results are aggregated into a comprehensive report.
"""

from __future__ import annotations

import os
import argparse
import glob
from pathlib import Path
from loguru import logger
from utils.llm_factory import create_model
from smolagents import LiteLLMModel
from smolagents.agents import ToolCallingAgent
from toolkits.scoped_filesystem_toolkit import build_scoped_tools



import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from statistics import mean

try:
    from litellm import completion
    from litellm.exceptions import RateLimitError
except ImportError as exc:
    raise ImportError(
        "litellm is required for LLM judging. Install via `pip install litellm`."
    ) from exc

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("llm_judge")


# Judge models - sequential evaluation for diverse perspectives
JUDGE_MODELS = [
    "vertex_ai/gemini-2.5-pro",
]

# External API support (Colab-hosted model)
EXTERNAL_API_URL = os.environ.get("LLM_JUDGE_URL", None)

def check_external_api_health(url: str = None) -> bool:
    """Check if the external LLM API is reachable."""
    import requests
    
    api_url = url or EXTERNAL_API_URL
    if not api_url:
        return False
    
    try:
        response = requests.get(f"{api_url.rstrip('/')}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ External API healthy: {data.get('model', 'unknown')}")
            return True
        else:
            logger.warning(f"External API returned status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"External API health check failed: {e}")
        return False


def call_external_evaluate_endpoint(content_a: str, content_b: str, codebase_context: str, max_retries: int = 3) -> dict:
    """Call the custom /evaluate endpoint on the Colab-hosted GPT-OSS-20B model.
    
    This uses the dedicated evaluation endpoint which handles prompt formatting
    and returns structured JSON results.
    """
    import requests
    import time
    
    url = EXTERNAL_API_URL
    if not url:
        raise ValueError("LLM_JUDGE_URL environment variable not set")
    
    endpoint = f"{url.rstrip('/')}/evaluate"
    
    # Truncate content to fit model context
    payload = {
        "content_a": content_a[:6000],
        "content_b": content_b[:6000],
        "codebase_context": codebase_context[:3000]
    }
    
    logger.info(f"Calling external evaluate endpoint: {endpoint}")
    logger.info(f"Payload sizes: A={len(payload['content_a'])} B={len(payload['content_b'])} ctx={len(payload['codebase_context'])}")
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(endpoint, json=payload, timeout=180)
            
            if response.status_code != 200:
                raise RuntimeError(f"API returned status {response.status_code}: {response.text[:200]}")
            
            data = response.json()
            response_text = data.get("response", "")
            
            logger.info(f"Raw response ({len(response_text)} chars): {response_text[:500]}...")
            
            # Parse JSON from response
            # Strip markdown fences if present
            response_text = re.sub(r"^```(?:json)?\s*", "", response_text, flags=re.IGNORECASE).strip()
            response_text = re.sub(r"\s*```$", "", response_text).strip()
            
            # Try to parse JSON
            try:
                result = json.loads(response_text)
                result["model"] = "gpt-oss-20b"
                return result
            except json.JSONDecodeError:
                # Try to find JSON object in response
                match = re.search(r'\{[^{}]*"winner"[^{}]*\}', response_text, re.DOTALL)
                if match:
                    result = json.loads(match.group(0))
                    result["model"] = "gpt-oss-20b"
                    return result
                raise RuntimeError(f"Could not parse JSON from response: {response_text[:200]}")
                
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout (attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                time.sleep(5 * attempt)
                continue
            raise
        except Exception as e:
            logger.error(f"Evaluate endpoint failed (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(3 * attempt)
                continue
            raise
    
    raise RuntimeError("Max retries exceeded for evaluate endpoint")


def call_external_judge_api(messages: list, max_tokens: int = 2048) -> str:
    """Call the external LLM Judge API using LiteLLM (Colab-hosted GPT-OSS-20B)."""
    import litellm
    
    url = EXTERNAL_API_URL
    if not url:
        raise ValueError("LLM_JUDGE_URL environment variable not set")
    
    # LiteLLM appends /chat/completions, so we need /v1 in the base
    api_base = url.rstrip("/") + "/v1"
    
    logger.info(f"Calling external judge API via LiteLLM: {api_base}")
    logger.info(f"Request: {len(messages)} messages, max_tokens={max_tokens}")
    
    # Log full message content
    for i, msg in enumerate(messages):
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        logger.info(f"[REQ MSG {i}] role={msg.get('role', '?')}, content ({len(content)} chars):\n{content[:2000]}{'...[truncated]' if len(content) > 2000 else ''}")
    
    # Use LiteLLM with custom api_base for OpenAI-compatible endpoints
    response = litellm.completion(
        model="openai/gpt-oss-20b",
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.1,
        api_base=api_base,
        api_key="dummy"  # Required by LiteLLM but ignored by our server
    )
    
    content = response.choices[0].message.content
    logger.info(f"[RESPONSE] ({len(content)} chars):\n{content[:2000]}{'...[truncated]' if len(content) > 2000 else ''}")
    
    return content


class ExternalAPIModel:
    """A smolagents-compatible model wrapper that uses LiteLLM for external API."""
    
    def __init__(self, api_url: str = None):
        self.api_url = api_url or EXTERNAL_API_URL
        if not self.api_url:
            raise ValueError("LLM_JUDGE_URL environment variable not set and no api_url provided")
        self.model_id = "gpt-oss-20b"
        # Attributes expected by smolagents
        self.last_input_token_count = 0
        self.last_output_token_count = 0
    
    def _call_api(self, messages, max_tokens=4096):
        """Internal method to call the external API via LiteLLM."""
        import litellm
        
        # Convert messages to list of dicts if needed
        formatted_messages = []
        for msg in messages:
            if hasattr(msg, "role") and hasattr(msg, "content"):
                content = ""
                if msg.content:
                    content = str(msg.content) if not isinstance(msg.content, list) else str(msg.content)
                formatted_messages.append({"role": msg.role, "content": content})
            elif isinstance(msg, dict):
                formatted_messages.append(msg)
            else:
                formatted_messages.append({"role": "user", "content": str(msg)})
        
        api_base = self.api_url.rstrip("/") + "/v1"
        
        # Add ngrok header to bypass browser warning page
        extra_headers = {
            "ngrok-skip-browser-warning": "true"
        }
        
        response = litellm.completion(
            model="openai/gpt-oss-20b",
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=0.1,
            api_base=api_base,
            api_key="dummy",
            extra_headers=extra_headers
        )
        
        content = response.choices[0].message.content
        
        # Update token counts
        self.last_input_token_count = response.usage.prompt_tokens if response.usage else 0
        self.last_output_token_count = response.usage.completion_tokens if response.usage else 0
        
        return content
    
    def __call__(self, messages, stop_sequences=None, grammar=None, tools_to_call_from=None, **kwargs):
        """Call the external API and return a response compatible with smolagents."""
        from smolagents.models import ChatMessage
        
        max_tokens = kwargs.get("max_tokens", 4096)
        content = self._call_api(messages, max_tokens)
        
        # Return a ChatMessage-like object
        return ChatMessage(role="assistant", content=content)
    
    def generate(self, messages, stop_sequences=None, grammar=None, tools_to_call_from=None, **kwargs):
        """Generate method required by smolagents ToolCallingAgent."""
        from smolagents.models import ChatMessage
        
        max_tokens = kwargs.get("max_tokens", 4096)
        content = self._call_api(messages, max_tokens)
        
        # Return a ChatMessage
        return ChatMessage(role="assistant", content=content)

# Evaluation criteria
CRITERIA = ["accuracy", "completeness", "clarity", "structure", "diagrams"]

# Truncation limits
MAX_TUTORIAL_CHARS = 50000
MAX_CODEBASE_CONTEXT_CHARS = 50000


EVALUATION_PROMPT = """You are an expert technical documentation reviewer. Evaluate this tutorial for a software codebase.

## Codebase Context
{codebase_context}

## Tutorial to Evaluate
{tutorial_content}

## Evaluation Criteria

Score each criterion from 1-5:
- **accuracy**: Are code snippets and technical details correct? Do they match the actual codebase?
- **completeness**: Does the tutorial cover all important aspects of the topic?
- **clarity**: Is the writing clear, well-organized, and easy to follow?
- **structure**: Are headings logical? Is there good flow from intro to conclusion?
- **diagrams**: Are Mermaid diagrams present, syntactically correct, and helpful?

## Response Format

Return ONLY valid JSON (no markdown fences):
{{
    "scores": {{
        "accuracy": <1-5>,
        "completeness": <1-5>,
        "clarity": <1-5>,
        "structure": <1-5>,
        "diagrams": <1-5>
    }},
    "overall": <1-5>,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "suggestions": ["suggestion1", "suggestion2"],
    "rationale": "Brief explanation of your scores"
}}
"""

AGENT_JUDGE_PROMPT = """You are a meticulous technical documentation judge conducting a blind A/B test.
Your goal: Determine which Tutorial Series better teaches developers how to use this codebase.

## Your Tools
- `get_codebase_tree`: See the project structure
- `read_codebase_file`: Read source files AND tutorial files

## Tutorial Locations
### Series A
{content_a}

### Series B
{content_b}

---

## MANDATORY WORKFLOW (Follow Exactly)

### Step 1: Understand the Codebase
1. Call `get_codebase_tree` to see the project structure.
2. Read the main entry point (e.g., `index.ts`, `main.py`, `lib/core.ts`).
3. Identify the **key exported functions/classes** that users would import.

### Step 2: Read ALL Tutorials (REQUIRED)
1. Read EVERY `.md` file listed in Series A.
2. Read EVERY `.md` file listed in Series B.
3. Do NOT skip any file. Do NOT assume content from filenames.

### Step 3: Fact-Check Code Snippets
For each series, verify at least 3 code examples:
- Are import paths correct? (e.g., `from pkg import X` - does `X` exist?)
- Are function signatures accurate? (e.g., `encode(data, options)` - check actual params)
- Are API behaviors described correctly?

### Step 4: Score Each Criterion

**FIDELITY (1-5)**: Code Accuracy
| Score | Meaning |
|-------|---------|
| 5 | All code snippets are copy-paste correct. Imports, functions, params match codebase exactly. |
| 4 | Minor issues (e.g., optional param omitted) but code would run. |
| 3 | Some inaccuracies but core concepts correct. |
| 2 | Multiple errors. Code would fail or mislead users. |
| 1 | Fabricated APIs, hallucinated functions, fundamentally wrong. |

**PEDAGOGY (1-5)**: Teaching Quality
| Score | Meaning |
|-------|---------|
| 5 | Perfect progression: basics → intermediate → advanced. Clear explanations with diagrams. |
| 4 | Good flow with minor gaps. Concepts build logically. |
| 3 | Adequate but jumps around or assumes knowledge. |
| 2 | Confusing order. Hard to follow for beginners. |
| 1 | No clear structure. Random topics. |

**COVERAGE (1-5)**: Completeness (JUDGE BY CONTENT, NOT FILE COUNT!)
| Score | Meaning |
|-------|---------|
| 5 | Covers all major features: core APIs, advanced options, CLI (if exists), streaming (if exists). |
| 4 | Covers most features. Minor gaps. |
| 3 | Covers basics well but misses significant features. |
| 2 | Very shallow. Only scratches the surface. |
| 1 | Barely covers anything useful. |

---

## CRITICAL REMINDERS
- **File count ≠ Coverage**. A 3-file series can beat a 6-file series if content is denser.
- **Actually read the files**. Never assume content from filenames alone.
- **Verify claims with tools**. If a tutorial says "use `encodeStream()`", check if that function exists.

---

## FINAL OUTPUT (Required)
After completing all steps, call `final_answer` with this exact structure:

```python
final_answer({{
    "winner": "A" or "B" or "Tie",
    "fidelity_A": <1-5>,
    "fidelity_B": <1-5>,
    "pedagogy_A": <1-5>,
    "pedagogy_B": <1-5>,
    "coverage_A": <1-5>,
    "coverage_B": <1-5>,
    "verified_snippets": [
        {{"series": "A", "claim": "import X from pkg", "verified": true/false}},
        {{"series": "B", "claim": "encode(data, opts)", "verified": true/false}}
    ],
    "rationale": "Detailed explanation citing specific evidence from your file reads..."
}})
```
"""

COMPARE_PROMPT = """You are an expert technical documentation reviewer.
Your task is to compare two versions of a tutorial for the same topic and decide which one is better.

## Codebase Context
{codebase_context}

## Tutorial Version A
{content_a}

## Tutorial Version B
{content_b}

## Instructions
1. Read the Codebase Context to understand the topic.
2. Read both tutorials.
3. Compare them based on:
    - **Accuracy**: Does it match the code?
    - **Clarity**: Is it easy to understand?
    - **Completeness**: Does it solve the problem?
    - **Code Quality**: Are examples robust?

## Response Format
Return ONLY valid JSON (no markdown fences):
{{
    "winner": "A" or "B" or "Tie",
    "rationale": "Explanation...",
    "scores": {{
        "A": <1-5>,
        "B": <1-5>
    }}
}}
"""

SERIES_COMPARE_PROMPT = """You are judging tutorial quality by checking if code matches the actual codebase.

Available files to read:
CODEBASE: {codebase_files}
TUTORIALS A: {series_a_files}
TUTORIALS B: {series_b_files}

To read a file, just say: I want to read <filename>

Start by reading a few key source files, then read tutorials from both series.

When done, output JSON: {{"winner":"A or B","fidelity_A":1-5,"fidelity_B":1-5,"pedagogy_A":1-5,"pedagogy_B":1-5,"coverage_A":1-5,"coverage_B":1-5,"rationale":"why"}}"""

def evaluate_series_external(codebase_root: str | Path, baseline_paths: List[Path], deep_paths: List[Path]) -> dict | None:
    """Compare tutorials using external GPT-OSS-20B API with tool-calling simulation.
    
    Like the Gemini agentic pipeline: give model a prompt with file list and tool
    instructions, model requests files via READ: commands, we provide them iteratively.
    """
    import requests
    import time
    
    codebase_root = Path(codebase_root) if isinstance(codebase_root, str) else codebase_root
    
    # Check API health first
    if not check_external_api_health():
        return {"winner": "Error", "rationale": "External API is not reachable. Check LLM_JUDGE_URL and ensure Colab notebook is running."}
    
    url = EXTERNAL_API_URL
    if not url:
        return {"winner": "Error", "rationale": "LLM_JUDGE_URL not set"}
    
    endpoint = f"{url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true"
    }
    
    # Filter tutorial files
    series_a_files = sorted([p for p in baseline_paths if p.name.endswith('.md') and not p.name.startswith('spawned')])
    series_b_files = sorted([p for p in deep_paths if p.name.endswith('.md') and not p.name.startswith('spawned') and p.name != 'tutorial_plan.md'])
    
    logger.info(f"Series A: {len(series_a_files)} tutorials, Series B: {len(series_b_files)} tutorials")
    
    # Build file index for quick lookup
    file_index = {}
    
    # Add codebase files to index
    codebase_files_list = []
    for fp in codebase_root.rglob("*"):
        if fp.is_file() and not any(skip in str(fp) for skip in ["__pycache__", ".git", "venv", "node_modules", ".pyc"]):
            try:
                rel = str(fp.relative_to(codebase_root))
                file_index[fp.name] = fp
                file_index[rel] = fp
                if rel.endswith(('.py', '.ts', '.js', '.md')):
                    codebase_files_list.append(rel)
            except:
                pass
    
    # Add tutorials to index with prefixes
    series_a_names = []
    for p in series_a_files:
        file_index[f"A/{p.name}"] = p
        file_index[f"series_a/{p.name}"] = p
        series_a_names.append(f"A/{p.name}")
    
    series_b_names = []
    for p in series_b_files:
        file_index[f"B/{p.name}"] = p
        file_index[f"series_b/{p.name}"] = p
        series_b_names.append(f"B/{p.name}")
    
    # Build SMALL initial prompt - just instructions and file list, NO content
    prompt = f"""You are a technical documentation judge comparing two tutorial series.

To read files, output EXACTLY this format on its own line:
READ: A/01_getting_started.md

## AVAILABLE TUTORIALS

Series A (Baseline):
{chr(10).join(series_a_names)}

Series B (Deep Agent):
{chr(10).join(series_b_names)}

Codebase files: {', '.join(codebase_files_list[:10])}

## TASK
1. Read tutorials using READ: commands (one per line)
2. Compare and score: FIDELITY, PEDAGOGY, COVERAGE (1-5 each)
3. Output JSON when done

## EXAMPLE
To read a file, say:
READ: A/01_getting_started.md

When finished, output:
{{"winner": "A", "fidelity_A": 4, "fidelity_B": 3, "pedagogy_A": 4, "pedagogy_B": 3, "coverage_A": 4, "coverage_B": 3, "rationale": "explanation"}}

Start now. Read the first tutorial:
READ: {series_a_names[0] if series_a_names else 'A/01_getting_started.md'}
"""

    logger.info(f"Initial prompt: {len(prompt)} chars")
    
    messages = [{"role": "user", "content": prompt}]
    max_turns = 30
    files_read = set()
    
    # Pre-load first tutorial to show the model how it works
    if series_a_files:
        first_file = series_a_files[0]
        first_name = f"A/{first_file.name}"
        try:
            first_content = first_file.read_text(errors='replace')[:4000]
            messages.append({"role": "assistant", "content": f"READ: {first_name}"})
            messages.append({"role": "user", "content": f"=== {first_name} ===\n{first_content}"})
            files_read.add(first_name)
            logger.info(f"Pre-loaded: {first_name} ({len(first_content)} chars)")
        except:
            pass
    
    for turn in range(max_turns):
        logger.info(f"Turn {turn + 1}/{max_turns}, files read: {len(files_read)}")
        
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json={
                    "messages": messages,
                    "max_tokens": 1500,
                    "temperature": 0.1
                },
                timeout=120
            )
            
            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text[:200]}")
                time.sleep(3)
                continue
            
            data = response.json()
            response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not response_text:
                logger.warning("Empty response, retrying...")
                time.sleep(2)
                continue
            
            logger.info(f"Response ({len(response_text)} chars): {response_text[:200]}...")
            messages.append({"role": "assistant", "content": response_text})
            
            # Check for final JSON result
            json_match = re.search(r'\{[^{}]*"winner"[^{}]*\}', response_text, re.DOTALL)
            if json_match and len(files_read) >= 4:  # Only accept JSON after reading files
                try:
                    result = json.loads(json_match.group(0))
                    result["model"] = "gpt-oss-20b"
                    result["turns"] = turn + 1
                    result["files_read"] = list(files_read)
                    logger.info(f"✅ Evaluation complete in {turn + 1} turns: Winner={result.get('winner')}")
                    return result
                except json.JSONDecodeError:
                    pass
            
            # Parse READ: commands - try multiple patterns
            read_requests = re.findall(r'READ:\s*([^\n,]+)', response_text, re.IGNORECASE)
            
            # Also try to find file paths mentioned without READ: prefix
            if not read_requests:
                # Look for A/filename.md or B/filename.md patterns
                path_patterns = re.findall(r'[AB]/[^\s,\n]+\.md', response_text)
                if path_patterns:
                    read_requests = path_patterns[:2]
            
            # Also try to find {"path": "..."} patterns
            if not read_requests:
                json_paths = re.findall(r'"path":\s*"([^"]+)"', response_text)
                if json_paths:
                    read_requests = json_paths[:2]
            
            list_requests = re.findall(r'LIST:\s*([^\n,]+)', response_text, re.IGNORECASE)
            
            tool_outputs = []
            
            # Handle READ requests
            for filename in read_requests[:2]:  # Max 2 files per turn
                filename = filename.strip().strip('"\'`')
                fp = file_index.get(filename)
                if fp and fp.exists():
                    try:
                        content = fp.read_text(errors='replace')[:4000]
                        tool_outputs.append(f"=== {filename} ===\n{content}")
                        files_read.add(filename)
                        logger.info(f"READ: {filename} ({len(content)} chars)")
                    except Exception as e:
                        tool_outputs.append(f"=== {filename} ===\nError reading: {e}")
                else:
                    # Try fuzzy match
                    matches = [k for k in file_index.keys() if filename.lower() in k.lower()]
                    if matches:
                        tool_outputs.append(f"File '{filename}' not found. Did you mean: {', '.join(matches[:5])}?")
                    else:
                        tool_outputs.append(f"File '{filename}' not found.")
            
            # Handle LIST requests
            for dirname in list_requests[:1]:
                dirname = dirname.strip().strip('"\'`')
                dir_path = codebase_root / dirname if dirname else codebase_root
                if dir_path.exists() and dir_path.is_dir():
                    files = [f.name for f in dir_path.iterdir() if f.is_file()][:20]
                    dirs = [f.name + "/" for f in dir_path.iterdir() if f.is_dir()][:10]
                    tool_outputs.append(f"=== LIST: {dirname} ===\nFiles: {', '.join(files)}\nDirs: {', '.join(dirs)}")
            
            if tool_outputs:
                messages.append({"role": "user", "content": "\n\n".join(tool_outputs)})
            else:
                # No tool requests - prompt model to continue
                if len(files_read) < 4:
                    messages.append({"role": "user", "content": f"You've read {len(files_read)} files. Please read more tutorials using READ: commands. Try: READ: {series_a_names[0] if series_a_names else 'A/...'}"})
                else:
                    messages.append({"role": "user", "content": "You have read enough files. Please provide your final JSON evaluation now."})
            
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout on turn {turn + 1}")
            time.sleep(5)
            continue
        except Exception as e:
            logger.error(f"Error on turn {turn + 1}: {e}")
            time.sleep(2)
            continue
    
    logger.warning("Max turns reached without final result")
    return {"winner": "Error", "rationale": f"Max turns reached. Read {len(files_read)} files: {list(files_read)}", "model": "gpt-oss-20b"}


def evaluate_series(model_id: str, codebase_context: str, baseline_paths: List[Path], deep_paths: List[Path]) -> dict | None:
    """Compare two complete sets of tutorials using an Agentic Judge."""
    
    # Check codebase_context - we actually interpret it as "codebase_root path" for the agent?
    # CLI passes "full_context" string currently.
    # Refactoring: CLI needs to pass the ROOT PATH, not the content string.
    # But wait, `evaluate_series` signature in CLI call (Step 935) was `evaluate_series(model_id, full_context, ...)`
    # I need to change CLI to pass ROOT PATH.
    # For now, I will extract root path from the FIRST deep_path parent's parent if not passed explicitly?
    # No, I should fix the signature. But let's look at `codebase_context` arg.
    # If the user passed `full_context` string, that won't work for `build_scoped_tools`.
    # I will assume `codebase_context` MIGHT be a Path object or a string.
    # I will update CLI to pass `codebase_root` (Path) instead of `full_context`.
    
    # Logic to locate codebase root if passed as string (won't work). 
    # I will assume CLI update is coming next.
    # For now, assume `codebase_context` is a Path or valid path string.
    
    # Logic to locate codebase root
    candidate_root = Path(codebase_context) if isinstance(codebase_context, (str, Path)) else None
    if not candidate_root or (isinstance(candidate_root, Path) and not candidate_root.exists()):
         # Fallback inference
         candidate_root = deep_paths[0].parent.parent.parent.parent / "agent_workspace" / deep_paths[0].parent.parent.name
         logger.warning(f"Inferred codebase root for Agent Judge: {candidate_root}")
    
    if not candidate_root.exists():
        logger.error(f"Cannot find codebase root at {candidate_root} for agent tools.")
        return {"winner": "Error", "rationale": "Codebase root not found for agent tools."}
        
    logger.info(f"Agent Judge initializing with tools for: {candidate_root}")

    # Setup Evaluation Context in Codebase Root
    import shutil
    
    # We create a temporary evaluation directory inside the codebase root
    # This allows the agent to access them using the scoped tools (which are bound to codebase_root)
    eval_root = candidate_root / "_evaluation_temp"
    dir_a = eval_root / "Series_A"
    dir_b = eval_root / "Series_B"
    
    # Clean/Create dirs
    if eval_root.exists(): shutil.rmtree(eval_root)
    dir_a.mkdir(parents=True)
    dir_b.mkdir(parents=True)
    
    # Copy files
    files_a_names = []
    files_b_names = []
    
    for p in baseline_paths:
        dest = dir_a / p.name
        shutil.copy2(p, dest)
        files_a_names.append(str(dest.relative_to(candidate_root)))

    for p in deep_paths:
        dest = dir_b / p.name
        shutil.copy2(p, dest)
        files_b_names.append(str(dest.relative_to(candidate_root)))
        
    logger.info(f"Staged tutorials in {eval_root}")
    
    # Construct Listing Strings for Prompt
    list_a = "\n".join([f"- {n}" for n in sorted(files_a_names)])
    list_b = "\n".join([f"- {n}" for n in sorted(files_b_names)])

    prompt = AGENT_JUDGE_PROMPT.format(
        content_a=f"Files located at:\n{list_a}\n\n(Use `read_codebase_file` to read them.)",
        content_b=f"Files located at:\n{list_b}\n\n(Use `read_codebase_file` to read them.)"
    )
    
    # Initialize Agent
    tools = build_scoped_tools(
        codebase_root=str(candidate_root),
        workspace_root=str(candidate_root), # Allow reading everything in root
        allow_tree=True,
        allow_directory_listing=True,
        allow_writes=False # Judge is read-only
    )
    
    # Use ExternalAPIModel for colab, otherwise use create_model
    if model_id in ("colab", "gpt-oss-20b", "external"):
        model = ExternalAPIModel(api_url=EXTERNAL_API_URL)
        logger.info(f"Using ExternalAPIModel with URL: {EXTERNAL_API_URL}")
        use_code_agent = True  # CodeAgent parses tool calls from code, no need for parse_tool_calls
    else:
        model = create_model(model_id=model_id)
        use_code_agent = False
    
    # Step callback to add delay between steps
    import time as time_module
    def step_delay_callback(step_log):
        time_module.sleep(0.5)  # 0.5 second delay between steps
    
    # Use CodeAgent for external API (parses tool calls from code blocks)
    # Use ToolCallingAgent for models with native tool calling
    if use_code_agent:
        from smolagents import CodeAgent
        agent = CodeAgent(
            tools=tools,
            model=model,
            max_steps=50,
            step_callbacks=[step_delay_callback],
        )
    else:
        agent = ToolCallingAgent(
            tools=tools,
            model=model,
            max_steps=50,
            step_callbacks=[step_delay_callback],
        )

    max_retries = 10
    retry_delay = 5  # Start with 5 seconds
    
    for attempt in range(max_retries):
        try:
            response = agent.run(prompt)
            
            # Cleanup
            if eval_root.exists(): shutil.rmtree(eval_root)
            
            # If agent uses final_answer(dict), response is the dict!
            if isinstance(response, dict):
                response["file_name"] = "Comparison (Agentic)"
                response["model"] = model_id
                return response
            
            # Try to parse result from agent content
            content = str(response)
            
            # Try JSON parse
            import json
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    data["file_name"] = "Comparison (Agentic)"
                    data["model"] = model_id
                    return data
            except: pass
            
            # Try to find JSON in the content
            json_pattern = r'\{[^{}]*"winner"[^{}]*\}'
            import re
            match = re.search(json_pattern, content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                    if isinstance(data, dict):
                        data["file_name"] = "Comparison (Agentic)"
                        data["model"] = model_id
                        return data
                except: pass

            # Try AST on raw content?
            try:
                import ast
                data = ast.literal_eval(content)
                if isinstance(data, dict):
                    data["file_name"] = "Comparison (Agentic)"
                    data["model"] = model_id
                    return data
            except: pass
            
            return {"file_name": "Comparison", "model": model_id, "winner": "Error", "rationale": f"JSON parse error: {content[:200]}"}
            
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "rate" in error_str or "resource_exhausted" in error_str
            
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                import time
                time.sleep(wait_time)
                continue
            
            logger.error(f"Agentic comparison failed: {e}")
            # Cleanup on error
            if eval_root.exists(): shutil.rmtree(eval_root)
            return {"file_name": "Comparison", "model": model_id, "winner": "Error", "rationale": str(e)}


def evaluate_pair(model_id: str, file_name: str, codebase_context: str, path_a: Path, path_b: Path) -> dict | None:
    """Compare two tutorials using an LLM."""
    content_a = path_a.read_text(errors="replace") if path_a.exists() else "MISSING"
    content_b = path_b.read_text(errors="replace") if path_b.exists() else "MISSING"
    
    if content_a == "MISSING" and content_b == "MISSING":
        return None
        
    truncate_len = 6000 # Shorter to fit two into context
    
    prompt = COMPARE_PROMPT.format(
        codebase_context=codebase_context,
        content_a=_truncate(content_a, truncate_len),
        content_b=_truncate(content_b, truncate_len)
    )
    
    try:
        # Check if using external Colab API
        if model_id in ("colab", "gpt-oss-20b", "external"):
            content = call_external_judge_api(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048
            )
        else:
            from utils.llm_factory import create_model
            model = create_model(model_id=model_id)
            
            response = model(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096
            )
            
            # smolagents Model returns ChatMessage directly
            if hasattr(response, "content"):
                 content = str(response.content).strip()
            else:
                 # Fallback for other potential return types
                 content = str(response).strip()
        
        if content in ["None", ""] or content is None:
            logger.warning(f"Empty response for {file_name}. Retry suggested.")
            return {"file_name": file_name, "model": model_id, "winner": "Error", "rationale": "Empty/Blocked response from model"}

        # Strip markdown fences
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE).strip()
        content = re.sub(r"\s*```$", "", content).strip()
        
        # Simple cleanup for common JSON errors
        content = re.sub(r",\s*\}", "}", content) # Trailing comma in object
        content = re.sub(r",\s*\]", "]", content) # Trailing comma in list

        try:
            data = json.loads(content)
            data["file_name"] = file_name
            data["model"] = model_id
            return data
        except json.JSONDecodeError as exc:
            # Fallback: Try to find the first JSON object in the string
            match = re.search(r"(\{.*\})", content, flags=re.DOTALL)
            if match:
                 try:
                    c_fixed = match.group(1)
                    c_fixed = re.sub(r",\s*\}", "}", c_fixed)
                    data = json.loads(c_fixed)
                    data["file_name"] = file_name
                    data["model"] = model_id
                    return data
                 except:
                    pass
            
            logger.error(f"JSON Parse Error for {file_name}.\nError: {exc}\nContent:\n{content}")
            return {"file_name": file_name, "model": model_id, "winner": "Error", "rationale": f"JSON parse error. Content: {content[:200]}"}
            
    except Exception as e:
        logger.error(f"Comparison failed for {file_name}: {e}")
        return {"file_name": file_name, "model": model_id, "winner": "Error", "rationale": str(e)}


@dataclass
class TutorialScore:
    """Score for a single tutorial from a single model."""
    tutorial_name: str
    model: str
    scores: Dict[str, int] = field(default_factory=dict)
    overall: float = 0.0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class AggregatedTutorialScore:
    """Aggregated scores for a tutorial across all models."""
    tutorial_name: str
    avg_scores: Dict[str, float] = field(default_factory=dict)
    avg_overall: float = 0.0
    all_strengths: List[str] = field(default_factory=list)
    all_weaknesses: List[str] = field(default_factory=list)
    all_suggestions: List[str] = field(default_factory=list)
    model_scores: List[TutorialScore] = field(default_factory=list)


@dataclass
class EvaluationReport:
    """Complete evaluation report."""
    tutorial_dir: str
    codebase: str
    models_used: List[str] = field(default_factory=list)
    tutorials: List[AggregatedTutorialScore] = field(default_factory=list)
    overall_avg: float = 0.0
    generated_at: str = ""


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text while preserving beginning and end."""
    if len(text) <= max_chars:
        return text
    half = (max_chars - 50) // 2
    return text[:half] + "\n\n... [truncated] ...\n\n" + text[-half:]


def _build_codebase_context(codebase_root: Path, max_chars: int = MAX_CODEBASE_CONTEXT_CHARS) -> str:
    """Build a context string from codebase files."""
    context_parts = [f"# Codebase: {codebase_root.name}\n"]
    
    # Prioritize README and key files
    priority_files = ["README.md", "readme.md", "README.rst", "setup.py", "pyproject.toml", "package.json"]
    
    files_added = 0
    total_chars = 0
    
    for pf in priority_files:
        fp = codebase_root / pf
        if fp.exists() and fp.is_file():
            try:
                content = fp.read_text(encoding="utf-8")[:2000]
                context_parts.append(f"\n## {pf}\n```\n{content}\n```")
                total_chars += len(content)
                files_added += 1
            except Exception:
                continue
    
    # Add some source files if space allows
    if total_chars < max_chars - 2000:
        for ext in [".py", ".ts", ".js"]:
            for fp in codebase_root.rglob(f"*{ext}"):
                if files_added >= 10 or total_chars >= max_chars:
                    break
                if any(skip in str(fp) for skip in ["node_modules", "__pycache__", ".git", "venv", "test"]):
                    continue
                try:
                    content = fp.read_text(encoding="utf-8")[:1500]
                    rel_path = fp.relative_to(codebase_root)
                    context_parts.append(f"\n## {rel_path}\n```\n{content}\n```")
                    total_chars += len(content)
                    files_added += 1
                except Exception:
                    continue
    
    return _truncate("\n".join(context_parts), max_chars)





def _call_judge(
    model: str,
    tutorial_content: str,
    codebase_context: str,
    temperature: float = 0.0,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Call a single judge model and parse response."""
    prompt = EVALUATION_PROMPT.format(
        codebase_context=codebase_context,
        tutorial_content=_truncate(tutorial_content, MAX_TUTORIAL_CHARS),
    )
    
    last_error: Exception | None = None
    
    for attempt in range(1, max_retries + 1):
        try:
            response = model(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )
            
            # Handle smolagents.models.ChatMessage or LiteLLM response
            if hasattr(response, "content"):
                content = str(response.content).strip()
            elif isinstance(response, dict):
                choices = response.get("choices") or []
                if not choices:
                    raise RuntimeError("Judge model returned no choices")
                content = str(choices[0].get("message", {}).get("content", "")).strip()
            else:
                content = str(response).strip()

            if not content:
                raise RuntimeError("Judge model returned empty content")
            
            # Strip markdown fences if present
            content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE).strip()
            content = re.sub(r"\s*```$", "", content).strip()
            
            # Parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON object
                match = re.search(r"\{.*\}", content, flags=re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                raise RuntimeError(f"Invalid JSON response: {content[:200]}")
                
        except RateLimitError as exc:
            last_error = exc
            wait = min(5.0 * attempt, 20.0)
            logger.warning(f"Rate limited on {model} (attempt {attempt}/{max_retries}); sleeping {wait}s")
            time.sleep(wait)
        except Exception as exc:
            last_error = exc
            if attempt >= max_retries:
                raise
            wait = min(3.0 * attempt, 15.0)
            logger.warning(f"Judge call failed on {model} (attempt {attempt}/{max_retries}): {exc}")
            time.sleep(wait)
    
    if last_error:
        raise last_error
    raise RuntimeError("Unknown judge failure")


def evaluate_tutorial(
    tutorial_path: Path,
    codebase_context: str,
    models: List[str] = JUDGE_MODELS,
) -> AggregatedTutorialScore:
    """Evaluate a single tutorial with multiple models."""
    
    tutorial_content = tutorial_path.read_text(encoding="utf-8")
    tutorial_name = tutorial_path.name
    
    model_scores: List[TutorialScore] = []
    
    for model in models:
        logger.info(f"  → Evaluating with {model}...")
        try:
            result = _call_judge(model, tutorial_content, codebase_context)
            
            score = TutorialScore(
                tutorial_name=tutorial_name,
                model=model,
                scores=result.get("scores", {}),
                overall=result.get("overall", 0),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", []),
                rationale=result.get("rationale", ""),
            )
            model_scores.append(score)
            
        except Exception as e:
            logger.error(f"  ✗ {model} failed: {e}")
            # Add a placeholder score
            model_scores.append(TutorialScore(
                tutorial_name=tutorial_name,
                model=model,
                rationale=f"Evaluation failed: {e}"
            ))
    
    # Aggregate scores
    valid_scores = [s for s in model_scores if s.scores]
    
    if valid_scores:
        avg_scores = {}
        for criterion in CRITERIA:
            values = [s.scores.get(criterion, 0) for s in valid_scores if s.scores.get(criterion)]
            avg_scores[criterion] = round(mean(values), 2) if values else 0.0
        
        overall_values = [s.overall for s in valid_scores if s.overall]
        avg_overall = round(mean(overall_values), 2) if overall_values else 0.0
    else:
        avg_scores = {c: 0.0 for c in CRITERIA}
        avg_overall = 0.0
    
    # Collect all feedback
    all_strengths = list(set(s for score in valid_scores for s in score.strengths))
    all_weaknesses = list(set(w for score in valid_scores for w in score.weaknesses))
    all_suggestions = list(set(s for score in valid_scores for s in score.suggestions))
    
    return AggregatedTutorialScore(
        tutorial_name=tutorial_name,
        avg_scores=avg_scores,
        avg_overall=avg_overall,
        all_strengths=all_strengths[:5],
        all_weaknesses=all_weaknesses[:5],
        all_suggestions=all_suggestions[:5],
        model_scores=model_scores,
    )


def evaluate_tutorials(
    tutorial_dir: Path,
    codebase_root: Path,
    models: List[str] = JUDGE_MODELS,
) -> EvaluationReport:
    """Evaluate all tutorials in a directory."""
    
    tutorial_files = sorted(tutorial_dir.glob("*.md"))
    if not tutorial_files:
        raise ValueError(f"No markdown tutorials found in {tutorial_dir}")
    
    logger.info(f"Found {len(tutorial_files)} tutorials to evaluate")
    logger.info(f"Using models: {models}")
    
    # Build codebase context once
    logger.info("Building codebase context...")
    codebase_context = _build_codebase_context(codebase_root)
    
    # Evaluate each tutorial
    tutorial_scores: List[AggregatedTutorialScore] = []
    
    for i, tutorial_path in enumerate(tutorial_files, 1):
        logger.info(f"\n[{i}/{len(tutorial_files)}] Evaluating: {tutorial_path.name}")
        score = evaluate_tutorial(tutorial_path, codebase_context, models)
        tutorial_scores.append(score)
    
    # Calculate overall average
    all_overalls = [t.avg_overall for t in tutorial_scores if t.avg_overall > 0]
    overall_avg = round(mean(all_overalls), 2) if all_overalls else 0.0
    
    from datetime import datetime
    
    return EvaluationReport(
        tutorial_dir=str(tutorial_dir),
        codebase=str(codebase_root),
        models_used=models,
        tutorials=tutorial_scores,
        overall_avg=overall_avg,
        generated_at=datetime.now().isoformat(),
    )


def write_json_report(report: EvaluationReport, output_path: Path) -> None:
    """Write evaluation report as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "tutorial_dir": report.tutorial_dir,
        "codebase": report.codebase,
        "models_used": report.models_used,
        "overall_avg": report.overall_avg,
        "generated_at": report.generated_at,
        "tutorials": [
            {
                "name": t.tutorial_name,
                "avg_scores": t.avg_scores,
                "avg_overall": t.avg_overall,
                "strengths": t.all_strengths,
                "weaknesses": t.all_weaknesses,
                "suggestions": t.all_suggestions,
                "model_details": [
                    {
                        "model": s.model,
                        "scores": s.scores,
                        "overall": s.overall,
                        "rationale": s.rationale,
                    }
                    for s in t.model_scores
                ],
            }
            for t in report.tutorials
        ],
    }
    
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"JSON report written to: {output_path}")


def write_markdown_report(report: EvaluationReport, output_path: Path) -> None:
    """Write evaluation report as Markdown."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = [
        "# Tutorial Evaluation Report",
        "",
        f"**Generated:** {report.generated_at}",
        f"**Codebase:** `{Path(report.codebase).name}`",
        f"**Tutorial Directory:** `{report.tutorial_dir}`",
        f"**Models Used:** {', '.join(report.models_used)}",
        "",
        f"## Overall Score: {report.overall_avg}/5.0",
        "",
        "---",
        "",
        "## Summary by Tutorial",
        "",
        "| Tutorial | Accuracy | Completeness | Clarity | Structure | Diagrams | Overall |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    
    for t in report.tutorials:
        row = [
            t.tutorial_name,
            str(t.avg_scores.get("accuracy", "-")),
            str(t.avg_scores.get("completeness", "-")),
            str(t.avg_scores.get("clarity", "-")),
            str(t.avg_scores.get("structure", "-")),
            str(t.avg_scores.get("diagrams", "-")),
            str(t.avg_overall),
        ]
        lines.append("| " + " | ".join(row) + " |")
    
    lines.extend(["", "---", ""])
    
    # Detailed breakdowns
    for t in report.tutorials:
        lines.extend([
            f"## {t.tutorial_name}",
            "",
            f"**Average Score:** {t.avg_overall}/5.0",
            "",
        ])
        
        if t.all_strengths:
            lines.append("### Strengths")
            for s in t.all_strengths:
                lines.append(f"- {s}")
            lines.append("")
        
        if t.all_weaknesses:
            lines.append("### Weaknesses")
            for w in t.all_weaknesses:
                lines.append(f"- {w}")
            lines.append("")
        
        if t.all_suggestions:
            lines.append("### Suggestions")
            for s in t.all_suggestions:
                lines.append(f"- {s}")
            lines.append("")
        
        lines.append("### Model Opinions")
        for ms in t.model_scores:
            model_name = ms.model.split("/")[-1]
            lines.append(f"- **{model_name}**: {ms.overall}/5 — {ms.rationale[:100]}...")
        
        lines.extend(["", "---", ""])
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Markdown report written to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate tutorials using multiple LLM judges"
    )
    # Mode 1: Single directory eval
    parser.add_argument(
        "--tutorials", type=Path, default=None,
        help="Path to tutorial directory containing .md files"
    )
    
    # Mode 2: A/B Comparison
    parser.add_argument("--baseline", type=Path, default=None, help="Path to Series A tutorials")
    parser.add_argument("--deep", type=Path, default=None, help="Path to Series B tutorials")
    
    # Common
    parser.add_argument(
        "--codebase", type=Path, default=None,
        help="Path to codebase root (auto-detected if not provided)"
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output directory for reports"
    )
    parser.add_argument(
        "--models", type=str, default=None,
        help="Comma-separated list of models"
    )
    parser.add_argument(
        "--colab", action="store_true",
        help="Use Colab-hosted GPT-OSS-20B API (requires LLM_JUDGE_URL env var)"
    )
    parser.add_argument(
        "--judge-url", type=str, default=None,
        help="URL for external LLM judge API (overrides LLM_JUDGE_URL env var)"
    )
    args = parser.parse_args()
    
    # Set external API URL if provided via CLI
    global EXTERNAL_API_URL
    if args.judge_url:
        EXTERNAL_API_URL = args.judge_url
        logger.info(f"Using external judge API: {EXTERNAL_API_URL}")
    
    # Determine Codebase
    codebase_root = None
    if args.codebase:
        codebase_root = args.codebase.expanduser().resolve()
    
    # Mode: Compare
    if args.baseline and args.deep:
        if not codebase_root:
            # Fallback assumption
            codebase_root = args.deep.parent.parent # data/deep_agent_output/REPO/tutorials -> REPO ? No.
            # safe fallback: current dir
            if not codebase_root or not codebase_root.exists():
                 codebase_root = Path(".")
        
        logger.info(f"Starting A/B Comparison: {args.baseline.name} vs {args.deep.name}")
        
        baseline_files = set(f.name for f in args.baseline.glob("*.md"))
        deep_files = set(f.name for f in args.deep.glob("*.md"))
        common_files = sorted(list(baseline_files.intersection(deep_files)))
        
        if not common_files:
            logger.error("No common files to compare!")
            return

        logger.info(f"Comparing {len(common_files)} common files...")
        context = _build_codebase_context(codebase_root)
        
        # Select models - --colab flag overrides --models
        if args.colab:
            models = ["colab"]
            logger.info("Using Colab-hosted GPT-OSS-20B API for evaluation")
        elif args.models:
            models = [m.strip() for m in args.models.split(",")]
        else:
            models = JUDGE_MODELS
        
        all_results = []
        
        for file_name in common_files:
            for model_id in models:
                logger.info(f"Comparing {file_name} with {model_id}...")
                res = evaluate_pair(model_id, file_name, context, args.baseline/file_name, args.deep/file_name)
                if res:
                    all_results.append(res)
                    print(f"Winner: {res.get('winner')} | {file_name}")

        # Summary
        wins = {"A": 0, "B": 0, "Tie": 0, "Error": 0}
        for r in all_results:
            w = r.get("winner", "Error")
            wins[w] = wins.get(w, 0) + 1
            
        print("\n" + "="*50)
        print("AGGREGATE WIN RATES")
        print("="*50)
        total = len(all_results)
        if total > 0:
            print(f"Total: {total}")
            print(f"Series A: {wins['A']} ({wins['A']/total*100:.1f}%)")
            print(f"Series B: {wins['B']} ({wins['B']/total*100:.1f}%)")
            print(f"Tie:          {wins['Tie']} ({wins['Tie']/total*100:.1f}%)")
        
        # Write JSON
        if args.output:
            out_file = args.output / "comparison_report.json"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
            logger.info(f"Saved comparison report to {out_file}")
            
        return

    # Mode: Single Eval
    if args.tutorials:
        tutorial_dir = args.tutorials.expanduser().resolve()
        if not tutorial_dir.exists():
            logger.error(f"Tutorial directory not found: {tutorial_dir}")
            return
            
        if not codebase_root:
             codebase_root = tutorial_dir.parent # Best guess
        
        models = [m.strip() for m in args.models.split(",")] if args.models else JUDGE_MODELS
        report = evaluate_tutorials(tutorial_dir, codebase_root, models)
        
        output_dir = args.output or tutorial_dir.parent
        write_json_report(report, output_dir / "evaluation_report.json")
        write_markdown_report(report, output_dir / "evaluation_report.md")
        logger.info(f"Evaluation complete! Score: {report.overall_avg}/5.0")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
