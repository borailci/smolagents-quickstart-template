# DeepAgents Harbor Knowledge Base

## 1. Overview
The `deepagents_harbor` module provides an integration layer that allows DeepAgents to operate within Harbor environments. It essentially adapts the generic DeepAgents framework to leverage Harbor's specific environment capabilities, primarily focusing on sandbox execution and consistent agent behavior tracking. This module acts as a bridge, enabling DeepAgents to interact with the underlying execution environment (like Docker or Modal) through a unified `HarborSandbox` backend and provides a `DeepAgentsWrapper` to manage the agent's lifecycle and interaction.

## 2. Key Components

### `HarborSandbox` (`backend.py`)
This class is a concrete implementation of `SandboxBackendProtocol` from DeepAgents. Its primary role is to provide sandboxed execution capabilities, translating DeepAgents' abstract sandbox operations (execute, read, write, edit, list, grep, glob) into shell commands that are then executed by the `BaseEnvironment` provided by Harbor. It handles command execution, output parsing, error filtering, and ensures safe file operations using base64 encoding and `shlex.quote` for security.

### `DeepAgentsWrapper` (`deepagents_wrapper.py`)
This is the core agent implementation that wraps the DeepAgents framework for use in Harbor. It extends `harbor.agents.base.BaseAgent` and orchestrates the setup and execution of a DeepAgent. It's responsible for initializing the LLM, creating the DeepAgent instance (either a CLI-based or SDK-based agent), preparing the system prompt with environment context (like current directory and file listings), invoking the DeepAgent with a given instruction, and saving the execution trajectory and metrics.

### `create_example_id_from_instruction` (`tracing.py`)
This utility function is used for LangSmith integration. It generates a deterministic UUID from an instruction string, which is crucial for linking runs to specific examples within LangSmith for experiment tracking and feedback. The UUID generation uses SHA-256 hashing to ensure consistency.

## 3. Data Flow & Dependencies

The data flow primarily revolves around the `DeepAgentsWrapper` acting as the central orchestrator.

1.  **Initialization**: `DeepAgentsWrapper` is initialized with a `logs_dir`, `model_name`, and other configuration. It initializes an `HarborSandbox` instance, which in turn depends on a `harbor.environments.base.BaseEnvironment` for actual command execution.
2.  **Instruction Execution**: When `DeepAgentsWrapper.run()` is called with an `instruction`, it first reads environment configuration and instantiates the `HarborSandbox` backend.
3.  **System Prompt Generation**: Before invoking the DeepAgent, `DeepAgentsWrapper` calls `_get_formatted_system_prompt()`. This method queries the `HarborSandbox` (e.g., `als_info(".")` for directory listing and `aexecute("pwd")` for current directory) to gather environment context.
4.  **DeepAgent Creation**: The `DeepAgentsWrapper` then creates either a CLI-based or SDK-based DeepAgent using `deepagents.create_deep_agent` or `deepagents_cli.agent.create_cli_agent`, passing the `HarborSandbox` as the execution backend and the formatted system prompt.
5.  **Agent Invocation**: The `deep_agent.ainvoke()` method is called with the user instruction. During its execution, the DeepAgent will make tool calls that translate to method calls on the `HarborSandbox` (e.g., `aexecute`, `aread`, `awrite`).
6.  **Sandbox Execution**: `HarborSandbox` methods construct shell commands (e.g., `grep`, `awk`, `perl`, `ls`, `mkdir`, `base64`) and pass them to `self.environment.exec()` for execution within the Harbor environment.
7.  **Result Handling**: `HarborSandbox` processes the output of shell commands, filters out harmless bash messages, and returns structured results (e.g., `ExecuteResponse`, `WriteResult`, `EditResult`, `FileInfo`, `GrepMatch`) back to the DeepAgent.
8.  **Trajectory Saving**: After the DeepAgent completes its task, `DeepAgentsWrapper._save_trajectory()` processes the messages exchanged with the DeepAgent, extracting token usage and structuring the conversation into `Step` and `Observation` objects to form a `Trajectory`. This trajectory is then saved as a JSON file for analysis and replay.
9.  **Tracing**: LangSmith tracing is optionally enabled, where `create_example_id_from_instruction` helps in linking runs to examples. The `deep_agent.ainvoke` call is wrapped in a LangSmith trace context if `LANGSMITH_EXPERIMENT` is set.

**Key Dependencies:**
*   `deepagents`: The core framework for autonomous agents.
*   `harbor.environments.base.BaseEnvironment`: Provides the underlying execution environment for shell commands.
*   `harbor.agents.base.BaseAgent`: Base class for Harbor agents.
*   `harbor.models.trajectories`: Data models for saving agent execution trajectories.
*   `langchain`: Used for initializing chat models (`init_chat_model`) and message handling.
*   `langsmith`: For experiment tracking and feedback.

## 4. Code Deep Dive

### 4.1 `HarborSandbox.aexecute` - Robust Command Execution
This method demonstrates how `HarborSandbox` executes shell commands and meticulously handles their output, including filtering out common, harmless bash error messages to present a cleaner output to the agent.

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

