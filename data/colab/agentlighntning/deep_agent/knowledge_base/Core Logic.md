## 1. Overview

The `agentlightning` core logic is comprised of a client-server architecture for distributed task execution and a set of data models that define the objects passed between them. The system is designed to manage "rollouts" (tasks), which are executed by clients. These clients can fetch tasks, retrieve associated "resources" (like LLM configurations or prompt templates), and report back the results.

A significant portion of the current core logic (`client.py`, `server.py`, and many types in `core.py`) is marked as **legacy and deprecated**. The modern approach, mentioned throughout the documentation, is a "store-based" architecture, which seems to replace the direct HTTP client/server communication. This analysis covers the legacy components as they are defined in the provided files.

## 2. File-by-File Analysis

### `agentlightning/client.py`

- **Purpose**: Provides a client interface to interact with a legacy `AgentLightningServer`. It handles the communication for fetching tasks, downloading resources, and submitting results.
- **Key Components**:
  - `AgentLightningClient`: The main client class. It offers both synchronous (`requests`) and asynchronous (`aiohttp`) methods. It polls the server for tasks, fetches resources by ID (with local caching), and posts completed "rollouts". This class is explicitly deprecated in favor of `LightningStoreClient`.
  - `DevTaskLoader`: A mock client/server for local development. It simulates the server's behavior by serving a predefined list of tasks and resources from memory, allowing for offline testing. This is also deprecated in favor of `Trainer.dev`.

### `agentlightning/server.py`

- **Purpose**: Implements the legacy HTTP server that dispatches tasks to clients. It uses FastAPI to expose a simple REST API.
- **Key Components**:
  - `AgentLightningServer`: The main server controller. It manages the FastAPI app, handles server startup/shutdown, and orchestrates the underlying data store. It provides methods to queue new tasks and retrieve completed rollouts. It is deprecated in favor of `LightningStoreServer`.
  - `ServerDataStore`: An in-memory, asynchronous store for the server's state. It manages the task queue (`asyncio.Queue`), tracks tasks currently being processed, stores completed rollouts, and versions resources. It is deprecated in favor of `LightningStore`.
  - **API Endpoints**:
    - `GET /task`: A client polls this endpoint to receive the next available task.
    - `GET /resources/{resource_id}`: Fetches a specific version of a resource.
    - `GET /resources/latest`: Fetches the most recent version of a resource.
    - `POST /rollout`: A client sends the results of its task execution to this endpoint.

### `agentlightning/types/core.py`

- **Purpose**: This file is the single source of truth for the data structures used across the client, server, and the broader `agentlightning` ecosystem. It contains a mix of legacy and modern data models.
- **Key Components**:
  - **Legacy Models**: These models are used by the deprecated `client` and `server` modules.
    - `Task`: Represents a unit of work to be performed by a client.
    - `RolloutLegacy`: The payload a client sends back to the server after completing a task. It contains the results, reward, and other metadata.
    - `TaskIfAny`: A wrapper used by the server to indicate if a task is available for a polling client.
  - **Modern Models**: These models are part of the new store-based architecture.
    - `Rollout`: The modern equivalent of a task/rollout, containing richer status, configuration, and metadata.
    - `Attempt`: Represents a single execution attempt of a `Rollout`, allowing for retries.
    - `AttemptedRollout`: A combination of a `Rollout` and its currently active `Attempt`.
    - `RolloutConfig`: Defines retry and timeout policies for a `Rollout`.
    - `Worker`: Represents a client worker process.
  - **Protocols & Hooks**:
    - `Dataset`: A protocol defining a generic interface for datasets, similar to `torch.utils.data.Dataset`.
    - `Hook`: A base class for defining callbacks at different points in the agent runner's lifecycle (e.g., `on_rollout_start`, `on_rollout_end`).

### `agentlightning/types/resources.py`

- **Purpose**: Defines the structure of "resources," which are configurable, versioned entities that can be distributed to clients along with tasks. These resources can be models, prompts, or other tunable parameters.
- **Key Components**:
  - `Resource`: The base class for all resource types.
  - `LLM`: A resource representing a connection to a Language Model, including its endpoint, model name, and sampling parameters.
  - `ProxyLLM`: A specialized `LLM` resource that automatically rewrites the model endpoint to route requests through a proxy. This is used to inject rollout and attempt IDs into the request path for detailed tracking.
  - `PromptTemplate`: A resource for storing and formatting prompt strings, with support for different templating engines.
  - `NamedResources`: A type alias for a dictionary mapping a string name to a resource instance (e.g., `{"main_llm": LLM(...)}`).
  - `ResourcesUpdate`: A payload that bundles a `NamedResources` dictionary with a versioning identifier (`resources_id`), which clients use to fetch the correct set of resources for a given task.

## 3. Integration & Data Flow

The core logic operates on a simple, polled request-response pattern:

1.  An `AgentLightningServer` is started, which opens up HTTP endpoints.
2.  A user or process queues tasks into the server via `server.queue_task()`.
3.  An `AgentLightningClient` starts and begins polling the server's `/task` endpoint.
4.  When a task is available, the server sends a `Task` object to the client.
5.  The `Task` object contains a `resources_id`. The client uses this ID to fetch the corresponding `ResourcesUpdate` from the server's `/resources/{resource_id}` endpoint.
6.  The client executes the task using the provided input and the downloaded resources.
7.  Upon completion, the client packages the results into a `RolloutLegacy` object and `POST`s it back to the server's `/rollout` endpoint.
8.  The server stores the completed rollout for later analysis.

The `DevTaskLoader` variant short-circuits this by replacing the HTTP server with an in-memory queue, but follows the same logical flow.

The newer, store-based architecture appears to replace this direct HTTP communication with a persistent or in-memory database (`LightningStore`), which likely provides more robust features for queuing, retries (`RolloutConfig`, `Attempt`), and worker management (`Worker`).

## 4. API Reference (Legacy Client)

### `agentlightning.client.AgentLightningClient`

| Method | Signature | Description |
|---|---|---|
| **Initialization** | `__init__(self, endpoint: str, poll_interval: float = 5.0, timeout: float = 10.0)` | Initializes the client to connect to a specific server endpoint. |
| **Sync Polling** | `poll_next_task(self) -> Optional[Task]` | Blocks and polls the server until a task is available. |
| **Async Polling** | `poll_next_task_async(self) -> Optional[Task]` | Asynchronously polls the server until a task is available. |
| **Sync Resources** | `get_resources_by_id(self, resource_id: str) -> Optional[ResourcesUpdate]` | Fetches a resource bundle by its unique ID. Results are cached in memory. |
| **Async Resources** | `get_resources_by_id_async(self, resource_id: str) -> Optional[ResourcesUpdate]` | Asynchronously fetches a resource bundle by its unique ID. |
| **Sync Latest Resources**| `get_latest_resources(self) -> Optional[ResourcesUpdate]` | Fetches the latest available resource bundle from the server. |
| **Async Latest Resources**| `get_latest_resources_async(self) -> Optional[ResourcesUpdate]` | Asynchronously fetches the latest resource bundle. |
| **Sync Rollout** | `post_rollout(self, rollout: RolloutLegacy) -> Optional[Dict[str, Any]]` | Submits a completed rollout result to the server. |
| **Async Rollout** | `post_rollout_async(self, rollout: RolloutLegacy) -> Optional[Dict[str, Any]]` | Asynchronously submits a completed rollout result. |
