
# Harbor Backend Analysis

## 1. Overview

The Harbor Backend is a Python-based integration layer that allows `deepagents` to operate within a `harbor` environment. It acts as a bridge, translating `deepagents` actions (like file system operations and command execution) into shell commands that are executed in the sandboxed Harbor environment. It also handles LangSmith tracing and trajectory logging for observability.

This system is designed to run autonomous agents in a controlled, isolated environment, capturing their interactions for analysis and debugging. The key components are the `HarborSandbox`, which implements the `SandboxBackendProtocol` for agent-environment communication, and the `DeepAgentsWrapper`, which orchestrates the agent's lifecycle.

## 2. File-by-File Analysis

### `libs/harbor/deepagents_harbor/backend.py`

- **Purpose**: This file provides the `HarborSandbox` class, which is a concrete implementation of the `deepagents` `SandboxBackendProtocol`. It translates abstract file and execution commands into shell commands suitable for a generic sandboxed environment.
- **Key Components**:
  - `HarborSandbox`: A class that implements the `SandboxBackendProtocol`. It uses an underlying `harbor` environment to execute commands. All of its methods are asynchronous (`async`) and rely on shell commands (`grep`, `awk`, `perl`, `find`) to perform actions.
    - **Execution**: `aexecute` runs a bash command and filters out common non-interactive shell error messages.
    - **File I/O**: `aread`, `awrite`, and `aedit` use shell commands to read, write, and modify files. Content is Base64-encoded to handle special characters safely.
    - **File System**: `als_info` and `aglob_info` list files and directories.
    - **Search**: `agrep_raw` performs a recursive search for a pattern in files.

### `libs/harbor/deepagents_harbor/deepagents_wrapper.py`

- **Purpose**: This file contains the `DeepAgentsWrapper`, which is a `harbor` `BaseAgent`. It is the main entry point for running a `deepagent` within the Harbor framework. It sets up the agent, formats the system prompt with environment context, invokes the agent, and saves the resulting trajectory.
- **Key Components**:
  - `DeepAgentsWrapper`: The primary class that integrates `deepagents` with `harbor`.
    - `run()`: The main method that orchestrates the agent's execution. It sets up the `HarborSandbox`, creates the `deepagent` (either from `deepagents-cli` or the SDK), and invokes it with the user's instruction. It also handles LangSmith tracing.
    - `_get_formatted_system_prompt()`: A helper that constructs a dynamic system prompt containing the current working directory and a listing of files, giving the agent initial context.
    - `_save_trajectory()`: A method that processes the agent's message history and saves it to a `trajectory.json` file in the standard `ATIF-v1.2` format. It also calculates token usage.

### `libs/harbor/deepagents_harbor/tracing.py`

- **Purpose**: This utility file provides a function to create a deterministic UUID for LangSmith tracing.
- **Key Components**:
  - `create_example_id_from_instruction()`: A function that generates a stable UUID from a given instruction string by hashing it. This allows runs in a LangSmith experiment to be consistently linked to the same test case (example).

## 3. Architecture & Data Flow

1.  The `DeepAgentsWrapper` is initialized by the Harbor runtime.
2.  When a task is started, the `run` method is called with an instruction.
3.  A `HarborSandbox` instance is created, linking it to the active Harbor environment.
4.  The wrapper fetches the current directory and file listing from the `HarborSandbox` to create a `system_prompt`.
5.  A `deepagent` is created using the specified model and the `HarborSandbox` as its backend.
6.  The `deepagent` is invoked with the instruction. If `LANGSMITH_EXPERIMENT` is set, the run is traced in LangSmith.
7.  The `deepagent` uses the `HarborSandbox` to execute commands (e.g., `aexecute`, `aread`, `awrite`).
8.  The `HarborSandbox` translates these calls into shell commands and executes them in the Harbor environment.
9.  After the agent finishes, the `DeepAgentsWrapper` saves the entire interaction history as a `trajectory.json` file.

## 4. Integration Points

- **Verified Dependencies**:
    - `deepagents`: The core framework for the autonomous agent.
    - `harbor`: The platform providing the sandboxed execution environment.
    - `langchain`: Used for the LLM chat model and message objects.
    - `langsmith`: Used for observability and tracing.
    - `deepagents-cli`: Provides an alternative, more configurable agent creation function (`create_cli_agent`).
- **Package Name**: The package name is `deepagents-harbor`, as verified from `pyproject.toml`.

## 5. Public Interface & API Reference

The primary public interface is the `DeepAgentsWrapper` class, which is designed to be used by the Harbor agent runner.

### `class DeepAgentsWrapper(BaseAgent)`

**Description**: A Harbor agent that wraps a `deepagent` to execute tasks in a sandboxed environment.

| Method Signature | Return Type | Description |
| --- | --- | --- |
| `__init__(self, logs_dir: Path, model_name: str \| None = None, temperature: float = 0.0, verbose: bool = True, use_cli_agent: bool = True, *args, **kwargs)` | `None` | Initializes the wrapper. `use_cli_agent` determines whether to use the agent from `deepagents-cli` or the standard SDK. |
| `name() -> str` | `str` | Returns the static name of the agent: `"deepagent-harbor"`. |
| `version() -> str \| None` | `str \| None` | Returns the agent version. |
| `setup(self, environment: BaseEnvironment) -> None` | `None` | Prepares the agent for execution (currently a no-op). |
| `run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None` | `None` | The main entry point to execute a task. Orchestrates agent creation, invocation, and logging. |

### `class HarborSandbox(SandboxBackendProtocol)`

**Description**: Implements the `SandboxBackendProtocol` for `deepagents` by executing shell commands in a Harbor environment.

| Method Signature | Return Type | Description |
| --- | --- | --- |
| `__init__(self, environment: BaseEnvironment) -> None` | `None` | Initializes the sandbox with a Harbor environment. |
| `aexecute(self, command: str) -> ExecuteResponse` | `ExecuteResponse` | Executes a shell command in the environment. |
| `aread(self, file_path: str, offset: int = 0, limit: int = 2000) -> str` | `str` | Reads a file's content with line numbers. |
| `awrite(self, file_path: str, content: str) -> WriteResult` | `WriteResult` | Writes content to a new file. |
| `aedit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult` | `EditResult` | Replaces occurrences of a string in a file. |
| `als_info(self, path: str) -> list[FileInfo]` | `list[FileInfo]` | Lists the contents of a directory. |
| `agrep_raw(self, pattern: str, path: str \| None = None, glob: str \| None = None) -> list[GrepMatch] \| str` | `list[GrepMatch] \| str` | Searches for a pattern in files recursively. |
| `aglob_info(self, pattern: str, path: str = "/") -> list[FileInfo]` | `list[FileInfo]` | Finds files matching a glob pattern. |

### `tracing.py`

| Function Signature | Return Type | Description |
| --- | --- | --- |
| `create_example_id_from_instruction(instruction: str, seed: int = 42) -> str` | `str` | Creates a deterministic UUID from an instruction string for LangSmith tracing. |

## 6. Use Cases

- **Autonomous Task Execution**: Use this module to run a `deepagent` to perform software development or data analysis tasks within a secure, isolated Harbor environment.
- **Agent Evaluation**: The integration with LangSmith and the detailed trajectory logging make it suitable for evaluating the performance of different agent models and prompts.
- **Reproducible Research**: The deterministic nature of the environment and tracing allows for reproducible experiments on agent behavior.
