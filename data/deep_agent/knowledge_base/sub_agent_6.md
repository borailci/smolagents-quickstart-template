## Harbor DeepAgents Modules Analysis

### 1. Overview
This document provides a technical analysis of the `harbor` modules, specifically focusing on `deepagents_harbor/backend.py`, `deepagents_harbor/deepagents_wrapper.py`, and `deepagents_harbor/tracing.py`. These modules collectively enable the integration of DeepAgents within the Harbor environment, allowing autonomous agents to execute tasks in a sandboxed context. The `backend.py` module implements the core sandbox functionalities using shell commands, `deepagents_wrapper.py` orchestrates the DeepAgent execution and trajectory saving, and `tracing.py` provides utilities for deterministic LangSmith example ID generation.

### 2. File-by-File Analysis

#### `libs/harbor/deepagents_harbor/backend.py`
- **Purpose**: This file provides a concrete implementation of the `SandboxBackendProtocol` for DeepAgents within a Harbor environment. It allows DeepAgents to interact with the underlying system (e.g., file system, process execution) using bash commands.
- **Key Components**:
  - `HarborSandbox` class: This class extends `SandboxBackendProtocol` and provides asynchronous methods for executing shell commands and performing file operations. It handles common issues like non-interactive shell messages and ensures proper error reporting.
  - `aexecute(self, command: str) -> ExecuteResponse`: Executes a bash command in the environment and filters out harmless bash error messages from the output.
  - `aread(self, file_path: str, offset: int = 0, limit: int = 2000) -> str`: Reads file content, optionally with line numbers, offset, and limit. It uses `awk` for efficient reading.
  - `awrite(self, file_path: str, content: str) -> WriteResult`: Writes content to a new file. It base64 encodes the content to avoid shell escaping issues and uses `mkdir -p` to create parent directories.
  - `aedit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult`: Edits a file by replacing occurrences of a string. It uses `perl` for robust string replacement and handles cases where the string is not found or appears multiple times without `replace_all`.
  - `als_info(self, path: str) -> list[FileInfo]`: Lists directory contents, indicating whether each entry is a file or a directory.
  - `agrep_raw(self, pattern: str, path: str | None = None, glob: str | None = None) -> list[GrepMatch] | str`: Searches for a pattern in files using `grep` and parses the output into `GrepMatch` objects.
  - `aglob_info(self, pattern: str, path: str = "/") -> list[FileInfo]`: Finds files matching a glob pattern.

#### `libs/harbor/deepagents_harbor/deepagents_wrapper.py`
- **Purpose**: This file defines a wrapper for integrating DeepAgents with Harbor environments. It handles the setup, execution, and result logging of DeepAgent tasks, including integration with LangSmith for tracing and experiment tracking.
- **Key Components**:
  - `DeepAgentsWrapper` class: Extends `BaseAgent` and orchestrates the DeepAgent execution.
    - `__init__`: Initializes the wrapper with logging directory, model name, temperature, and flags for using CLI or SDK agents. It also sets up LangChain's chat model.
    - `_get_formatted_system_prompt(self, backend: HarborSandbox) -> str`: Generates a dynamic system prompt for the DeepAgent, including the current working directory and a listing of the first 10 files. This provides crucial context to the agent.
    - `run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None`: The main execution method. It sets up the `HarborSandbox` backend, creates a DeepAgent (either CLI or SDK based on configuration), integrates with LangSmith for tracing, invokes the DeepAgent with the given instruction, and saves the execution trajectory.
    - `_save_trajectory(self, environment: BaseEnvironment, instruction: str, result: dict) -> None`: Parses the DeepAgent's execution messages (AIMessage, ToolMessage, HumanMessage) into a structured trajectory format (`ATIF-v1.2`), tracks token usage, and saves it as a `trajectory.json` file.

#### `libs/harbor/deepagents_harbor/tracing.py`
- **Purpose**: This file provides a utility function for generating deterministic UUIDs from instruction strings, primarily for use as `example_id` in LangSmith for consistent experiment tracking.
- **Key Components**:
  - `create_example_id_from_instruction(instruction: str, seed: int = 42) -> str`: Takes an instruction string, normalizes it, and generates a deterministic UUID using SHA-256 hashing. A seed is incorporated to prevent collisions.

