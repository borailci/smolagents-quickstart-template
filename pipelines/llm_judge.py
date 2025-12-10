
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
import json
import re
from pathlib import Path
from loguru import logger
from utils.llm_factory import create_model
from smolagents import LiteLLMModel
from toolkits.rag_store import SimpleChromaRAGStore

# Updated prompt to reflect RAG context
JUDGE_PROMPT = """You are an expert technical writer and software engineer. You are comparing two versions of a tutorial.
You have access to RELEVANT CODE SNIPPETS retrieved from the actual codebase.

*** RELEVANT CODE CONTEXT (RAG Retrieved) ***
{codebase_context}
*** END CODE CONTEXT ***

Tutorial A:
{baseline_content}

Tutorial B:
{deep_agent_content}

Evaluate them on the following criteria using a 1-5 scale (1=Poor, 5=Excellent):

1. **Fidelity**: Is the code accurate? Does it match the actual codebase? (Fact-checking). *Note: The context provided is retrieved based on relevance. If a specific function is missing from context but seems plausible, give benefit of the doubt, but penalize obvious hallucinations.*
2. **Pedagogy**: Is it easy for a beginner to understand? Is the structure logical?
3. **Coverage**: Does it cover the most important parts of the system? (Completeness)

Which tutorial is better overall?

Output your answer in the following JSON format:
{{
  "winner": "A", "B", or "Tie",
  "reasoning": "Detailed explanation...",
  "fidelity_A": <1-5>,
  "fidelity_B": <1-5>,
  "pedagogy_A": <1-5>,
  "pedagogy_B": <1-5>,
  "coverage_A": <1-5>,
  "coverage_B": <1-5>
}}
"""

def evaluate_pair(model: LiteLLMModel, model_id: str, file_name: str, path_a: Path, path_b: Path, rag_store: SimpleChromaRAGStore) -> dict | None:
    content_a = path_a.read_text(errors="replace") if path_a.exists() else "MISSING"
    content_b = path_b.read_text(errors="replace") if path_b.exists() else "MISSING"

    if content_a == "MISSING" and content_b == "MISSING":
        return None
    
    # RAG Retrieval
    # Construct a query from the filename and the beginning of the content (usually the intro/overview)
    # We prioritize the provided content to find what code it *should* differencing.
    query_text = f"Tutorial Topic: {file_name}\n\nContent Preview:\n{content_b[:1000]}" 
    
    logger.info(f"Retrieving context for {file_name}...")
    try:
        # Retrieve top 15 chunks to get good coverage without blowing context
        retrieved_chunks = rag_store.query(query=query_text, top_k=15)
        codebase_context = "\n".join(retrieved_chunks)
        if not codebase_context:
            codebase_context = "No relevant code chunks found in RAG store."
    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}")
        codebase_context = "Error retrieving code context."

    logger.info(f"Evaluating {file_name} with {model_id} (Context size: {len(codebase_context)} chars)...")

    prompt = JUDGE_PROMPT.format(
        codebase_context=codebase_context,
        baseline_content=content_a, 
        deep_agent_content=content_b
    )
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000
            )
            # Parse JSON
            clean_json = re.sub(r"```json\n|```", "", response.content).strip()
            data = json.loads(clean_json)
            data["files"] = file_name
            data["model"] = model_id
            return data
        except Exception as e:
            if "429" in str(e) or "exhausted" in str(e).lower():
                wait = (attempt + 1) * 5
                logger.warning(f"Rate limit hit for {file_name} ({model_id}). Waiting {wait}s... Error detail: {str(e)[:200]}")
                time.sleep(wait)
            else:
                logger.error(f"Failed to evaluate {file_name} with {model_id}: {e}")
                return None
    return None

def main():
    parser = argparse.ArgumentParser(description="Compare two sets of tutorials.")
    parser.add_argument("--baseline", type=Path, required=True, help="Path to baseline tutorials")
    parser.add_argument("--deep", type=Path, required=True, help="Path to deep agent tutorials")
    parser.add_argument("--codebase", type=Path, required=True, help="Path to the codebase root") # Still required to initialize RAG paths, though we rely on cache
    parser.add_argument("--models", type=str, default="vertex_ai/gemini-2.5-pro", 
                        help="Comma-separated list of model IDs to use as judges")
    parser.add_argument("--rag-cache", type=Path, default=Path("data/rag_cache"), help="Path to RAG ChromaDB cache")

    args = parser.parse_args()
    
    model_ids = [m.strip() for m in args.models.split(",")]

    # Find common files
    files_a = set(f.name for f in args.baseline.glob("*.md"))
    files_b = set(f.name for f in args.deep.glob("*.md"))
    all_files = sorted(list(files_a | files_b))

    logger.info("Initializing RAG Store...")
    # Initialize RAG store to read from existing index
    rag_store = SimpleChromaRAGStore(
        codebase_root=args.codebase,
        knowledge_base_root=args.codebase, # Not really used for query-only but required by init
        persist_directory=args.rag_cache,
        collection_name="codebase_rag_cache" # Mapped to existing cache from tutorial_toolkit.py
    )
    
    # Ensure index exists (should be fast if already built)
    rag_store.ensure_index(include_codebase=True, include_knowledge_base=False)

    all_results = []

    print(f"\n{'Model':<25} | {'File':<30} | {'Winner':<6} | {'Fid A':<5} | {'Fid B':<5} | {'Ped A':<5} | {'Ped B':<5} | {'Cov A':<5} | {'Cov B':<5}")
    print("-" * 140)

    for model_id in model_ids:
        try:
            # Create model instance for this specific judge
            model = create_model(model_id=model_id)
            
            for file_name in all_files:
                path_a = args.baseline / file_name
                path_b = args.deep / file_name
                
                result = evaluate_pair(model, model_id, file_name, path_a, path_b, rag_store)
                
                if result:
                    all_results.append(result)
                    print(f"{model_id:<25} | {file_name:<30} | {result.get('winner', '?'):<6} | "
                          f"{result.get('fidelity_A', 0):<5} | {result.get('fidelity_B', 0):<5} | "
                          f"{result.get('pedagogy_A', 0):<5} | {result.get('pedagogy_B', 0):<5} | "
                          f"{result.get('coverage_A', 0):<5} | {result.get('coverage_B', 0):<5}")
                
                # Inter-file throttle - Reduced since RAG is lighter
                time.sleep(1.0)
                
        except Exception as e:
            logger.error(f"Failed to initialize model {model_id}: {e}")

    # Aggregation Table
    if all_results:
        print("\n" + "="*50)
        print("AGGREGATE WIN RATES")
        print("="*50)
        
        wins = {"A": 0, "B": 0, "Tie": 0}
        total = 0
        
        for r in all_results:
            w = r.get("winner", "Tie")
            if w not in wins: w = "Tie"
            wins[w] += 1
            total += 1
            
        print(f"Total Evaluations: {total}")
        print(f"Baseline Wins (A): {wins['A']} ({wins['A']/total*100:.1f}%)")
        print(f"Deep Agent Wins (B): {wins['B']} ({wins['B']/total*100:.1f}%)")
        print(f"Ties:             {wins['Tie']} ({wins['Tie']/total*100:.1f}%)")

if __name__ == "__main__":
    main()
