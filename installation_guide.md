# Deep Agent - Installation & Setup Guide

This guide will help you set up the **Deep Agent** project on your local machine. This system uses AI agents to analyze codebases and generate high-quality tutorials.

## 1. Prerequisites

Before starting, ensure you have the following installed:

*   **Python 3.13+**: Required for the backend pipeline.
    *   *Check*: `python3 --version`
*   **uv**: An extremely fast Python package manager (replaces pip/venv).
    *   *Install*: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pip install uv`)
*   **Node.js 18+ & npm**: Required for the Web UI.
    *   *Check*: `node -v`

## 2. Project Installation

Clone the repository and install backend dependencies:

```bash
# 1. Clone the repo
git clone <repository_url>
cd smolagents-quickstart-template

# 2. Sync dependencies using uv (creates .venv automatically)
uv sync
```

## 3. Configuration

The project requires an environment file for API keys and settings.

1.  **Create `.env` file**:
    If an `env.example` exists, copy it. Otherwise, create a `.env` file in the root directory.

    ```bash
    cp env.example .env
    # OR create manually
    touch .env
    ```

2.  **Edit `.env`**:
    Open the file and configure your LLM provider credentials.

    ```ini
    # --- LLM Keys (Vertex AI or Keys) ---
    VERTEX_PROJECT=your-gcp-project-id
    VERTEX_LOCATION=us-central1
    # OR for other providers
    # OPENAI_API_KEY=sk-...

    # --- Project Settings ---
    # ROOT directory of the codebase you want to analyze (Absolute Path)
    CODEBASE_ROOT_PATH=/absolute/path/to/target/repo
    
    # Path where outputs (KB, tutorials) will be saved
    SUB_AGENTS_ROOT_PATH=./data
    ```

## 4. Running the Agent (Backend)

The main interaction is through the `./run.sh` script.

###  Full Pipeline (Deep Agent)
This runs the entire process: Build Knowledge Base -> Plan Tutorials -> Generate Tutorials.

```bash
./run.sh deep-agent
```

## 5. Running the Web UI

The project includes a modern Dashboard to view the generated tutorials and knowledge base.

```bash
# 1. Navigate to UI folder
cd ui

# 2. Install dependencies
npm install

# 3. Start the Development Server
npm run dev
```

Open your browser at [http://localhost:3000](http://localhost:3000).

*   **Tutorials**: Navigate to `/tutorial/<repo_name>` (e.g., `/tutorial/instructor`)
*   **Knowledge Base**: View summaries and plans.

## 6. Troubleshooting

*   **"File not found" logs**: Ensure `CODEBASE_ROOT_PATH` in `.env` points to a *valid, existing* directory.
*   **"Rate limit exceeded"**: The system has auto-retries, but you can adjust `RATE_LIMIT_MAX_REQUESTS` in `config.py` if needed.
*   **UI Issues**: If charts or markdown look broken, try clearing the `.next` cache: `rm -rf ui/.next` and restart `npm run dev`.
*   **Missing Plan Updates**: Check `/data/deep_agent_output/<repo_name>/knowledge_base/compilation_plan.md` to track agent progress manually.

---
**Happy Coding! 🚀**
