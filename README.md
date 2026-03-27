# Smolagents Quickstart Template

[📄 View Final Report (`Rapor_21011035_21011506.pdf`)](teslim-paketi/Doc/Rapor_21011035_21011506.pdf)

A minimal template for building AI agents with [Smolagents](https://huggingface.co/docs/smolagents). Features tool-calling agents, filesystem operations, optional multi-agent orchestration, and OpenTelemetry tracing.

## Features

- **Two-Phase Analysis Pipeline**: A **Supervisor Agent** orchestrates typed **Sub-Agent** analyzers to build a structured **Knowledge Base**.
- **Tutorial Generation**: An autonomous pipeline that transforms the Knowledge Base into pedagogical tutorials with optional code search and RAG helpers.
- **Judge LLM Evaluation**: Integrated benchmarking suite that uses SOTA models (Claude 4.5, GPT-OSS-120B) to audit content quality.
- **Observability**: OpenTelemetry tracing with **Phoenix** and OpenInference for detailed pipeline monitoring.
- **LiteLLM Integration**: Unified access to multiple LLM providers (Google, OpenAI, Anthropic, etc.).
- **Local RAG**: Optional retrieval-augmented generation backed by a local Chroma vector store.

## Quick Start

1. **Install dependencies:**

   ```bash
   uv sync
   ```

1. **Set up environment:**
   ```bash
   cp env.example .env
   ```

1. **Run a pipeline:**
   ```bash
   ./run.sh deep-agent --codebase data/agent_workspace/agent-lightning
   ```

### Judge LLM & Evaluation

The system includes a robust evaluation framework that uses independent "Judge" models to score the generated content across three dimensions:
- **Fidelity**: Accuracy of code snippets and technical explanations against the source code.
- **Pedagogy**: Logical flow and clarity of teaching from simple to complex concepts.
- **Coverage**: How much of the critical codebase surface area is documented.

Run the judge directly on existing benchmark results:
```bash
./run.sh judge --results-dir data/bench/my-project
```

## Requirements

- Python 3.13+
- uv package manager

## License

MIT

## Web UI

A modern web interface is available for browsing and editing generated tutorials.

<div align="center">
  <img src="assets/ui_landing.png" alt="UI Landing Page" width="800" />
  <br/><br/>
  <img src="assets/ui_tutorial.png" alt="UI Tutorial View" width="800" />
</div>

### Quick Start (UI)

```bash
cd ui
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the tutorial browser.

See [ui/GUIDE.md](ui/GUIDE.md) for detailed setup instructions.