### 3. Architecture & Data Flow

```mermaid
graph TD
    A[Harbor Environment] --> B{DeepAgentsWrapper}
    B -->|Provides Environment| C[HarborSandbox]
    C -->|Executes Bash Commands| D[Underlying System/Shell]

    B -->|Generates System Prompt| C
    B -->|Creates DeepAgent (CLI/SDK)| E[DeepAgent Core]
    E -->|Invokes with Instruction & Config| B
    E -->|Calls Sandbox Methods| C

    B -->|Saves Trajectory & Metrics| F[Logs Directory (trajectory.json)]
    B -->|LangSmith Tracing| G[LangSmith Platform]

    H[Instruction String] --> B
    H -->|Generates Example ID| I[tracing.py::create_example_id_from_instruction]
    I --> G

    subgraph Harbor DeepAgents Internal Flow
        E -- Tool Calls --> C
        C -- Results --> E
    end
```

**Data Flow Explanation:**
1.  The `Harbor Environment` initializes the `DeepAgentsWrapper` and provides it with the execution environment.
2.  `DeepAgentsWrapper` creates a `HarborSandbox` instance, which acts as the interface to the `Underlying System/Shell` for executing commands and file operations.
3.  `DeepAgentsWrapper` generates a dynamic `system_prompt` by querying the `HarborSandbox` for current directory and file listings, providing crucial context to the agent.
4.  Based on configuration, `DeepAgentsWrapper` instantiates either a CLI or SDK `DeepAgent Core`.
5.  The `Instruction String` for the task is fed into `DeepAgentsWrapper`.
6.  The `tracing.py` module uses the `Instruction String` to generate a deterministic `example_id` for LangSmith tracing.
7.  `DeepAgentsWrapper` invokes the `DeepAgent Core` with the instruction and relevant configuration, wrapping the invocation with `LangSmith Tracing` if enabled, sending data to the `LangSmith Platform`.
8.  During its operation, `DeepAgent Core` makes `Tool Calls` (e.g., `aread`, `awrite`, `aexecute`) to the `HarborSandbox`.
9.  `HarborSandbox` executes these calls on the `Underlying System/Shell` and returns the `Results` to the `DeepAgent Core`.
10. After the DeepAgent completes its task, `DeepAgentsWrapper` processes the execution `messages` to construct a detailed `trajectory.json` file, which is saved to the `Logs Directory`. This trajectory includes steps, observations, tool calls, and final metrics.

### 4. Code Deep Dive

#### `HarborSandbox.aexecute` - Robust Command Execution
This snippet demonstrates how `HarborSandbox` executes bash commands and intelligently filters out common, harmless bash errors that occur in non-interactive environments, ensuring cleaner output for the agent.

```python
    async def aexecute(
        self,
        command: str,
    ) -> ExecuteResponse:
        """Execute a bash command in the task environment."""
        result = await self.environment.exec(command)

        # These errors appear in harbor environments when running bash commands
        # in non-interactive/non-TTY contexts. They're harmless artifacts.
        # Filter them from both stdout and stderr, then collect them to show in stderr.
        error_messages = [
            "bash: cannot set terminal process group (-1): Inappropriate ioctl for device",
            "bash: no job control in this shell",
            "bash: initialize_job_control: no job control in background: Bad file descriptor",
        ]

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        # Collect the bash messages if they appear (to move to stderr)
        bash_messages = []
        for error_msg in error_messages:
            if error_msg in stdout:
                bash_messages.append(error_msg)
                stdout = stdout.replace(error_msg, "")
            if error_msg in stderr:
                stderr = stderr.replace(error_msg, "")

        stdout = stdout.strip()
        stderr = stderr.strip()

        # Add bash messages to stderr
        if bash_messages:
            bash_msg_text = "\n".join(bash_messages)
            stderr = f"{bash_msg_text}\n{stderr}".strip() if stderr else bash_msg_text

        # Only append stderr label if there's actual stderr content
        if stderr:
            output = stdout + "\n\n stderr: " + stderr if stdout else "\n stderr: " + stderr
        else:
            output = stdout
        return ExecuteResponse(
            output=output,
            exit_code=result.return_code,
        )
```

