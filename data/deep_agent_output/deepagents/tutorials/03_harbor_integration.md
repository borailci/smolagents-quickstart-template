# Integrating DeepAgents with Harbor

DeepAgents provides a powerful framework for building autonomous agents, offering capabilities like planning, flexible filesystem interaction, and subagent management. When combined with Harbor, a robust environment for managing agent execution, DeepAgents gain access to sandboxed environments, consistent behavior tracking, and enhanced security. This tutorial will guide you through understanding and leveraging the integration of DeepAgents with Harbor.

## 1. Overview: Why Integrate DeepAgents with Harbor?

Integrating DeepAgents with Harbor creates a synergistic environment where the advanced reasoning and planning capabilities of DeepAgents are augmented by Harbor's secure, isolated, and trackable execution infrastructure. This combination is particularly beneficial for tasks requiring:

*   **Sandboxed Execution**: DeepAgents can operate in isolated environments, preventing unintended side effects on the host system.
*   **Consistent Behavior Tracking**: Harbor provides mechanisms to log and trace agent executions, crucial for debugging, analysis, and auditing.
*   **Environment Abstraction**: Harbor's `BaseEnvironment` allows DeepAgents to interact with various underlying execution contexts (e.g., Docker, Modal) through a unified interface.

The `deepagents_harbor` module acts as the crucial bridge, adapting the generic DeepAgents framework to utilize Harbor's specific features.

## 2. Key Components of the Integration

The integration relies on two primary components that extend the DeepAgents framework within the Harbor ecosystem:

### 2.1 HarborSandbox

`HarborSandbox` is a concrete implementation of DeepAgents' `SandboxBackendProtocol`. Its core function is to translate abstract DeepAgents file operations (like `read`, `write`, `list`) and command executions (`execute`) into shell commands that are then run by Harbor's `BaseEnvironment`. This provides a secure and consistent interface for DeepAgents to interact with the underlying filesystem and execute commands.

Key responsibilities include:

*   **Command Execution**: Running shell commands via `self.environment.exec()`.
*   **Output Parsing and Filtering**: Processing command outputs and filtering out benign bash messages to provide cleaner results to the agent.
*   **Secure File Operations**: Using techniques like base64 encoding and `shlex.quote` to enhance security during file interactions.

### 2.2 DeepAgentsWrapper

The `DeepAgentsWrapper` is a specialized agent implementation that extends `harbor.agents.base.BaseAgent`. It orchestrates the lifecycle of a DeepAgent within Harbor, from initialization to execution and trajectory saving.

Its main functions are:

*   **LLM Initialization**: Setting up the Language Model for the DeepAgent.
*   **DeepAgent Creation**: Instantiating the DeepAgent (either CLI-based or SDK-based) using `deepagents.create_deep_agent`.
*   **Contextual Prompt Generation**: Preparing the system prompt with relevant environment information (e.g., current directory, file listings) queried from `HarborSandbox`.
*   **Instruction Invocation**: Calling the DeepAgent with a given instruction.
*   **Trajectory and Metric Saving**: Logging the agent's execution, including messages, tool calls, observations, and token usage, into a structured `Trajectory` for analysis.

## 3. Data Flow and Interaction

Understanding the data flow is crucial for comprehending how DeepAgents and Harbor interact. The `DeepAgentsWrapper` acts as the central coordinator, facilitating communication between the DeepAgent's core logic and the Harbor execution environment.

```mermaid
graph TD
    A[User Instruction] --> B(DeepAgentsWrapper.run());
    B --> C{Initialize HarborSandbox};
    C --> D[HarborSandbox queries BaseEnvironment (pwd, ls_info)];
    D --> E{Generate System Prompt};
    E --> F[Create DeepAgent (with HarborSandbox as backend)];
    F --> G[DeepAgent.ainvoke(instruction)];
    G -- Tool Calls (e.g., aexecute, aread, awrite) --> H[HarborSandbox Methods];
    H -- Shell Commands (e.g., grep, awk, base64) --> I[BaseEnvironment.exec()];
    I -- Command Output --> H;
    H -- Structured Results (ExecuteResponse, WriteResult) --> G;
    G -- Execution Complete --> J(DeepAgentsWrapper._save_trajectory());
    J --> K[Save Trajectory JSON / LangSmith Tracing];
```

**Explanation of Flow:**

1.  A user initiates an instruction, which is passed to `DeepAgentsWrapper.run()`.
2.  The `DeepAgentsWrapper` initializes a `HarborSandbox` instance, connecting it to the underlying `BaseEnvironment`.
3.  It then queries the `HarborSandbox` (e.g., for the current directory and file listings) to gather context for the DeepAgent's system prompt.
4.  A DeepAgent instance is created, using the `HarborSandbox` as its execution backend.
5.  The DeepAgent is invoked with the user's instruction.
6.  During its operation, the DeepAgent makes tool calls (e.g., to read files, execute commands) that are routed to the `HarborSandbox` methods.
7.  `HarborSandbox` translates these into shell commands and executes them using `BaseEnvironment.exec()`.
8.  The results from the shell commands are processed by `HarborSandbox` and returned to the DeepAgent.
9.  Once the DeepAgent completes its task, `DeepAgentsWrapper._save_trajectory()` captures the entire interaction log, including messages, tool calls, and observations.
10. The trajectory is saved as a JSON file, and optionally, traced in LangSmith.

