'''
# Core Components Analysis

## 1. Overview

The core components of the `agentlightning` package provide the foundational infrastructure for distributed task execution, configuration management, and interaction with Large Language Models (LLMs). This includes a legacy client-server system for task orchestration, a powerful command-line configuration utility, a sophisticated LLM proxy built on LiteLLM, and a set of semantic conventions for standardized observability.

A key architectural pattern is the deprecation of the original HTTP-based client/server (`client.py`, `server.py`) in favor of a more robust, store-based architecture, which is hinted at in deprecation warnings. The `llm_proxy.py` is a central, modern component designed for scalable and observable LLM interactions, integrating with a `LightningStore` for persistence.

## 2. File-by-File Analysis

### `agentlightning/client.py`

- **Purpose**: This module provides client classes for interacting with the legacy `agentlightning.server`. It contains utilities for polling tasks, fetching resources, and submitting results. The entire module is deprecated and recommends using `agentlightning.store` APIs for new development.
- **Key Components**:
  - `AgentLightningClient`: A client with both synchronous (`requests`) and asynchronous (`aiohttp`) methods to communicate with the `AgentLightningServer`. It handles polling for tasks, retrieving resource bundles by ID, and posting completed `RolloutLegacy` objects.
  - `DevTaskLoader`: An in-memory mock client for local development and testing. It simulates the server by serving a predefined list of tasks and a static resource bundle, avoiding the need for a live server. It stores submitted rollouts for inspection.

### `agentlightning/server.py`

- **Purpose**: Implements the legacy FastAPI-based HTTP server that manages a queue of tasks, serves them to `AgentLightningClient` instances, and collects the resulting rollouts. This component is also deprecated in favor of the newer store-based architecture.
- **Key Components**:
  - `ServerDataStore`: An asynchronous, in-memory data store that manages the task queue, tracks in-progress tasks, and stores completed rollouts and versioned resources. It uses `asyncio.Lock` to ensure safe parallel access from FastAPI request handlers.
  - `AgentLightningServer`: A controller class that wraps the FastAPI application and `uvicorn` server. It defines the API endpoints (`/task`, `/resources/{id}`, `/rollout`), manages the server lifecycle (`start`, `stop`), and includes logic for handling stale or timed-out tasks.

### `agentlightning/config.py`

- **Purpose**: Provides a utility to automatically generate a command-line interface (CLI) from the `__init__` signatures of Python classes. This simplifies the process of configuring and instantiating multiple components from the command line.
- **Key Components**:
  - `lightning_cli(*classes)`: The primary function that takes one or more classes as input. It inspects their `__init__` methods to create corresponding CLI arguments (e.g., `--myclass.my-arg`). It intelligently handles type conversions for `str`, `int`, `float`, `bool`, `List`, and `Optional` types, and generates help strings. It then parses `sys.argv` and returns instantiated objects of the provided classes.

### `agentlightning/llm_proxy.py`

- **Purpose**: This module contains the `LLMProxy`, a powerful and highly configurable proxy for routing LLM requests. It is built on `litellm` and `FastAPI`/`uvicorn`. The proxy is deeply integrated with the `agentlightning` observability and data persistence model via the `LightningStore`.
- **Key Components**:
  - `LLMProxy`: A class that manages the lifecycle of the proxy server. It can be launched in multiple modes (multiprocess, thread, asyncio) and registers custom middleware and `litellm` callbacks. It uses a temporary YAML file to configure the underlying `litellm` instance with a list of models and other settings.
  - `RolloutAttemptMiddleware`: A FastAPI middleware that intercepts incoming requests. It extracts `rollout_id` and `attempt_id` from the URL path (e.g., `/rollout/{rid}/attempt/{aid}/...`), rewrites the path to a clean one for `litellm`, and injects the IDs as request headers (`x-rollout-id`, `x-attempt-id`) for tracing purposes.
  - `StreamConversionMiddleware`: A crucial middleware that converts streaming API requests into non-streaming ones before they hit the `litellm` backend, and then reconstructs a standard Server-Sent Events (SSE) stream from the complete response. This serves as a workaround for bugs in `litellm`'s OpenTelemetry implementation for streaming responses.
  - `LightningSpanExporter`: A custom OpenTelemetry `SpanExporter` that buffers exported spans. It waits until it has collected the complete trace for a root span before flushing the entire subtree to the configured `LightningStore` or an OTLP endpoint. This ensures that all related spans are persisted together with the correct `rollout_id` and `attempt_id`.

### `agentlightning/semconv.py`

- **Purpose**: This file defines a set of semantic conventions for OpenTelemetry tracing within the `agentlightning` ecosystem. It provides standardized names for spans and attributes, ensuring consistency in collected trace data.
- **Key Components**:
  - **Span Name Constants**: Defines standard names for common operations, such as `AGL_MESSAGE`, `AGL_OPERATION`, `AGL_REWARD`, etc.
  - `LightningResourceAttributes`: An `Enum` defining resource attribute keys that are attached to all spans in a trace, such as `agentlightning.rollout_id` and `agentlightning.attempt_id`.
  - `LightningSpanAttributes`: An `Enum` defining attribute keys for data specific to a single span, like `agentlightning.reward`, `agentlightning.tag`, and `agentlightning.operation.input`.
  - **Pydantic Models**: Includes models like `RewardPydanticModel` and `LinkPydanticModel` for stricter, type-safe implementation of these conventions in helper functions.

## 3. Integration & Data Flow

The components, while some are legacy, illustrate a clear design pattern for distributed systems and observability.

1.  **Configuration (`config.py`)**: The `lightning_cli` function acts as the entry point for many applications, allowing developers to instantiate and configure major components like clients, servers, or trainers from the command line without writing boilerplate parsing code.

2.  **Legacy Task Execution (`client.py` & `server.py`)**: The `AgentLightningServer` maintains a queue of tasks. An `AgentLightningClient` polls the server's `/task` endpoint. Upon receiving a task, the client fetches the required resources from the `/resources/...` endpoint, executes the task, and `POST`s the result back to the `/rollout` endpoint. This entire flow is marked as deprecated.

3.  **Modern LLM Interaction (`llm_proxy.py`)**: The `LLMProxy` is the modern gateway for all LLM calls. A client (e.g., an agent) makes an OpenAI-compatible request to the proxy. The `RolloutAttemptMiddleware` intercepts this, adding crucial tracing headers. The request is processed by `litellm`, which invokes callbacks like `LightningOpenTelemetry`. The resulting traces are exported via the `LightningSpanExporter` to a `LightningStore`. The `StreamConversionMiddleware` ensures this process works reliably even for streaming requests.

## 4. API Reference

### `agentlightning.client.AgentLightningClient`

| Method | Signature | Description |
| --- | --- | --- |
| `__init__` | `(self, endpoint: str, poll_interval: float = 5.0, timeout: float = 10.0)` | Initializes the client. |
| `poll_next_task_async` | `(self) -> Optional[Task]` | Asynchronously polls the server for the next available task. |
| `get_resources_by_id_async` | `(self, resource_id: str) -> Optional[ResourcesUpdate]` | Asynchronously fetches a resource bundle by its ID. |
| `get_latest_resources_async` | `(self) -> Optional[ResourcesUpdate]` | Asynchronously fetches the latest available resource bundle. |
| `post_rollout_async` | `(self, rollout: RolloutLegacy) -> Optional[Dict[str, Any]]` | Asynchronously posts a completed rollout to the server. |
| `poll_next_task` | `(self) -> Optional[Task]` | Synchronously polls the server for the next available task. |
| `get_resources_by_id` | `(self, resource_id: str) -> Optional[ResourcesUpdate]` | Synchronously fetches a resource bundle by its ID. |
| `get_latest_resources` | `(self) -> Optional[ResourcesUpdate]` | Synchronously fetches the latest available resource bundle. |
| `post_rollout` | `(self, rollout: RolloutLegacy) -> Optional[Dict[str, Any]]` | Synchronously posts a completed rollout to the server. |

### `agentlightning.server.AgentLightningServer`

| Method | Signature | Description |
| --- | --- | --- |
| `__init__` | `(self, host: str = "127.0.0.1", port: int = 8000, task_timeout_seconds: float = 300.0)` | Initializes the server controller. |
| `start` | `async (self)` | Starts the FastAPI server in the background. |
| `stop` | `async (self)` | Stops the FastAPI server. |
| `queue_task` | `async (self, sample: Any, mode: ..., resources_id: ..., metadata: ...) -> str` | Adds a new task to the server's processing queue. |
| `update_resources` | `async (self, resources: NamedResources) -> str` | Publishes a new version of resources to the server. |
| `get_completed_rollout` | `async (self, rollout_id: str) -> Optional[RolloutLegacy]` | Retrieves a single completed rollout by its ID. |
| `poll_completed_rollout` | `async (self, rollout_id: str, timeout: Optional[float] = None) -> Optional[RolloutLegacy]` | Polls for a specific rollout until it is available or timeout occurs. |
| `retrieve_completed_rollouts` | `async (self) -> List[RolloutLegacy]` | Retrieves all completed rollouts and clears the internal buffer. |

### `agentlightning.config.lightning_cli`

| Method | Signature | Description |
| --- | --- | --- |
| `lightning_cli` | `(*classes: Type[CliConfigurable]) -> CliConfigurable | Tuple[CliConfigurable, ...]` | Parses command-line arguments to configure and instantiate the given classes. |

### `agentlightning.llm_proxy.LLMProxy`

| Method | Signature | Description |
| --- | --- | --- |
| `__init__` | `(self, port, model_list, store, host, litellm_config, ...)` | Initializes the LLM Proxy. See source for full signature. |
| `start` | `async (self)` | Starts the proxy server and initializes global middleware and callbacks. |
| `stop` | `async (self)` | Stops the proxy server and cleans up resources. |
| `restart` | `async (self, *, _port: int | None = None)` | Restarts the server, optionally on a new port. |
| `is_running` | `(self) -> bool` | Returns `True` if the server is currently active. |
| `set_store` | `(self, store: LightningStore) -> None` | Sets the `LightningStore` instance for the proxy to use. |
| `update_model_list` | `(self, model_list: List[ModelConfig]) -> None` | Replaces the current model list. |
| `as_resource` | `(self, rollout_id, attempt_id, model, ...) -> LLM` | Creates an `LLM` resource object pointing to this proxy with rollout context. |

'''