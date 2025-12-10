
import os
import argparse
import glob
from pathlib import Path
from loguru import logger
from utils.llm_factory import create_model
from smolagents import LiteLLMModel



import os
import argparse
import glob
import time
from pathlib import Path
from loguru import logger
from utils.llm_factory import create_model
from smolagents import LiteLLMModel

JUDGE_PROMPT = """You are an expert technical writer and software engineer. You are comparing two versions of a tutorial.
You have access to the ACTUAL CODEBASE that these tutorials are supposed to be about.

*** GROUND TRUTH CODEBASE CONTEXT ***
{codebase_context}
*** END CODEBASE CONTEXT ***

Tutorial A (Baseline):
{baseline_content}

Tutorial B (Deep Agent):
{deep_agent_content}

Evaluate them on the following criteria:
1. **Accuracy (CRITICAL)**: Is the code and explanation technically correct? DOES IT HALLUCINATE? Check if the files, functions, and classes mentioned actually exist in the Ground Truth Codebase.
2. **Completeness**: Does it cover the topic comprehensively?
3. **Clarity**: Is it easy to understand?
4. **Best Practices**: Does it encourage good coding patterns?

Which tutorial is better?
Output your answer in the following JSON format:
{{
  "winner": "A", "B", or "Tie",
  "reasoning": "Detailed explanation...",
  "score_A": <0-10>,
  "score_B": <0-10>
}}
"""

def read_codebase(root_path: Path) -> str:
    """Flatten the codebase into a single string."""
    context = []
    # Collect reasonable text files
    extensions = ["*.py", "*.md", "*.txt", "*.toml", "Makefile"]
    
    for ext in extensions:
        for file_path in root_path.rglob(ext):
            if "node_modules" in str(file_path) or ".git" in str(file_path) or "__pycache__" in str(file_path):
                continue
            
            try:
                content = file_path.read_text(errors="replace")
                rel_path = file_path.relative_to(root_path)
                context.append(f"--- FILE: {rel_path} ---\n{content}\n")
            except Exception:
                pass
                
    return "\n".join(context)

def evaluate_pair(model: LiteLLMModel, file_name: str, path_a: Path, path_b: Path, codebase_context: str):
    content_a = path_a.read_text(errors="replace") if path_a.exists() else "MISSING"
    content_b = path_b.read_text(errors="replace") if path_b.exists() else "MISSING"

    if content_a == "MISSING" and content_b == "MISSING":
        return None
    
    logger.info(f"Evaluating {file_name}...")
    prompt = JUDGE_PROMPT.format(
        codebase_context=codebase_context,
        baseline_content=content_a, 
        deep_agent_content=content_b
    )
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = model(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )
            return response.content
        except Exception as e:
            if "429" in str(e) or "exhausted" in str(e).lower():
                wait = (attempt + 1) * 20
                logger.warning(f"Rate limit hit for {file_name}. Waiting {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"Failed to evaluate {file_name}: {e}")
                return None
    return None

def main():
    parser = argparse.ArgumentParser(description="Compare two sets of tutorials.")
    parser.add_argument("--baseline", type=Path, required=True, help="Path to baseline tutorials")
    parser.add_argument("--deep", type=Path, required=True, help="Path to deep agent tutorials")
    parser.add_argument("--codebase", type=Path, required=True, help="Path to the codebase root")
    
    args = parser.parse_args()

    # Find common files
    files_a = set(f.name for f in args.baseline.glob("*.md"))
    files_b = set(f.name for f in args.deep.glob("*.md"))
    all_files = sorted(list(files_a | files_b))

    logger.info("Reading codebase context...")
    codebase_context = read_codebase(args.codebase)
    logger.info(f"Codebase context length: {len(codebase_context)} chars")

    model = create_model()
    
    print(f"{'File':<30} | {'Winner':<10} | {'A':<3} | {'B':<3} | {'Reasoning'}")
    print("-" * 100)


    for file_name in all_files:
        path_a = args.baseline / file_name
        path_b = args.deep / file_name
        
        result_json = evaluate_pair(model, file_name, path_a, path_b, codebase_context)
        
        # Throttling between files
        time.sleep(15.0)
        
        if result_json:
            import json
            import re
            
            try:
                clean_json = re.sub(r"```json\n|```", "", result_json).strip()
                data = json.loads(clean_json)
                
                print(f"{file_name:<30} | {data.get('winner', '?'):<10} | {data.get('score_A', 0):<3} | {data.get('score_B', 0):<3} | {data.get('reasoning', '')[:50]}...")
            except Exception:
                 print(f"{file_name:<30} | ERROR PARSING JSON")
                 logger.debug(f"Raw output: {result_json}")

if __name__ == "__main__":
    main()
