'''
# Running Agents in a Secure Harbor Environment

Welcome to this guide on running DeepAgents in a secure, containerized Harbor environment. This tutorial will walk you through the `deepagents_harbor` library, explaining how it enables agents to operate safely within Harbor and detailing the workflow for automated task execution.

## The `deepagents_harbor` Library

The `deepagents_harbor` library is a specialized component designed to bridge the gap between the core DeepAgents framework and the Harbor containerization platform. Its primary goal is to allow agents to perform tasks that require file system access or shell command execution without compromising the security of the host system. It achieves this through a secure sandbox environment that translates agent actions into safe, isolated commands.

## The Role of `HarborSandbox`

The cornerstone of this library is the `HarborSandbox` backend. Unlike a standard `FilesystemBackend` that interacts directly with the local disk, the `HarborSandbox` acts as a secure translation layer. When an agent attempts to perform a file operation (e.g., reading, writing, or editing), the sandbox intercepts the request and converts it into a corresponding shell command. This command is then executed within the isolated Harbor container.

This design ensures that the agent never has direct access to the underlying filesystem. Every action is mediated and executed as a sandboxed process, providing a robust security model.

Here’s a visual representation of the workflow:

```mermaid
graph TD
    A[DeepAgent] -->|Tool Call: read("file.txt")| B(HarborSandbox);
    B -->|Translates to Shell Command| C{environment.exec('cat file.txt')};
    C -->|Executes in Container| D[Harbor Environment];
    D -->|Returns stdout/stderr| C;
    C -->|Command Result| B;
    B -->|Formats as Tool Output| A;
```

For instance, when the agent needs to read a file, it calls the `aread` method. As you can see in the source code, `HarborSandbox` translates this into an `awk` command to retrieve the file's content with line numbers.

```python
# From libs/harbor/deepagents_harbor/backend.py
async def aread(
    self,
    file_path: str,
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """Read file content with line numbers using shell commands."""
    # Escape file path for shell
    safe_path = shlex.quote(file_path)

    # Check if file exists and handle empty files
    cmd = f"""
if [ ! -f {safe_path} ]; then
    echo "Error: File not found"
    exit 1
fi
if [ ! -s {safe_path} ]; then
    echo "System reminder: File exists but has empty contents"
    exit 0
fi
# Use awk to add line numbers and handle offset/limit
awk -v offset={offset} -v limit={limit} '
    NR > offset && NR <= offset + limit {{
        printf "%6d\t%s\n", NR, $0
    }}
    NR > offset + limit {{ exit }}
' {safe_path}
"""
    result = await self.aexecute(cmd)

    if result.exit_code != 0 or "Error: File not found" in result.output:
        return f"Error: File '{file_path}' not found"

    return result.output.rstrip()
```

## Workflow 2 in Action: Automated Task Execution

Workflow 2, as outlined in the executive summary, describes a scenario where an automated process triggers a DeepAgent to perform a task within a Harbor environment. A key component in this workflow is the `DeepAgentsWrapper` class.

The `DeepAgentsWrapper` is responsible for setting up the agent with the `HarborSandbox` and managing its execution lifecycle. It formats the initial system prompt with crucial context, such as the current working directory and a list of files, so the agent can start its task with immediate awareness of its environment.

### Setting up the Agent

The wrapper instantiates the agent, connecting it to the specified LLM and configuring it with the `HarborSandbox` backend.

Here is how the `DeepAgentsWrapper` initializes the agent for automated execution:

```python
# From libs/harbor/deepagents_harbor/deepagents_wrapper.py

# ... inside the `run` method ...
backend = HarborSandbox(environment)

# Get formatted system prompt with directory context
system_prompt = await self._get_formatted_system_prompt(backend)

deep_agent = create_deep_agent(
    model=self._model, backend=backend, system_prompt=system_prompt
)

# ... invoke the agent ...
result = await deep_agent.ainvoke(
    {"messages": [{"role": "user", "content": instruction}]},
    config=config,
)
```

This setup ensures that when the agent is invoked with an instruction (e.g., "Analyze the codebase and generate documentation"), all its subsequent actions are securely handled by the `HarborSandbox`.

### Running the Task

To trigger the agent, an instruction is sent to the `run` method of the `DeepAgentsWrapper`. The wrapper then invokes the agent with the instruction and saves a detailed record of the entire execution, known as a trajectory.

```bash
# Conceptual example of triggering the agent
# This would typically be done through a Harbor orchestration script

# Instruction for the agent
INSTRUCTION="Analyze the codebase and generate documentation for all public functions in utils.py"

# The Harbor environment would then call the wrapper's `run` method
# which executes the agent in a secure container
```

## Key Takeaways

- **Security First**: The `deepagents_harbor` library prioritizes security by ensuring agents never have direct file system access.
- **Sandbox Translation**: `HarborSandbox` is the core component that translates agent tool calls into secure shell commands.
- **Automated Execution**: The `DeepAgentsWrapper` class simplifies the process of running agents in an automated fashion within Harbor.
- **Full Traceability**: The entire process is logged, providing a clear trajectory for debugging and analysis.

This architecture allows you to harness the power of DeepAgents for complex, automated tasks while adhering to the strict security requirements of a production environment.
'''