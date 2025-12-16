'''
# Getting Started with DeepAgents

Welcome to the world of DeepAgents! This tutorial will guide you through the foundational concepts of the `deepagents` library, showing you how to build your first intelligent agent.

DeepAgents is a powerful Python framework for creating, running, and managing stateful AI agents. It leverages the robustness of LangGraph to build agents as state machines, allowing for complex, multi-step task execution.

## Core Concepts: The Building Blocks of a DeepAgent

The heart of the library is the `create_deep_agent` function. It assembles an agent from two primary types of components: **Backends** and **Middleware**.

### Backends: The Agent's Environment

A **Backend** defines where and how an agent operates. It provides the I/O layer, dictating how the agent interacts with its environment. For example, it determines how files are read or written. The `deepagents` library comes with a few built-in backends, including:

*   `StateBackend`: An in-memory, ephemeral backend. All "files" are stored in a simple dictionary and are lost when the process ends. It's perfect for quick, self-contained tasks.
*   `FilesystemBackend`: Allows the agent to read and write directly to the local filesystem.

### Middleware: The Agent's Abilities

**Middleware** components are pluggable modules that give an agent its capabilities. They intercept the agent's execution flow to add new tools and functionality. For instance, `FilesystemMiddleware` adds tools like `ls`, `read_file`, and `write_file` to the agent.

## Architecture at a Glance

Here’s how these pieces fit together. When you call `create_deep_agent`, it combines a Backend and a set of Middleware to construct a fully configured agent.

```mermaid
graph TD
    subgraph User Code
        A[create_deep_agent(...)]
    end

    subgraph Agent Configuration
        B[Backend: StateBackend]
        C[Middleware: FilesystemMiddleware]
    end

    subgraph Executable Agent
        D{DeepAgent State Machine}
    end

    A --> |uses| B
    A --> |uses| C
    B --> |configures| D
    C --> |adds tools to| D
```

This modular design makes it easy to customize agents for different tasks and environments.

## Your First DeepAgent: "Hello, World!"

Let's build a simple agent that writes "Hello, World!" to a virtual file. We'll use the `StateBackend` for this, so no actual files will be written to your disk.

First, ensure you have the `deepagents` library installed:

```bash
pip install deepagents
```

Now, let's write the Python code:

```python
import asyncio
from deepagents import create_deep_agent
from deepagents.backends.state import StateBackend

# 1. Define the main asynchronous function
async def main():
    # 2. Instantiate the StateBackend
    # This backend stores data in memory.
    backend = StateBackend()

    # 3. Create the agent
    # We pass the backend to the FilesystemMiddleware via the `create_deep_agent` function.
    agent = create_deep_agent(
        backend=backend
    )

    # 4. Define the task for the agent
    objective = "Write a file named 'hello.txt' with the content 'Hello, World!'"

    # 5. Run the agent
    final_answer = await agent.ainvoke(
        {"messages": [("user", objective)]}
    )

    # 6. Print the results
    print("--- Agent's Final Answer ---")
    print(final_answer['messages'][-1].content)

    print("\n--- StateBackend Contents ---")
    print(backend.get_files())

# 7. Run the main function
if __name__ == "__main__":
    asyncio.run(main())

```

### Running the Code

When you execute this script, the `create_deep_agent` function assembles an agent configured to use the in-memory `StateBackend`. The agent receives the instruction, uses its `write_file` tool (provided by the `FilesystemMiddleware`), and writes the content to the backend.

### Expected Output

You should see the following output:

```text
--- Agent's Final Answer ---
I have successfully written the file 'hello.txt' with the content 'Hello, World!'.

--- StateBackend Contents ---
{'hello.txt': 'Hello, World!'}
```

As you can see, the agent confirms the file was written, and we can inspect the `StateBackend` to see the "virtual" file and its content.

## Next Steps

Congratulations on building your first DeepAgent! You've learned how `create_deep_agent`, Backends, and Middleware work together.

In the next tutorial, we will explore the `FilesystemBackend` to build an agent that can interact with real files on your local disk.
'''