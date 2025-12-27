'''
# DeepAgents Core Analysis: `deepagents.graph`

## 1. Overview

The `deepagents.graph` module serves as the primary entry point for constructing and configuring "deep agents". These agents are built upon the `langgraph` library and come pre-configured with a suite of powerful middleware, providing capabilities such as to-do list management, a virtual filesystem, and the ability to spawn and manage sub-agents.

The core of this module is the `create_deep_agent` factory function. It simplifies the complex process of assembling an agent by bundling essential middleware and providing sensible defaults, while still allowing for extensive customization through its parameters. The goal is to offer a robust, general-purpose agent that can handle complex, long-running tasks by breaking them down and leveraging its built-in tools.

## 2. File-by-File Analysis

### `libs/deepagents/deepagents/graph.py`

- **Purpose**: This file defines the `create_deep_agent` function, which acts as a high-level constructor for creating pre-configured `langgraph` agents with specialized capabilities.
- **Key Components**:
  - `create_deep_agent()`: The main factory function that assembles the agent, its tools, and its middleware stack.
  - `get_default_model()`: A helper function that provides a default `ChatAnthropic` model instance, specifically `claude-sonnet-4-5-20250929`.

## 3. Public Interface & Use Cases

The primary public interface of this module is the `create_deep_agent` function. It is the designated entry point for users who want to create a deep agent.

**When to use this module:**
- To create an agent capable of managing a to-do list for complex tasks.
- When you need an agent that can interact with a virtual filesystem (list, read, write, edit files).
- For tasks that can be broken down into sub-tasks, which can be delegated to specialized sub-agents.
- As a starting point for building a customized, powerful agent without having to configure all the underlying middleware manually.

## 4. Integration Patterns

The `create_deep_agent` function integrates several components from the `deepagents` and `langchain` ecosystems:

- **Core Agent Logic**: It uses `langchain.agents.create_agent` as the foundation for building the final `CompiledStateGraph`.
- **Dependencies**:
    - `deepagents.backends.protocol`: The filesystem and execution capabilities are provided via a `backend` that adheres to the `BackendProtocol`. This allows for swappable storage and execution environments.
    - `deepagents.middleware`: It heavily relies on custom middleware from this package:
        - `FilesystemMiddleware`: Adds file operation tools (`ls`, `read_file`, etc.).
        - `SubAgentMiddleware`: Enables the agent to define and call sub-agents.
        - `PatchToolCallsMiddleware`: Patches tool calls for better compatibility.
    - `langchain.agents.middleware`: Standard middleware like `TodoListMiddleware`, `SummarizationMiddleware`, and `HumanInTheLoopMiddleware` are used to add core functionalities.
- **Configuration**: The agent is configured by passing parameters like `model`, `tools`, `subagents`, and `checkpointer` directly to the `create_deep_agent` function, which then wires them into the respective middleware and the core agent graph.

## 5. API Reference

### `create_deep_agent()`

Creates and configures a deep agent with built-in capabilities.

| Parameter         | Type                                                   | Default/Notes                                                                                                                                                                                                                               |
|-------------------|--------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `model`           | `str \| BaseChatModel \| None`                          | Optional. The language model to use. Defaults to `claude-sonnet-4-5-20250929` via `get_default_model()`.                                                                                                                                      |
| `tools`           | `Sequence[BaseTool \| Callable \| dict[str, Any]] \| None` | Optional. A list of custom tools for the agent.                                                                                                                                                                                           |
| `system_prompt`   | `str \| None`                                             | Optional. Additional instructions to be appended to the base system prompt.                                                                                                                                                                 |
| `middleware`      | `Sequence[AgentMiddleware]`                            | Optional. A sequence of additional `AgentMiddleware` to apply after the default stack.                                                                                                                                                      |
| `subagents`       | `list[SubAgent \| CompiledSubAgent] \| None`           | Optional. A list of sub-agents that the main agent can invoke.                                                                                                                                                                              |
| `response_format` | `ResponseFormat \| None`                                 | Optional. A structured output format for the agent's responses.                                                                                                                                                                            |
| `context_schema`  | `type[Any] \| None`                                     | Optional. The Pydantic or LangChain schema for the agent's state.                                                                                                                                                                         |
| `checkpointer`    | `Checkpointer \| None`                                   | Optional. A `langgraph` checkpointer for persisting agent state.                                                                                                                                                                            |
| `store`           | `BaseStore \| None`                                     | Optional. A persistent store, required if the backend is a `StoreBackend`.                                                                                                                                                                  |
| `backend`         | `BackendProtocol \| BackendFactory \| None`             | Optional. The backend for file storage and command execution.                                                                                                                                                                               |
| `interrupt_on`    | `dict[str, bool \| InterruptOnConfig] \| None`         | Optional. A dictionary to configure human-in-the-loop interruptions for specific tools.                                                                                                                                                     |
| `debug`           | `bool`                                                 | `False`. If `True`, enables debug mode in `langgraph`.                                                                                                                                                                                     |
| `name`            | `str \| None`                                             | Optional. A name for the agent.                                                                                                                                                                                                             |
| `cache`           | `BaseCache \| None`                                     | Optional. A `langgraph` cache for the agent.                                                                                                                                                                                              |
| **Returns**       | `CompiledStateGraph`                                   | A compiled `langgraph` state graph representing the fully configured deep agent.                                                                                                                                                            |

'''