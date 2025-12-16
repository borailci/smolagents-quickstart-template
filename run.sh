#!/bin/zsh

# Activate environment if needed (uncomment and modify if using venv)
# source venv/bin/activate

# Set environment variables from .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

if [ $# -eq 0 ]; then
  echo "Usage: $0 <command> [options]"
  echo ""
  echo "Commands:"
  echo "  knowledge-base, kb    Build knowledge base from codebase"
  echo "  tutorials, tutorial   Generate tutorials from knowledge base"
  echo "  deep-agent            Run full pipeline (KB + tutorials)"
  echo "  evaluate, eval        Evaluate tutorial quality with LLM judges"
  echo "  gen-rag               Generate RAG index"
  exit 1
fi

# Run pipeline CLI with forwarded arguments
uv run python -m pipelines.cli "$@"
