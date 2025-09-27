#!/bin/zsh

# Activate environment if needed (uncomment and modify if using venv)
# source venv/bin/activate

# Set environment variables from .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Run main.py using uv
uv run main.py
