
# Instrumentation and Utilities Analysis

## 1. Overview

This document provides a technical analysis of the instrumentation and utility modules within the `agentlightning` package. These modules provide the core functionality for tracing, instrumentation, and server management.

- **`agentlightning.instrumentation.agentops`**: This module monkey-patches the `agentops` library to enhance its data capturing capabilities, specifically for token-level details and log probabilities. It also introduces a mechanism to disable communication with the remote AgentOps service, allowing for local-only tracing.

- **`agentlightning.tracer.otel`**: This is the core tracing implementation, providing an `OtelTracer` class that uses OpenTelemetry to create, manage, and export spans. It includes a custom `LightningSpanProcessor` to direct trace data to a `LightningStore`, which acts as a data backend.

- **`agentlightning.utils.otel`**: A collection of helper functions for working with OpenTelemetry. It provides utilities for attribute manipulation (flattening, unflattening, sanitizing), creating structured attributes for tags and links, and safely accessing the global tracer provider.

- **`agentlightning.utils.server_launcher`**: A robust utility for launching and managing `FastAPI` web applications using Uvicorn or Gunicorn. It supports multiple execution modes (`asyncio`, `thread`, `process`) and includes features like health checks and graceful shutdowns.

## 2. File-by-File Analysis

### `agentlightning/instrumentation/agentops.py`

- **Purpose**: To augment the `agentops` library's default instrumentation. It intercepts OpenAI API responses to extract and record `prompt_token_ids`, `response_token_ids`, and `logprobs`, which are not captured by the standard `agentops` library. It supports multiple versions of `agentops` by attempting different patching strategies.

- **Key Components**:
  - `instrument_agentops()`: Applies monkey-patches to `agentops`. It detects the installed version and applies the correct patch for either older (`_handle_response`) or newer (`handle_chat_attributes`) versions.
  - `uninstrument_agentops()`: Reverts the applied patches, restoring the original `agentops` functions.
  - `enable_agentops_service(enabled: bool)`: A global switch to control whether the instrumented `agentops` sends data to the remote AgentOps cloud service. If `False`, exporters and API clients will be bypassed.
  - `Bypassable...` classes (`BypassableAuthenticatedOTLPExporter`, `BypassableV3Client`, etc.): A suite of wrapper classes that inherit from `agentops` and `opentelemetry` components. They check the `_agentops_service_enabled` flag before executing network requests, allowing for silent dropping of data when the service is disabled.

### `agentlightning/tracer/otel.py`

- **Purpose**: Provides the primary tracing mechanism for the `agentlightning` framework. The `OtelTracer` class conforms to the base `Tracer` interface and uses OpenTelemetry as the backend. It is responsible for initializing the tracer provider and processing spans.

- **Key Components**:
  - `OtelTracer`: The main tracer implementation. It manages a global `TracerProvider` and provides methods like `trace_context` and `operation_context` to create and manage spans. It can be configured to send spans directly to a `LightningStore`.
  - `LightningSpanProcessor`: A custom OpenTelemetry `SpanProcessor`. When a span ends, `on_end` is called. This processor intercepts the span, converts it to an `agentlightning.Span` object, and submits it to the configured `LightningStore`. It cleverly runs its own `asyncio` event loop in a daemon thread to perform asynchronous I/O with the store without blocking the application's main thread.
  - `OtelSpanRecordingContext`: An object yielded by `operation_context` that allows the user to record events, exceptions, and attributes on the currently active span.

### `agentlightning/utils/otel.py`

- **Purpose**: A utility belt for OpenTelemetry interactions. It centralizes common tasks related to span attribute management and tracer retrieval, ensuring consistency across the codebase.

- **Key Components**:
  - `get_tracer_provider()` & `get_tracer()`: Safe accessors for the global OpenTelemetry `TracerProvider` and `Tracer`. They include checks to ensure that the tracing system has been initialized.
  - `flatten_attributes(...)` & `unflatten_attributes(...)`: Functions to convert nested dictionaries/lists into a flat dictionary with dot-separated keys (e.g., `{"a": {"b": 1}}` -> `{"a.b": 1}`) and back. This is the standard format for OpenTelemetry attributes.
  - `make_tag_attributes(...)` & `make_link_attributes(...)`: Helper functions that create flattened attributes for special `agentlightning` conventions: `agl.tag` for adding searchable tags to a span, and `agl.link` for creating relationships between spans.
  - `extract_tags_from_attributes(...)` & `extract_links_from_attributes(...)`: The inverse of the `make_` functions, used to parse tags and links from a span's attributes.
  - `sanitize_attributes(...)`: A function to ensure that all values in an attribute dictionary are of a type supported by OpenTelemetry (str, bool, int, float, or lists of these types). It will attempt to JSON-serialize other types.

### `agentlightning/utils/server_launcher.py`

- **Purpose**: To provide a standardized, programmatic way to launch a `FastAPI` application. It abstracts away the complexities of running Uvicorn and Gunicorn in different concurrency models and provides a consistent interface for startup, shutdown, and health checking.