## 4. Configuration and Setup

To configure a DeepAgent to run within Harbor, you typically instantiate the `DeepAgentsWrapper` with the necessary parameters, including the path for logs and the model to be used. The `HarborSandbox` is internally managed by the wrapper.

Here's a conceptual example of how you might set up the `DeepAgentsWrapper`:

```python
import os
from pathlib import Path
from harbor.environments.base import BaseEnvironment
from deepagents_harbor.deepagents_wrapper import DeepAgentsWrapper

class MyHarborEnvironment(BaseEnvironment):
    async def exec(self, command: str) -> dict:
        # Simulate command execution in a Harbor environment
        print(f"Executing in Harbor: {command}")
        if "ls" in command:
            return {"stdout": "file1.txt\nfile2.txt", "stderr": "", "return_code": 0}
        elif "pwd" in command:
            return {"stdout": "/app", "stderr": "", "return_code": 0}
        else:
            return {"stdout": f"Command executed: {command}", "stderr": "", "return_code": 0}

async def setup_harbor_deepagent():
    # Define a directory for logs within the Harbor context
    logs_directory = Path('/tmp/harbor_agent_logs')
    logs_directory.mkdir(exist_ok=True)

    # Instantiate your Harbor environment (this would be provided by Harbor)
    harbor_env = MyHarborEnvironment()

    # Initialize the DeepAgentsWrapper with the environment and configuration
    deep_agents_wrapper = DeepAgentsWrapper(
        logs_dir=logs_directory,
        model_name="claude-3-opus-20240229", # Or your preferred model
        environment=harbor_env,
        # Other optional parameters like timeout, custom system message etc.
    )

    # Now you can run the agent with an instruction
    instruction = "List all files in the current directory and read 'file1.txt'."
    print(f"Running agent with instruction: {instruction}")
    # In a real Harbor setup, 'run' method would be called by the framework
    # For this example, we'll simulate the main call which in turn calls the internal run
    await deep_agents_wrapper.run_agent_flow(instruction)
    print("Agent flow completed.")

# Example of how to run this (typically part of a larger Harbor system)
# import asyncio
# asyncio.run(setup_harbor_deepagent())
```

_Note: The `MyHarborEnvironment` is a simplified mock-up. In a real Harbor setup, `BaseEnvironment` instances are provided by the Harbor framework itself._

## 5. Code Deep Dive: Essential Integration Snippets

Let's examine critical code snippets that highlight how the integration works at a lower level.

### 5.1 Robust Command Execution with `HarborSandbox.aexecute`

The `aexecute` method in `HarborSandbox` is responsible for running commands and meticulously handling their output, especially filtering out common, harmless bash error messages.

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

**Explanation**: This snippet demonstrates the robustness of `HarborSandbox`. It executes commands and proactively cleans up the output by identifying and relocating common, non-critical bash messages from `stdout` to `stderr`. This ensures that the DeepAgent receives focused and actionable information, free from distracting system-level noise.

### 5.2 Contextualizing the Agent with `DeepAgentsWrapper._get_formatted_system_prompt`

Providing the DeepAgent with accurate context about its operating environment is paramount. This method dynamically generates part of the system prompt.

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

**Explanation**: This method showcases how `DeepAgentsWrapper` intelligently provides the DeepAgent with an up-to-date understanding of its environment. By asynchronously querying the `HarborSandbox` for the current directory and a listing of files, it constructs a rich initial context for the agent. This proactive context provision helps the agent make informed decisions without needing to explicitly query its environment for basic information.

## 6. Benefits of DeepAgents-Harbor Integration

*   **Enhanced Security**: Running DeepAgents in a sandboxed Harbor environment mitigates risks associated with arbitrary code execution.
*   **Reproducibility and Auditability**: Trajectory logging and LangSmith tracing provide a complete record of agent interactions, essential for debugging, analysis, and compliance.
*   **Simplified Environment Management**: Harbor abstracts away the complexities of the underlying execution environment, allowing DeepAgents to focus on task completion.
*   **Scalability**: Leverage Harbor's infrastructure to scale DeepAgent operations, running multiple agents concurrently in isolated environments.
*   **Clearer Agent Output**: `HarborSandbox`'s intelligent error filtering ensures agents receive clean, actionable information.

## 7. Potential Pitfalls and Considerations

While powerful, the integration comes with considerations:

*   **Asynchronous-Only Backend**: `HarborSandbox` enforces asynchronous operations, meaning any part of DeepAgents expecting synchronous calls will fail.
*   **Shell Command Vulnerabilities**: Despite `shlex.quote` and base64 encoding, care must be taken when dynamically constructing shell commands to avoid injection risks.
*   **Dependency on External Tools**: `HarborSandbox` relies on standard Unix utilities. Their absence or differing behavior in a specific `BaseEnvironment` could cause issues.
*   **Context Window Management**: Extensive file interactions or subagent calls can still strain the LLM's context window. Intelligent prompt engineering and summarization remain important.

By understanding these components and considerations, you can effectively integrate DeepAgents with Harbor to build robust, secure, and highly capable autonomous systems.