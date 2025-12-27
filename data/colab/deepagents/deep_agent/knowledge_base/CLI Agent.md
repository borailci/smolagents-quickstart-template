
# Deep Agents CLI: Agent & Memory Analysis

## 1. Overview

The `deepagents-cli` package provides the core components for creating, managing, and interacting with conversational AI agents from the command line. The system is designed with a key architectural distinction: it can operate in either a **local mode**, with direct access to the user's filesystem and shell, or a **remote sandbox mode**, where execution is safely contained in a remote environment (e.g., Modal, Daytona).

The two primary files, `agent.py` and `agent_memory.py`, work together to construct a complete agent. `agent.py` is the factory for building the agent, configuring its tools, and establishing its execution environment. `agent_memory.py` provides a sophisticated, hierarchical long-term memory system that allows agents to persist knowledge across sessions at both user and project levels.

## 2. File-by-File Analysis

### `libs/deepagents-cli/deepagents_cli/agent.py`

- **Purpose**: This file is the central hub for agent creation and configuration. It defines the main factory function `create_cli_agent` and all supporting logic for setting up the agent's runtime environment, including its tools, middleware, and safety features.
- **Key Components**:
  - `create_cli_agent()`: The primary entry point for instantiating a CLI agent. It dynamically assembles the agent based on parameters like the desired model, whether it's in local or sandbox mode, and which features (memory, skills, shell) are enabled.
  - `get_system_prompt()`: Generates a dynamic system prompt that instructs the agent on its operating environment (local vs. remote sandbox), providing crucial context like the current working directory.
  - **Human-in-the-Loop (HITL) Functions**: A series of functions (`_add_interrupt_on`, `_format_shell_description`, etc.) implement a critical safety feature. They intercept potentially destructive tool calls (e.g., `shell`, `write_file`, `execute`), format a human-readable description of the intended action, and await user approval before execution.
  - `list_agents()` & `reset_agent()`: Utility functions for managing agent configurations stored on the user's local machine in `~/.deepagents/`.

### `libs/deepagents-cli/deepagents_cli/agent_memory.py`

- **Purpose**: This file implements the agent's long-term memory system through a LangGraph middleware component.
- **Key Components**:
  - `AgentMemoryMiddleware`: A middleware class that intercepts the agent's execution flow to inject long-term memory into the system prompt. It manages the loading and formatting of memory content.
  - **Hierarchical Memory System**: The core concept of this module. It defines two levels of memory files (`agent.md`):
    1.  **User Memory**: Located at `~/.deepagents/{assistant_id}/agent.md`. It stores the agent's core personality, style, and universal preferences that apply across all projects.
    2.  **Project Memory**: Located at `[project-root]/.deepagents/agent.md` or `[project-root]/agent.md`. It stores project-specific context, coding conventions, and architectural details.
  - `LONGTERM_MEMORY_SYSTEM_PROMPT`: An extensive prompt that instructs the agent on how to use its memory system effectively. It details when to read, when to write, and how to decide whether information belongs in user or project memory.

## 3. Integration and Data Flow

The integration pattern is centered around the `create_cli_agent` function, which acts as an assembler:

1.  **Initialization**: A caller (e.g., the main CLI command) invokes `create_cli_agent` with a model, an agent ID, and configuration flags.
2.  **Middleware Assembly**: The function builds a list of middleware components. Crucially, `AgentMemoryMiddleware` is added to manage memory, and other middleware like `SkillsMiddleware` or `ShellMiddleware` (for local mode) are added.
3.  **Backend Configuration**: A `CompositeBackend` is set up. In local mode, it defaults to a `FilesystemBackend`. In remote mode, it uses the provided sandbox backend.
4.  **Agent Creation**: The collected components (model, tools, backend, middleware) are passed to the `deepagents.create_deep_agent` function from the core library.
5.  **Memory Injection**: When the agent runs, the `AgentMemoryMiddleware` kicks in. Its `wrap_model_call` method reads the `agent.md` files from both user and project locations, formats them, and injects them into the final system prompt sent to the language model.
6.  **HITL Interruption**: If the agent attempts to use a tool configured for HITL (e.g., `shell`), the `InterruptOnConfig` settings halt the execution and prompt the user for approval before proceeding.

## 4. Use Cases

- **Interactive Development Assistant**: The primary use case is a CLI-based assistant for software development. A developer can chat with the agent to write code, read files, run tests, and perform other development tasks. The HITL feature provides a crucial safety layer.
- **Automated Workflows**: By disabling HITL (`auto_approve=True`), the agent can be used in automated scripts or CI/CD pipelines to perform tasks without human intervention.
- **Agent Benchmarking**: The `create_cli_agent` function is self-contained and can be imported into other frameworks (like testing or benchmarking suites) to programmatically create and evaluate agent performance.

## 5. Public Interface & API Reference

The main public interface for this module is the `create_cli_agent` function.

| Class / Function | Method / Signature | Description |
| :--- | :--- | :--- |
| **Function** | `create_cli_agent(model: str | BaseChatModel, assistant_id: str, *, tools: list[BaseTool] | None = None, sandbox: SandboxBackendProtocol | None = None, sandbox_type: str | None = None, system_prompt: str | None = None, auto_approve: bool = False, enable_memory: bool = True, enable_skills: bool = True, enable_shell: bool = True) -> tuple[Pregel, CompositeBackend]` | The main factory for creating a complete, configured CLI agent. It returns a LangGraph `Pregel` object ready for execution and the configured `CompositeBackend`. |
| **Class** | `AgentMemoryMiddleware` | A LangGraph middleware class for managing long-term memory. |
| `AgentMemoryMiddleware` | `__init__(self, *, settings: Settings, assistant_id: str, system_prompt_template: str | None = None)` | Initializes the middleware with application settings and the agent's ID. |
