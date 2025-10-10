# Smolagents Quickstart Template

A minimal template for building AI agents with [Smolagents](https://huggingface.co/docs/smolagents). Features tool-calling agents, filesystem operations, optional multi-agent orchestration, and OpenTelemetry tracing.

## Features

- Tool-calling agent with filesystem and web API tools
- Gradio chat interface
- File workspace for agent operations
- Optional multi-agent coordination
- Easy LLM provider integration via LiteLLM
- OpenTelemetry tracing with Phoenix and OpenInference for agent observability

## Quick Start

1. **Install dependencies:**
   ```bash
   uv sync
   ```

1. **Set up environment:**
   ```bash
   cp env.example .env
   ```
   
1. **Configure API key:** See [API Key Setup Guide](docs/api_key.md) for detailed instructions

1. **Run the application:**
   ```bash
   ./run.sh
   # or
   uv run main.py
   ```

Open the Gradio URL printed in your terminal to start chatting with the agent.

## Documentation

- **[How to Use Guide](docs/how_to.md)** - Student-friendly tutorials and exercises
- **[API Key Setup](docs/api_key.md)** - Complete guide for getting API keys

## Requirements

- Python 3.13+
- uv package manager

## License

MIT

