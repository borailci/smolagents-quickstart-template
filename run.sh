#!/bin/zsh

# Activate environment if needed (uncomment and modify if using venv)
# source venv/bin/activate

# Set environment variables from .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

if [ $# -eq 0 ]; then
  echo "Usage: $0 <command> [options]"
  echo "Commands: knowledge-base | tutorials | qa | spawn-subagents"
  exit 1
fi

# Run pipeline CLI with forwarded arguments
uv run pipelines/cli.py "$@"
