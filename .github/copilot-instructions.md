# Smolagents Quickstart Template - AI Agent Guidelines

## Overview
This is a template for building AI agents using the Smolagents framework. It provides modular components for agents, toolkits, UI, and tracing, focused on tool-calling agents with filesystem and web API capabilities.

## Architecture
- **Agents**: Modular agents inheriting from `BaseAgent`, using Smolagents' `ToolCallingAgent` or manager agents for orchestration.
- **Toolkits**: Collections of tools wrapped as `@tool` decorated functions, e.g., filesystem operations via Langchain, web APIs.
- **UI**: Gradio-based chat interface for agent interaction.
- **Tracing**: OpenTelemetry integration with Phoenix for observability.
- **Data Flow**: Agents receive user input via UI, execute tools on workspace (`data/agent_workspace`), return responses.

## Key Components
- `agents/`: Agent classes like `ExampleToolCallingAgent` (uses `LiteLLMModel` with env vars `LITELLM_MODEL_ID` and `LITELLM_API_KEY`).
- `toolkits/`: Tool collections, e.g., `FileSystemToolkit.get_tools()` returns [read_file, write_file, file_search, list_workspace_dir, get_tree].
- `ui/`: `GradioAgentUI` launches chat interface on localhost with sharing enabled.
- `prompts/prompts.py`: Agent instructions, e.g., `EXAMPLE_TOOL_CALLING_AGENT` for tool usage guidance.
- `data/agent_workspace/`: Sandbox for agent file operations, with example files like `car.c` and `alan_turing.md`.

## Developer Workflows
- **Setup**: `uv sync` to install deps, `cp env.example .env`, configure API keys per `docs/api_key.md`.
- **Run**: `./run.sh` (sources `.env`, runs `uv run main.py`) or `uv run main.py` directly.
- **Debug**: Check logs via Loguru, trace via Phoenix UI (launched automatically).
- **Multi-Agent**: Uncomment manager agent in `main.py` for orchestration.

## Conventions
- Agents: Subclass `BaseAgent`, set `self.agent` to Smolagents agent instance, implement `run()` method.
- Tools: Define as `@tool` functions with docstrings, collect in toolkit classes with `get_tools()` static method.
- Env Vars: Use `AGENT_WORKSPACE_PATH` for workspace root (defaults to `data/agent_workspace`).
- Imports: Load dotenv in entry points, use Loguru for logging.
- File Paths: Relative to workspace root for agent operations, enforce sandboxing in custom tools like `get_tree`.

## Examples
- **Agent Creation**: `tool_calling_agent = ExampleToolCallingAgent(tools=joke_tools + filesystem_tools)`
- **Tool Usage**: `@tool def read_file(file_path: str) -> List[str]: return read_file_tool.invoke(...)`
- **UI Launch**: `ui = GradioAgentUI(agent=tool_calling_agent); ui.launch()`
- **Tracing**: Register Phoenix and instrument Smolagents in `main.py` before agent init.</content>
<parameter name="filePath">/home/amirkia/Desktop/smolagents-quickstart-template/.github/copilot-instructions.md