- **Key Components**:
  - `PythonServerLauncher`: The main class that orchestrates the server launch. It takes a `FastAPI` app and `PythonServerLauncherArgs` to configure the launch.
  - `PythonServerLauncherArgs`: A dataclass for configuration, specifying port, host, launch mode (`asyncio`, `thread`, `mp`), number of workers, and timeouts.
  - **Launch Mode Functions**:
    - `run_uvicorn_asyncio`: Runs Uvicorn directly in the current `asyncio` event loop. Includes a watcher to verify startup and health.
    - `run_uvicorn_thread`: Runs Uvicorn in a separate daemon thread.
    - `run_uvicorn_subprocess`: Runs Uvicorn in a separate multiprocessing process.
    - `run_gunicorn`: For multi-worker setups, it launches a Gunicorn master process which in turn forks Uvicorn workers.
  - The launcher uses a `queue` or `multiprocessing.Queue` to communicate readiness or error events from the child thread/process back to the parent.

## 3. Integration & Use Cases

- **Typical Workflow**: A developer would use `OtelTracer` to trace their agent's operations. Within a trace, they might use `instrument_agentops` if they are using `agentops` and want to capture detailed token information. The underlying `OtelTracer` uses utilities from `agentlightning.utils.otel` to format attributes correctly. If the application involves a web server (e.g., for a custom tool or a user-facing interface), `PythonServerLauncher` would be used to manage its lifecycle.

- **Instrumentation**: The `agentops.py` module is a prime example of "downstream instrumentation"—modifying another library at runtime to extract more data. This is a powerful but fragile pattern that depends on the internal implementation of `agentops`.

- **Tracing and Storage**: `OtelTracer` and `LightningSpanProcessor` work together. The tracer creates spans, and the processor decides what to do with them. When a `LightningStore` is configured with OTLP support, the processor can delegate sending spans to a native `LightningStoreOTLPExporter`, which is more efficient. Otherwise, it uses its internal threaded loop to push spans to the store.

## 4. API Reference

### `agentlightning.instrumentation.agentops`

| Function | Signature | Description |
|---|---|---|
| `instrument_agentops` | `instrument_agentops()` | Instruments the `agentops` library to capture token IDs and logprobs. |
| `uninstrument_agentops` | `uninstrument_agentops()` | Removes the instrumentation from the `agentops` library. |
| `enable_agentops_service` | `enable_agentops_service(enabled: bool = True)` | Enables or disables communication with the remote AgentOps service. |

### `agentlightning.tracer.otel.OtelTracer`

| Method | Signature | Description |
|---|---|---|
| `init_worker` | `init_worker(self, worker_id: int, store: Optional[LightningStore] = None)` | Initializes the tracer for a specific worker, setting up the tracer provider. |
| `trace_context` | `async trace_context(self, name: Optional[str] = None, *, store: Optional[LightningStore] = None, rollout_id: Optional[str] = None, attempt_id: Optional[str] = None)` | An async context manager that starts a new trace. Spans created within this context are collected. |
| `operation_context`| `operation_context(self, name: str, attributes: Optional[Attributes] = None, ...)` | A context manager that creates a new span and yields a `SpanRecordingContext` to modify it. |
| `create_span` | `create_span(self, name: str, attributes: Optional[Attributes] = None, ...)` | Creates and immediately ends a single span. |
| `get_last_trace` | `get_last_trace(self) -> List[Span]` | Returns the list of spans captured in the most recent trace context. |

### `agentlightning.utils.otel`

| Function | Signature | Description |
|---|---|---|
| `get_tracer_provider`| `get_tracer_provider(inspect: bool = True) -> TracerProviderImpl` | Gets the configured OpenTelemetry tracer provider. |
| `get_tracer` | `get_tracer(use_active_span_processor: bool = True) -> trace_api.Tracer`| Gets an OpenTelemetry tracer instance. |
| `flatten_attributes` | `flatten_attributes(nested_data: Union[Dict, List], *, expand_leaf_lists: bool = False) -> Dict[str, Any]` | Flattens a nested dictionary or list into a flat dictionary with dot-separated keys. |
| `unflatten_attributes`| `unflatten_attributes(flat_data: Dict[str, Any]) -> Union[Dict, List]` | Reconstructs a nested structure from a flat dictionary. |
| `sanitize_attributes`| `sanitize_attributes(attributes: Dict[str, Any], force: bool = True) -> Attributes` | Sanitizes a dictionary of attributes to be valid OpenTelemetry attribute types. |

### `agentlightning.utils.server_launcher.PythonServerLauncher`

| Method | Signature | Description |
|---|---|---|
| `__init__` | `__init__(self, app: FastAPI, args: PythonServerLauncherArgs)` | Initializes the launcher with a FastAPI app and launch arguments. |
| `serve` | `async serve(self, serve_context: Optional[AsyncContextManager[Any]] = None)` | Starts the server in `asyncio` mode. Blocks until the server is stopped. |
| `serve_in_thread`| `serve_in_thread(self, serve_context: Optional[AsyncContextManager[Any]] = None)` | Starts the server in a new thread. Returns a `StoppableThread` handle. |
| `serve_in_process`| `serve_in_process(self, serve_context: Optional[AsyncContextManager[Any]] = None)` | Starts the server in a new process. Returns a `BaseProcess` handle. |
| `endpoint` | `endpoint` (property) | Returns the full endpoint URL of the running server (e.g., `http://127.0.0.1:8000`). |