#### `DeepAgentsWrapper._save_trajectory` - Trajectory Reconstruction
This method is crucial for converting the raw messages from the DeepAgent's execution into a structured `ATIF-v1.2` trajectory format, capturing agent steps, tool calls, observations, and metrics.

```python
    def _save_trajectory(
        self, environment: BaseEnvironment, instruction: str, result: dict
    ) -> None:
        """Save current trajectory to logs directory."""
        # Track token usage and cost for this run
        total_prompt_tokens = 0
        total_completion_tokens = 0

        # Create trajectory
        steps = [
            Step(
                step_id=1,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="user",
                message=instruction,
            ),
        ]

        observations = []
        pending_step: Step | None = None

        for msg in result["messages"]:
            if isinstance(msg, AIMessage):
                # Extract usage metadata from AIMessage
                usage: UsageMetadata = msg.usage_metadata
                if usage:
                    total_prompt_tokens += usage["input_tokens"]
                    total_completion_tokens += usage["output_tokens"]
                # If there's a pending step with tool calls, add it now with observations
                if pending_step is not None:
                    if pending_step.tool_calls and observations:
                        # Add observations to the pending step
                        pending_step.observation = Observation(results=observations)
                        observations = []
                    steps.append(pending_step)
                    pending_step = None

                # Extract content and tool calls from current AIMessage
                atf_tool_calls = []
                message = ""
                for cb in msg.content_blocks:
                    if cb["type"] == "text":
                        message += cb["text"]
                    elif cb["type"] == "reasoning":
                        message += cb["reasoning"]
                    elif cb["type"] == "tool_call":
                        atf_tool_calls.append(
                            ToolCall(
                                tool_call_id=cb["id"],
                                function_name=cb["name"],
                                arguments=cb["args"],
                            )
                        )
                    else:
                        # TODO: Add server side tool call results.
                        continue

                # Create new step
                new_step = Step(
                    step_id=steps[-1].step_id + 1 if steps else 0,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="agent",
                    message=message,
                    tool_calls=atf_tool_calls if atf_tool_calls else None,
                )

                # If this AIMessage has tool calls, make it pending (wait for observations)
                # Otherwise, add it immediately
                if atf_tool_calls:
                    pending_step = new_step
                else:
                    steps.append(new_step)

            elif isinstance(msg, ToolMessage):
                # Collect observations for the pending step
                observations.append(
                    ObservationResult(
                        source_call_id=msg.tool_call_id,
                        content=str(msg.content),
                    )
                )
            elif isinstance(msg, HumanMessage):
                pass
            else:
                raise NotImplementedError(
                    f"Message type {type(msg)} not supported for step conversion"
                )

        # Add any remaining pending step
        if pending_step is not None:
            if pending_step.tool_calls and observations:
                pending_step.observation = Observation(results=observations)
            steps.append(pending_step)

        # Build and save trajectory
        metrics = FinalMetrics(
            total_prompt_tokens=total_prompt_tokens or None,
            total_completion_tokens=total_completion_tokens or None,
            total_steps=len(steps),
        )
        trajectory = Trajectory(
            schema_version="ATIF-v1.2",
            session_id=environment.session_id,
            agent=Agent(
                name=self.name(),
                version=self.version() or "unknown",
                model_name=self._model_name,
                extra={
                    "framework": "deepagents",
                    "langchain_version": "1.0+",
                },
            ),
            steps=steps,
            final_metrics=metrics,
        )
        trajectory_path = self.logs_dir / "trajectory.json"
        trajectory_path.write_text(json.dumps(trajectory.to_json_dict(), indent=2))
```

### 5. Integration Points
- **Dependencies**: The `harbor` DeepAgents modules depend on `deepagents`, `langchain`, `langsmith`, and `harbor.environments.base`. It uses `deepagents.backends.protocol` for defining sandbox interactions.
- **Dependents**: These modules are primarily designed to be used within the `Harbor` framework to enable `DeepAgents` to operate within its sandboxed environments. The `DeepAgentsWrapper` acts as the main entry point for running DeepAgent tasks, consuming a `Harbor Environment` and producing execution `trajectories` and `metrics`.