**Explanation**: This snippet is critical for the sandbox's reliability. It executes a given `command` via the `self.environment.exec` call. A key feature is its handling of typical, benign bash error messages that often appear in non-interactive shell environments. These messages are filtered from `stdout` and `stderr` and, if present, are collected and prepended to the `stderr` output to ensure the agent receives relevant error information without being distracted by noise.

### 4.2 `DeepAgentsWrapper._get_formatted_system_prompt` - Contextualizing the Agent
This method showcases how the DeepAgent is provided with crucial initial context about its operating environment, including the current working directory and a listing of files.

```python
    async def _get_formatted_system_prompt(self, backend: HarborSandbox) -> str:
        """Format the system prompt with current directory and file listing context.

        Args:
            backend: Harbor sandbox backend to query for directory information

        Returns:
            Formatted system prompt with directory context
        """
        # Get directory information from backend
        ls_info = await backend.als_info(".")
        current_dir = (await backend.aexecute("pwd")).output

        # Get first 10 files
        total_files = len(ls_info) if ls_info else 0
        first_10_files = ls_info[:10] if ls_info else []
        has_more = total_files > 10

        # Build file listing header based on actual count
        if total_files == 0:
            file_listing_header = "Current directory is empty."
            file_listing = ""
        elif total_files <= 10:
            # Show actual count when 10 or fewer
            file_count_text = "1 file" if total_files == 1 else f"{total_files} files"
            file_listing_header = f"Files in current directory ({file_count_text}):"
            file_listing = "\n".join(f"{i + 1}. {file}" for i, file in enumerate(first_10_files))
        else:
            # Show "First 10 of N" when more than 10
            file_listing_header = f"Files in current directory (showing first 10 of {total_files}):"
            file_listing = "\n".join(f"{i + 1}. {file}" for i, file in enumerate(first_10_files))

        # Format the system prompt with context
        formatted_prompt = SYSTEM_MESSAGE.format(
            current_directory=current_dir.strip() if current_dir else "/app",
            file_listing_header=file_listing_header,
            file_listing=file_listing,
        )

        return formatted_prompt
```

**Explanation**: This asynchronous method is responsible for dynamically generating a portion of the system prompt that provides the DeepAgent with an understanding of its initial working environment. It leverages the `HarborSandbox` to get the current directory (`pwd`) and list files (`ls_info`). It then formats this information into a readable string, ensuring that if there are many files, only the first 10 are listed, along with a count. This contextual information is vital for the agent to make informed decisions without immediately needing to perform `ls` commands.

### 4.3 `DeepAgentsWrapper._save_trajectory` - Comprehensive Trajectory Logging
This method details the structured logging of the agent's entire interaction, including user instructions, agent messages, tool calls, and observations, along with token usage metrics.

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

**Explanation**: This method is responsible for constructing and saving a detailed `Trajectory` object, which logs every step of the agent's interaction. It iterates through the `result["messages"]` from the DeepAgent invocation. It differentiates between `AIMessage` (agent's thoughts, actions, and tool calls), `ToolMessage` (results of tool calls, treated as observations), and `HumanMessage`. It intelligently groups `AIMessage` with subsequent `ToolMessage`s as `Observation`s within a `Step`, ensuring a coherent log of agent actions and their immediate outcomes. Token usage metrics are also extracted. This trajectory is invaluable for debugging, analysis, and understanding agent behavior.

## 5. Potential Pitfalls

*   **Shell Command Vulnerabilities**: While `shlex.quote` is used to mitigate some injection risks, constructing complex shell commands dynamically always carries a residual risk if not handled meticulously. Developers should be cautious when adding new shell-based functionalities.
*   **Asynchronous-only Backend**: The `HarborSandbox` explicitly raises `NotImplementedError` for synchronous methods (`read`, `write`, `edit`, `ls_info`, `grep_raw`, `glob_info`). This design choice enforces asynchronous programming, which is generally good for I/O-bound operations in agent systems but means any part of the DeepAgents framework expecting synchronous calls will fail.
*   **Error Message Filtering**: The filtering of bash error messages, while useful for cleaning up agent output, might inadvertently hide critical system errors if new types of benign messages emerge or if a genuinely problematic error matches one of the filtered strings.
*   **Limited Glob Support**: The `aglob_info` method explicitly states that its glob pattern support is not comprehensive, which could lead to unexpected behavior or missed files for complex glob patterns.
*   **Dependency on External Tools**: `HarborSandbox` relies on standard Unix utilities like `awk`, `grep`, `perl`, `basename`, `dirname`, `mkdir`, `cd`, `pwd`, and `base64`. The absence or different behavior of these tools in a specific `BaseEnvironment` could lead to failures.
*   **Hardcoded System Message Structure**: The `SYSTEM_MESSAGE` in `deepagents_wrapper.py` provides a fixed structure for the initial environment context. While customizable with dynamic content, its overall layout is static, which might limit flexibility for very different types of agent tasks.
*   **Trajectory Saving Complexity**: The `_save_trajectory` method involves intricate logic for parsing `AIMessage` and `ToolMessage` content blocks and managing `pending_step` and `observations`. Any change in the `langchain` message format or `deepagents` message structure could break this parsing logic, requiring careful maintenance."