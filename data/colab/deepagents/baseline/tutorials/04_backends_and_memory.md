# Backends and Long-term Memory in Deep Agents

## 1. Goal

This tutorial explains how to use backends in `deepagents` to provide agents with long-term memory. By default, an agent's file system is ephemeral and exists only for a single session. By using a persistent backend, an agent can maintain files and state across multiple conversations, enabling true long-term memory.

## 2. Prerequisites

To follow this tutorial, you need to have `deepagents` and `deepagents-harbor` installed.

```bash
pip install deepagents deepagents-harbor
```

## 3. Architecture

`deepagents` uses a pluggable backend system to manage file operations. For long-term memory, we can use a `CompositeBackend`. This backend routes file operations to different storage backends based on the file path. For example, we can route files in `/memories/` to a persistent store while keeping other files in an ephemeral in-memory store.

```mermaid
graph TD
    A[Agent] --> B{CompositeBackend};
    B --> C{/memories/*};
    B --> D{default};
    C --> E[StoreBackend (Persistent)];
    D --> F[StateBackend (Ephemeral)];
```

## 4. Implementation

### Available Backends

`deepagents` provides several built-in backends:

- **`StateBackend`** (default): Stores files in the agent's ephemeral state. Files are lost when the session ends.
- **`FilesystemBackend`**: Allows the agent to read and write files directly on the local disk within a specified root directory.
- **`StoreBackend`**: A persistent backend that uses a `langgraph.store` for storage.
- **`CompositeBackend`**: Routes file operations to other backends based on path prefixes.

### Long-term Memory with `CompositeBackend`

The `README.md` provides an excellent example of how to configure a `CompositeBackend` for long-term memory. By mapping the `/memories/` path to a `StoreBackend`, any files written to this directory will persist across sessions.

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

# The InMemoryStore can be replaced with a persistent store like Redis or a database.
store = InMemoryStore()

agent = create_deep_agent(
    backend=CompositeBackend(
        default=StateBackend(),
        routes={"/memories/": StoreBackend(store=store)},
    ),
)

# Now, any files the agent writes to /memories/ will be saved in the store.
# For example, the agent could perform the following action:
# write_file("/memories/user_preferences.txt", "The user prefers concise answers.")
```

### Using a Harbor Backend

The `deepagents-harbor` package provides a `HarborSandbox` backend, which allows the agent to operate within a `harbor` environment. This is useful for tasks that require a sandboxed environment with specific dependencies.

The `HarborSandbox` implements the `SandboxBackendProtocol`, which means it supports executing shell commands.

Here is how you can use the `HarborSandbox` from `deepagents_harbor.backend`:

```python
from deepagents import create_deep_agent
from deepagents_harbor.backend import HarborSandbox
from harbor.environments.docker import DockerEnvironment

# First, create a harbor environment
environment = DockerEnvironment() # You can configure this with a specific image

# Then, create the agent with the HarborSandbox backend
agent = create_deep_agent(
    backend=HarborSandbox(environment=environment),
)

# Now the agent can execute commands and interact with the filesystem
# within the Docker container managed by harbor.
result = agent.invoke({"messages": [{"role": "user", "content": "List all files in the current directory."}]})
```

## 5. Conclusion

By understanding and utilizing backends, you can significantly enhance your agents' capabilities. The `CompositeBackend` is a powerful tool for creating agents with long-term memory, allowing them to learn and evolve across multiple conversations. Furthermore, specialized backends like `HarborSandbox` enable agents to perform tasks in controlled, sandboxed environments.