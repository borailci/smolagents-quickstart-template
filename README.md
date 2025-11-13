# Smolagents Quickstart Template

A minimal template for building AI agents with [Smolagents](https://huggingface.co/docs/smolagents). Features tool-calling agents, filesystem operations, optional multi-agent orchestration, and OpenTelemetry tracing.

## Features

- Tool-calling agent with filesystem and web API tools
- Gradio chat interface
- File workspace for agent operations
- Optional multi-agent coordination
- Easy LLM provider integration via LiteLLM
- OpenTelemetry tracing with Phoenix and OpenInference for agent observability
- Optional retrieval-augmented generation backed by a local Chroma vector store

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

### Pipeline CLI (Knowledge Base & Tutorials)

Use the bundled CLI to generate knowledge-base docs, tutorials, and Q&A responses:

```bash
uv run pipelines/cli.py knowledge-base
uv run pipelines/cli.py tutorials --code-search --rag --rag-max-snippets 3
uv run pipelines/cli.py qa "How do background jobs work?"
uv run pipelines/cli.py spawn-subagents "Analyze src/utils and document helper utilities"
```

You can also control these defaults with environment variables:

| Feature           | CLI flag                             | Env var                            |
| ----------------- | ------------------------------------ | ---------------------------------- |
| Code search tools | `--code-search` / `--no-code-search` | `TUTORIAL_ENABLE_CODE_SEARCH=true` |
| Retrieval helper  | `--rag` / `--no-rag`                 | `TUTORIAL_ENABLE_RAG=true`         |
| Snippet cap       | `--rag-max-snippets N`               | `TUTORIAL_RAG_MAX_SNIPPETS=N`      |

With `--rag` enabled the tutorial toolkit rebuilds a persistent Chroma collection under `data/rag_vector_store`, embedding knowledge-base markdown and selected source files via LiteLLM. Subsequent queries are answered with semantic matches pulled from that vector store.

During knowledge-base generation the pipeline now writes a `scouting_report.md` snapshot (tree view plus README excerpts) before delegating to analyzer sub-agents, making the process easier to audit.

When enabled, the tutorial agent instructions remind it to call these helpers before guessing, leading to more grounded guides that include inline code samples from the repo.

## Documentation

- **[How to Use Guide](docs/how_to.md)** - Student-friendly tutorials and exercises
- **[API Key Setup](docs/api_key.md)** - Complete guide for getting API keys

## Requirements

- Python 3.13+
- uv package manager

## License

MIT
