'''
# Deep Agents (`libs/deepagents`)

## Overview

The `deepagents` library provides a framework for building sophisticated, "deep" LLM agents. Unlike simple agents that just call tools in a loop, deep agents are designed to handle complex, long-running tasks by incorporating planning, a virtual filesystem, and the ability to delegate tasks to specialized sub-agents. The core of the library is the `create_deep_agent` function, which assembles a powerful agent from a set of modular middleware components.

This component fits into a larger system by providing a ready-to-use, yet highly customizable, agent architecture. It abstracts away the complexity of building stateful, long-running agents, allowing developers to focus on the specific logic of their application.

## Entry Points

The main entry point for creating a deep agent is the `create_deep_agent` function located in `libs/deepagents/deepagents/graph.py`.

To understand the code, a developer should start by examining the `create_deep_agent` function. It shows how the different middleware components are composed to build the final agent. From there, one can dive into the individual middleware implementations in `libs/deepagents/deepagents/middleware/` to understand the specific functionalities like the filesystem, sub-agents, and planning.

## Key Concepts

- **Deep Agent**: An advanced LLM agent that can plan, use a filesystem, and delegate tasks to sub-agents to solve complex problems. This contrasts with "shallow" agents that have a simpler, more reactive architecture.

- **Middleware**: A component that intercepts and modifies the agent's behavior. The `deepagents` library uses a middleware architecture to add features like the filesystem (`FilesystemMiddleware`), sub-agents (`SubAgentMiddleware`), and planning (`TodoListMiddleware`).

- **Sub-agent**: A specialized agent that is spawned by the main agent to perform a specific task. This is useful for isolating context and breaking down complex problems into smaller, manageable parts.

- **Filesystem Backend**: An abstraction that provides the underlying storage for the agent's virtual filesystem. The default is an in-memory `StateBackend`, but it can be replaced with a persistent backend.

## Dependencies & Relationships

- **What this component calls**:
    - `langchain.agents.create_agent`: The core function from the LangChain library used to create the agent.
    - `TodoListMiddleware`, `FilesystemMiddleware`, `SubAgentMiddleware`, `SummarizationMiddleware`: The various middleware components that are composed to create the deep agent.

- **What calls this component**:
    - Application code that needs to create a deep agent will call the `create_deep_agent` function.

- **External libraries or APIs used**:
    - `langchain`: The primary dependency for building the agent.
    - `langchain_anthropic`: Used for the default chat model (Claude Sonnet).

## Patterns & Conventions

- **Middleware-based Architecture**: The functionality of the deep agent is built up by composing various middleware. This makes the architecture modular and extensible.

- **System Prompts for Instruction**: The behavior of the agent and its tools is heavily guided by detailed system prompts. For instance, the `FilesystemMiddleware` and `SubAgentMiddleware` inject their own system prompts to instruct the agent on how to use the provided tools.

- **Virtual Filesystem**: The agent interacts with a virtual filesystem, with all paths being absolute paths starting with `/`. This provides a consistent and secure way for the agent to manage files and context.

- **Error Handling**: The tools provided by the middleware include error handling. For example, attempting to read a non-existent file will return an error message to the agent.

## Code Examples

### 1. Creating a Deep Agent

This example shows how to create a deep agent with a custom model and a tool.

```python
from deepagents import create_deep_agent
from langchain_core.tools import tool

@tool
def internet_search(query: str) -> str:
    """Run a web search"""
    # Implementation of the search tool
    return f"Search results for: {query}"

# Create the deep agent
agent = create_deep_agent(
    model="openai:gpt-4o",
    tools=[internet_search],
    system_prompt="You are an expert researcher.",
)
```

**Why this matters:** This snippet is the most common entry point for using the `deepagents` library. It demonstrates how to easily create a powerful agent with custom tools and instructions, without needing to worry about the underlying implementation details.

### 2. Using the Filesystem

The agent can use the filesystem tools to manage context and offload information.

```python
# In the agent's thought process:
# 1. List files
# tool_code
# print(default_api.ls(path="/"))

# 2. Write to a file
# tool_code
# print(default_api.write_file(file_path="/research/notes.txt", content="LangGraph is a library for building stateful, multi-actor applications with LLMs."))

# 3. Read the file
# tool_code
# print(default_api.read_file(file_path="/research/notes.txt"))
```

**Why this matters:** The filesystem is a key feature of deep agents. It allows them to handle large amounts of information, persist data between steps, and work with files in a way that is similar to how a human would. This example shows the basic file operations that the agent can perform.

### 3. Defining and Using a Sub-agent

This example shows how to define a sub-agent and provide it to the main agent.

```python
from deepagents import create_deep_agent, SubAgent

research_subagent = {
    "name": "research-agent",
    "description": "Used to research more in-depth questions",
    "system_prompt": "You are a great researcher",
    "tools": [internet_search],
}

agent = create_deep_agent(
    subagents=[research_subagent]
)
```

**Why this matters:** Sub-agents are a powerful tool for breaking down complex tasks. This example shows how to define a specialized sub-agent and make it available to the main agent. This allows the main agent to delegate tasks, which can improve performance and reduce the complexity of the main agent's reasoning process.

## Tutorial Hints

- **When to use sub-agents**: Use sub-agents for tasks that are complex, multi-step, and can be performed in isolation. For simple, one-shot tasks, it's better to use a regular tool call.

- **Filesystem management**: Encourage the agent to use the filesystem to store intermediate results, especially when dealing with large amounts of data from tools like web search. This helps to keep the context window from overflowing.

- **Pitfall: Path validation**: All file paths in the virtual filesystem must be absolute paths starting with `/`. The agent might try to use relative paths, which will result in errors. It's important to remind the agent of this convention in the system prompt.

- **Prerequisites**: To fully understand this component, a developer should have a good understanding of the LangChain library, especially the concept of agents and tools. Familiarity with LangGraph is also helpful, as the deep agent is a LangGraph graph.
'''