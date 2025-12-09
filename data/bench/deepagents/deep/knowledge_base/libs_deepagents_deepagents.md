'''
# DeepAgents Library Documentation

## Overview

The `deepagents` library is a Python framework for building sophisticated AI agents. It extends the capabilities of standard LangChain agents by providing a rich set of built-in features, including filesystem interaction, sub-agent delegation, and robust middleware. The primary goal of this library is to enable the creation of "deep agents" that can perform complex, multi-step tasks by interacting with a sandboxed environment and delegating work to specialized sub-agents.

## Entry Points

The main entry point for creating an agent is the `create_deep_agent` function located in `deepagents/graph.py`.

```python
# deepagents/graph.py

def create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: list[SubAgent | CompiledSubAgent] | None = None,
    # ... other parameters
) -> CompiledStateGraph:
    # ...
```

To get started, a developer would typically call this function, providing a model, a list of custom tools (if any), and a system prompt. The function handles the composition of the agent, including the integration of default and custom middleware.

## Key Concepts

- **AgentMiddleware**: A component that intercepts and modifies the behavior of an agent. The `deepagents` library uses middleware to provide features like filesystem access (`FilesystemMiddleware`) and sub-agent delegation (`SubAgentMiddleware`).

- **SubAgent**: A specialized agent that can be invoked by the main agent to perform a specific task. Sub-agents are defined with a name, description, system prompt, and a set of tools. They are managed by the `SubAgentMiddleware` and invoked via the `task` tool.

- **BackendProtocol**: An interface that defines how the agent interacts with the external environment, such as the filesystem or a sandbox for code execution. The `FilesystemMiddleware` relies on a backend that implements this protocol.

- **FilesystemState**: A LangGraph state object that holds the state of the virtual filesystem, including the content of files. It uses a custom reducer function (`_file_data_reducer`) to handle state updates, such as file creation and deletion.

## Dependencies & Relationships

- **`create_deep_agent` → `create_agent` (LangChain)**: The core agent creation logic is delegated to LangChain's `create_agent` function.

- **`create_deep_agent` → Middlewares**: `create_deep_agent` composes a series of middleware, including:
    - `TodoListMiddleware`: For managing a to-do list.
    - `FilesystemMiddleware`: Provides filesystem tools (`ls`, `read_file`, etc.).
    - `SubAgentMiddleware`: Provides the `task` tool for invoking sub-agents.
    - `SummarizationMiddleware`: For summarizing long conversations.

- **`FilesystemMiddleware` → `BackendProtocol`**: The filesystem tools within this middleware delegate their operations to a backend object that conforms to the `BackendProtocol`.

- **`SubAgentMiddleware` → `create_agent`**: The `SubAgentMiddleware` dynamically creates sub-agents by calling `create_agent` for each sub-agent specification.

## Patterns & Conventions

- **Middleware-based Architecture**: The library heavily relies on the middleware pattern to extend the agent's functionality. This makes the system modular and easy to customize.

- **Backend Abstraction**: The use of the `BackendProtocol` decouples the agent's filesystem logic from the specific implementation of the filesystem, allowing for different backends (e.g., in-memory, on-disk) to be used.

- **State Reducers**: The `FilesystemState` uses a custom reducer (`_file_data_reducer`) to manage state updates. This is a common pattern in LangGraph for handling complex state transitions.

- **Tool Generators**: Functions like `_ls_tool_generator` and `_read_file_tool_generator` in `middleware/filesystem.py` act as factories for creating the filesystem tools. This keeps the tool creation logic organized.

## Code Examples

### 1. Creating a Deep Agent

```python
# From deepagents/graph.py

deep_agent = create_deep_agent(
    model=get_default_model(),
    tools=[MyCustomTool()],
    system_prompt="You are a helpful assistant.",
    subagents=[
        {
            "name": "code_reviewer",
            "description": "Reviews code for quality and errors.",
            "system_prompt": "You are a code reviewer.",
            "tools": [CodeAnalysisTool()],
        }
    ]
)
```

**Why this matters:** This snippet shows the primary entry point for creating a deep agent. It demonstrates how to configure the agent with a custom model, tools, and a sub-agent, showcasing the library's ease of use and extensibility.

### 2. Filesystem Middleware and Tools

```python
# From deepagents/middleware/filesystem.py

def _read_file_tool_generator(
    backend: BackendProtocol | Callable[[ToolRuntime], BackendProtocol],
    custom_description: str | None = None,
) -> BaseTool:
    # ...
    async def async_read_file(
        file_path: str,
        runtime: ToolRuntime[None, FilesystemState],
        offset: int = DEFAULT_READ_OFFSET,
        limit: int = DEFAULT_READ_LIMIT,
    ) -> str:
        resolved_backend = _get_backend(backend, runtime)
        file_path = _validate_path(file_path)
        return await resolved_backend.aread(file_path, offset=offset, limit=limit)

    return StructuredTool.from_function(
        name="read_file",
        description=tool_description,
        func=sync_read_file,
        coroutine=async_read_file,
    )
```

**Why this matters:** This example illustrates how a filesystem tool is generated. It shows the delegation to a backend, the validation of the file path, and the creation of a `StructuredTool`. This pattern is used for all filesystem tools, ensuring consistency and security.

### 3. Sub-Agent Middleware

```python
# From deepagents/middleware/subagents.py

class SubAgentMiddleware(AgentMiddleware):
    def __init__(
        self,
        *,
        default_model: str | BaseChatModel,
        default_tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
        # ... other parameters
    ) -> None:
        super().__init__()
        task_tool = _create_task_tool(
            default_model=default_model,
            default_tools=default_tools or [],
            # ...
        )
        self.tools = [task_tool]
```

**Why this matters:** This code shows how the `SubAgentMiddleware` creates and provides the `task` tool to the agent. This tool is the gateway for the agent to delegate tasks to sub-agents, which is a core feature of the `deepagents` library.

## Tutorial Hints

- **How do I add a new filesystem tool?**
  - You would need to modify the `FilesystemMiddleware` in `middleware/filesystem.py`. Follow the pattern of the existing tool generators (e.g., `_read_file_tool_generator`) to create a new function that defines your tool's logic and returns a `StructuredTool`. Don't forget to add the new tool to the list of tools created by the middleware.

- **How do I configure a custom sub-agent?**
  - When calling `create_deep_agent`, pass a list of sub-agent dictionaries to the `subagents` parameter. Each dictionary should define the `name`, `description`, `system_prompt`, and `tools` for the sub-agent.

- **What if I want to use a different backend for the filesystem?**
  - You can create your own backend class that implements the `BackendProtocol`. Then, when creating the `FilesystemMiddleware`, you can pass an instance of your custom backend to the `backend` parameter. For example, `FilesystemMiddleware(backend=MyCustomBackend())`.

- **Pitfall: Forgetting to provide a backend**
  - The `FilesystemMiddleware` requires a backend to function. If you don't provide one, it will default to a `StateBackend`, which might not be what you want for persistent storage. Always be explicit about the backend you are using.

- **Prerequisite: Understanding LangChain and LangGraph**
  - This library is built on top of LangChain and LangGraph. A good understanding of these two libraries, especially the concepts of agents, tools, and state management in LangGraph, is essential for working with `deepagents` effectively.
'''