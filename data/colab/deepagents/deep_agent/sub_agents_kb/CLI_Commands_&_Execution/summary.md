
# Deep Agents CLI: Commands & Execution Analysis

## 1. Overview

This document provides a technical analysis of the CLI command handling, task execution, and shell integration modules of the `deepagents-cli` package. These components form the core of the user-facing interactive shell, managing user input, agent interaction, and tool execution.

- `commands.py`: Implements handlers for meta-commands (like `/help`, `/clear`) and direct bash command execution (`!command`).
- `execution.py`: Orchestrates the main task execution loop, streaming agent responses, handling human-in-the-loop (HITL) tool approvals, and rendering UI components.
- `shell.py`: Provides a middleware that safely exposes a `shell` tool to the LangChain agent, allowing it to run local commands.

## 2. File-by-File Analysis

### `deepagents_cli/commands.py`

- **Purpose**: This module is responsible for parsing and handling user commands that are not intended for the AI agent. It acts as a pre-processor, intercepting "slash" (`/`) and "bang" (`!`) commands.
- **Key Components**:
  - `handle_command(command, agent, token_tracker)`: This function processes slash commands. It returns `"exit"` to terminate the CLI session, `True` if the command was handled, and `False` to indicate the input should be passed to the agent. It manages commands like `/quit`, `/clear`, `/help`, and `/tokens`.
  - `execute_bash_command(command)`: This function handles bang commands (e.g., `!ls -l`). It executes the given string as a shell command in a subprocess, captures its stdout and stderr, and prints them to the console. It includes a 30-second timeout for safety.

### `deepagents_cli/execution.py`

- **Purpose**: This is the engine of the CLI. It manages the entire lifecycle of a user request, from parsing input to streaming the agent's response and handling tool-use interruptions.
- **Key Components**:
  - `execute_task(...)`: The main asynchronous function that takes user input and orchestrates the agent's response. Its key responsibilities include:
    - Parsing file mentions (`@file`) and injecting their content into the prompt.
    - Streaming the agent's response, including text, reasoning steps, and tool calls.
    - Rendering UI elements like the "thinking" spinner, tool usage icons, and final markdown output.
    - Managing a `FileOpTracker` to display file operations.
    - Intercepting `Interrupt` exceptions for Human-in-the-Loop (HITL) approvals.
  - `prompt_for_tool_approval(action_request, assistant_id)`: Renders an interactive prompt for the user to approve or reject a tool action requested by the agent. It uses raw terminal I/O to create a navigable menu with arrow keys, falling back to simple text input on non-Unix systems. It also handles an "auto-accept all" option to streamline workflows.

### `deepagents_cli/shell.py`

- **Purpose**: This module provides a secure and isolated way for the agent to execute shell commands on the local machine.
- **Key Components**:
  - `ShellMiddleware`: A LangChain `AgentMiddleware` that injects a `shell` tool into the agent's available tools. 
    - It is initialized with a `workspace_root` to constrain the working directory of executed commands.
    - It uses Python's `subprocess.run` to execute commands with a configurable timeout and a limit on the output size to prevent overwhelming the agent.
    - It captures stdout, stderr, and the exit code, formatting them into a `ToolMessage` that is returned to the agent for processing.

## 3. Architecture & Data Flow

1.  The main CLI loop receives user input.
2.  The input is first checked by `commands.handle_command` (for `/...` commands) and `commands.execute_bash_command` (for `!...` commands).
3.  If not handled, the input is passed to `execution.execute_task`.
4.  `execute_task` sends the prompt to the LangGraph agent via `agent.astream()`.
5.  The agent streams back events: text chunks, tool call requests, and interrupts.
6.  When the agent wants to use a tool (like the `shell` tool from `shell.py`), the graph emits an `Interrupt`.
7.  `execute_task` catches this, stops the stream, and calls `prompt_for_tool_approval`.
8.  The user approves or rejects the action.
9.  `execute_task` resumes the agent's execution with the user's decision.
10. If approved, the `ShellMiddleware` in `shell.py` executes the command and returns the output as a `ToolMessage`.
11. The agent processes the tool's output and continues, streaming its final response back to the user.

## 4. Integration Points

- **Verified Dependencies**:
  - `deepagents_cli.config`: Provides shared configuration like console object and color styles.
  - `deepagents_cli.ui`: Used for rendering UI components like token tracking, help messages, and tool displays.
  - `deepagents_cli.input`: Used for parsing `@file` mentions in user input.
  - `deepagents_cli.file_ops`: Used to track and display previews for file-based tool calls.
  - `langchain` / `langgraph`: The core frameworks for building and running the agent.
  - `rich`: The library used for all styled console output.

## 5. API Reference

| Class / Function | Signature | Description |
| :--- | :--- | :--- |
| **commands.py** | | |
| `handle_command` | `(command: str, agent, token_tracker: TokenTracker) -> str | bool` | Handles slash commands like `/help`, `/clear`, `/quit`, and `/tokens`. |
| `execute_bash_command` | `(command: str) -> bool` | Executes a raw shell command (prefixed with `!`). |
| **execution.py** | | |
| `execute_task` | `async (user_input: str, agent, assistant_id: str | None, session_state, token_tracker: TokenTracker | None = None, backend=None) -> None` | Main entry point for processing user input and streaming agent response. Handles HITL. |
| `prompt_for_tool_approval` | `(action_request: ActionRequest, assistant_id: str | None) -> Decision | dict` | Displays an interactive prompt for the user to approve or reject a tool call. |
| **shell.py** | | |
| `ShellMiddleware` | `(workspace_root: str, timeout: float = 120.0, max_output_bytes: int = 100_000, env: dict[str, str] | None = None)` | A LangChain middleware that provides a `shell` tool to the agent for local command execution. |
