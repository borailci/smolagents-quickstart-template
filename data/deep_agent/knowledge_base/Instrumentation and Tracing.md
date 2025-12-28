'''
# Technical Analysis: Instrumentation and Tracing in `agentlightning`

## 1. Overview

The instrumentation and tracing modules in `agentlightning` form a system for capturing and analyzing the execution flow of AI agent applications. The architecture is centered around a core `Tracer` abstraction, with a primary implementation based on OpenTelemetry (`OtelTracer`). This system allows for detailed data collection from various parts of an application, including interactions with LLMs.

The key responsibilities of this system are:
- **Tracing Execution**: Providing a context manager (`trace_context`) to wrap application logic, capturing operations as spans.
- **Data Enrichment**: Monkey-patching third-party libraries like `agentops` and `litellm` to inject additional, high-value data into traces, such as prompt and response token IDs.
- **Data Persistence**: Storing captured trace data (spans) in a backend-agnostic `LightningStore`, with native support for the OpenTelemetry Protocol (OTLP).
- **Flexible Configuration**: Allowing developers to enable or disable communication with external services (like AgentOps) and to switch between different tracing backends.

## 2. File-by-File Analysis

### `agentlightning/tracer/base.py`

- **Purpose**: This file defines the core abstract interface for all tracers in the `agentlightning` ecosystem.
- **Key Components**:
  - `Tracer (ABC)`: An abstract base class that establishes the contract for tracing implementations. It defines the essential methods that any tracer must provide, ensuring a consistent API for starting traces, creating spans, and retrieving trace data.
  - `set_active_tracer() / get_active_tracer()`: Global functions to manage a process-wide "active" tracer instance. This allows different parts of the application to access the same tracer without passing it explicitly.
  - `with_active_tracer_context`: A decorator that ensures the tracer is set as active during an `async with` block.

### `agentlightning/tracer/otel.py`

- **Purpose**: This file contains the primary, concrete implementation of the `Tracer` interface, using the OpenTelemetry (OTel) framework as the backend.
- **Key Components**:
  - `OtelTracer(Tracer)`: The main class that implements the `Tracer` API. It manages the lifecycle of an OTel `TracerProvider`, registers span processors, and provides the `trace_context` for capturing spans.
  - `LightningSpanProcessor(SpanProcessor)`: A custom OTel `SpanProcessor` that intercepts all ended spans. Its main roles are to keep an in-memory list of spans for immediate retrieval (`get_last_trace`) and to asynchronously submit spans to a `LightningStore` if one is configured.
  - `OtelSpanRecordingContext`: An implementation of `SpanRecordingContext` that wraps an OTel `Span` object, allowing for the recording of exceptions, attributes, and status updates directly on the OTel span.
  - **OTLP Integration**: The tracer has logic to configure and use a `LightningStoreOTLPExporter`, which can send trace data directly to a `LightningStore` that exposes an OTLP-compatible endpoint. This is the more robust, service-oriented way of persisting traces.

### `agentlightning/instrumentation/agentops.py`

- **Purpose**: This module enhances the `agentops` library by monkey-patching it to capture richer data that is not collected by default, such as token IDs and log probabilities.
- **Key Components**:
  - `instrument_agentops()`: The main function that applies the patches. It intelligently detects the installed version of `agentops` and applies the correct patching strategy.
  - `uninstrument_agentops()`: Reverts the patches, restoring the original `agentops` functionality.
  - `Bypassable...` classes (`BypassableAuthenticatedOTLPExporter`, `BypassableV3Client`, etc.): A set of wrapper classes that intercept calls to the AgentOps backend. These can be globally toggled via `enable_agentops_service(enabled: bool)` to run in a "local mode," preventing any data from being sent to the AgentOps service. This is useful for development and testing.

### `agentlightning/instrumentation/litellm.py`

- **Purpose**: This module enhances the `litellm` library's OpenTelemetry integration to capture token IDs.
- **Key Components**:
  - `instrument_litellm()`: Monkey-patches the `set_attributes` method within `litellm`'s `OpenTelemetry` integration class. The patched function calls the original method and then adds `prompt_token_ids` and `response_token_ids` to the span if they are present in the LLM response object.
  - `uninstrument_litellm()`: Restores the original `set_attributes` method.

## 3. Integration & Usage Patterns

**Standard Tracing Workflow**:

1.  **Initialization**: An `OtelTracer` instance is created. It can be initialized with a `LightningStore` to enable data persistence.
2.  **Instrumentation**: `instrument_agentops()` and/or `instrument_litellm()` are called at application startup to enable data enrichment from these libraries.
3.  **Tracing Execution**: The main application logic is wrapped in the tracer's `async with tracer.trace_context(...)` block. This sets up the OTel context and the `LightningSpanProcessor` to capture all spans generated within the block.
4.  **Span Generation**: Inside the context, calls to OTel-instrumented libraries (like `openai` when instrumented by `agentops`) or manual span creation via `tracer.operation_context()` generate spans.
5.  **Data Capture**: The `LightningSpanProcessor` receives each completed span. It adds the span to an internal list and, if a `LightningStore` is configured, asynchronously sends it to the store.
6.  **Trace Retrieval**: After the context block exits, `tracer.get_last_trace()` can be called to get an in-memory list of all spans from that trace for immediate analysis.

## 4. API Reference

### `agentlightning.tracer.base.Tracer`

| Method | Signature | Description |
| --- | --- | --- |
| `trace_context` | `(name: Optional[str] = None, *, store: Optional[LightningStore] = None, rollout_id: Optional[str] = None, attempt_id: Optional[str] = None) -> AsyncContextManager[Any]` | Starts an asynchronous tracing context. All spans generated within this context are captured. |
| `get_last_trace` | `() -> List[Span]` | Retrieves the list of `Span` objects captured during the most recent trace context. |
| `create_span` | `(name: str, attributes: Optional[Attributes] = None, timestamp: Optional[float] = None, status: Optional[TraceStatus] = None) -> SpanCoreFields` | Creates and immediately ends a single span. |
| `operation_context` | `(name: str, attributes: Optional[Attributes] = None, ...) -> ContextManager[SpanRecordingContext]` | A context manager for recording a single operation as a span, allowing for more detailed recording (exceptions, etc.). |
| `init_worker` | `(worker_id: int, store: Optional[LightningStore] = None) -> None` | Initializes the tracer for a specific worker, optionally associating it with a data store. |
| `get_langchain_handler` | `() -> Optional[BaseCallbackHandler]` | Returns a callback handler for integration with LangChain agents. |

### `agentlightning.instrumentation.agentops`

| Function | Signature | Description |
| --- | --- | --- |
| `instrument_agentops`| `()` | Applies monkey-patches to the `agentops` library to capture token IDs and other metadata. |
| `uninstrument_agentops` | `()` | Removes the patches applied by `instrument_agentops`. |
| `enable_agentops_service` | `(enabled: bool = True) -> None` | Globally enables or disables communication with the remote AgentOps service. |

### `agentlightning.instrumentation.litellm`

| Function | Signature | Description |
| --- | --- | --- |
| `instrument_litellm` | `()` | Applies a monkey-patch to `litellm` to capture token IDs in OTel spans. |
| `uninstrument_litellm` | `()` | Removes the patch applied by `instrument_litellm`. |

'''