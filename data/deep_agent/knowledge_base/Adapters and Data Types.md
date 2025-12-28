
# Adapters and Data Types Analysis

## 1. Overview

The `agentlightning.adapter` and `agentlightning.types` modules form the data foundation for Agent Lightning. They define the core data structures used throughout the system and provide adapters to convert data between different formats.

- **`agentlightning.types`**: This package contains Pydantic models that define the shape of core concepts like `Rollout`, `Attempt`, `Task`, and various configuration and status types. These models ensure data consistency and provide validation across different components of the Agent Lightning framework.
- **`agentlightning.adapter`**: This package provides a set of tools for transforming data from one format to another. The primary use case is converting trace data (sequences of `Span` objects) into structured formats suitable for other systems, such as the OpenAI fine-tuning API.

## 2. File-by-File Analysis

### `agentlightning/adapter/base.py`

- **Purpose**: This file defines the base classes for all data adapters in the system. It establishes a generic and reusable pattern for data transformation.
- **Key Components**:
  - `Adapter(Generic[T_from, T_to])`: A generic base class for creating synchronous adapters. It implements the `__call__` method, allowing adapter instances to be used like functions. Subclasses must implement the `adapt` method to perform the actual data conversion.
  - `OtelTraceAdapter(Generic[T_to])`: A specialized adapter that inherits from `Adapter`. It is designed to convert a sequence of OpenTelemetry `ReadableSpan` objects into a target format `T_to`.
  - `TraceAdapter(Generic[T_to])`: Similar to `OtelTraceAdapter`, but specifically for converting Agent Lightning's internal `Span` objects into a target format `T_to`.

### `agentlightning/adapter/messages.py`

- **Purpose**: This module provides a concrete implementation of `TraceAdapter` to convert trace data into the format expected by OpenAI's chat completion and fine-tuning APIs.
- **Key Components**:
  - `OpenAIMessages(TypedDict)`: A dictionary type that defines the structure for OpenAI-compatible messages, including a list of messages and an optional list of tools.
  - `TraceToMessages(TraceAdapter[List[OpenAIMessages]])`: The main adapter class. It takes a sequence of `Span` objects, reconstructs the conversation flow (prompts, completions, tool calls), and outputs a list of `OpenAIMessages` objects ready for use with the OpenAI API.
  - `group_genai_dict(...)`: A helper function that converts flattened span attributes (e.g., `gen_ai.prompt.0.role`) into nested Python dictionaries and lists.
  - `convert_to_openai_messages(...)`: A generator function that takes the intermediate representation of prompts and completions and yields `OpenAIMessages` objects.

### `agentlightning/types/core.py`

- **Purpose**: This is the central file for data models in Agent Lightning. It defines the structure of rollouts, attempts, tasks, and other fundamental entities.
- **Key Components**:
  - **Rollout and Attempt Models**:
    - `Rollout`: Represents a single end-to-end execution of an agent task. It includes an ID, input, status (`queuing`, `running`, etc.), and configuration.
    - `Attempt`: Represents a single try of a `Rollout`. A rollout can have multiple attempts due to retries.
    - `AttemptedRollout`: A combined model that pairs a `Rollout` with its current `Attempt`.
    - `RolloutConfig`: Defines settings for a rollout, such as timeouts and retry conditions.
  - **Task Models (Legacy)**:
    - `Task`: A legacy model for representing a work item for an agent. Newer workflows use the `LightningStore` APIs directly.
  - **Status and Mode Types**:
    - `RolloutStatus`, `AttemptStatus`, `WorkerStatus`: `Literal` types that define the possible states for rollouts, attempts, and workers, respectively.
    - `RolloutMode`: A `Literal` type for the execution mode (`train`, `val`, `test`).
  - **Hooks**:
    - `Hook`: A base class for defining callbacks that can be triggered at different points in the agent runner's lifecycle (e.g., `on_trace_start`, `on_rollout_end`).
  - **Pagination and Filtering**:
    - `PaginatedResult`: A sequence-like container for query results that includes pagination metadata (`limit`, `offset`, `total`).
    - `FilterOptions`, `SortOptions`: TypedDicts that define the structure for filtering and sorting queries.

### `agentlightning/types/resources.py`

- **Purpose**: This file was not part of the provided list, but based on the imports in `agentlightning/types/core.py` and its name, it can be inferred that it defines data models related to the computational and data resources required for a rollout. For instance, it might contain a `Resources` class that specifies GPU requirements, data paths, or model weights.

## 3. Integration and Data Flow

The typical data flow is as follows:

1.  A `Rollout` is created and enqueued in the `LightningStore`.
2.  A `Runner` dequeues the `Rollout`, creating an `Attempt`.
3.  During execution, the agent and its tools generate trace data, which is captured as a sequence of `Span` objects.
4.  After the rollout is complete, a `TraceAdapter` like `TraceToMessages` can be used to process the sequence of `Span`s.
5.  The adapter transforms the spans into a structured format, like `OpenAIMessages`.
6.  This structured data can then be used for various purposes, such as fine-tuning a model, analytics, or evaluation.

The `core.py` models are used at every step to pass data between components, from the initial queuing of a `Rollout` to the final storage of results and spans.

## 4. API Reference

| Class / Type | Signature / Fields | Description |
| :--- | :--- | :--- |
| **`Adapter`** | `class Adapter(Generic[T_from, T_to])` | Generic base class for data transformation. Must implement `adapt`. |
| | `adapt(self, source: T_from, /) -> T_to` | Abstract method for conversion logic. |
| **`TraceAdapter`** | `class TraceAdapter(Adapter[Sequence[Span], T_to], Generic[T_to])` | Base adapter for converting a sequence of `Span` objects. |
| **`TraceToMessages`**| `class TraceToMessages(TraceAdapter[List[OpenAIMessages]])` | Converts a sequence of `Span` objects to `OpenAIMessages`. |
| | `adapt(self, source: Sequence[Span], /) -> List[OpenAIMessages]` | Performs the transformation from spans to OpenAI messages. |
| **`Rollout`** | `rollout_id: str`<br>`input: TaskInput`<br>`status: RolloutStatus`<br>... | The central model representing a single agent execution. |
| **`Attempt`** | `rollout_id: str`<br>`attempt_id: str`<br>`status: AttemptStatus`<br>... | Represents one execution attempt for a `Rollout`. |
| **`RolloutConfig`** | `timeout_seconds: float`<br>`max_attempts: int`<br>... | Configuration for retries and timeouts for a `Rollout`. |
| **`Hook`** | `class Hook(ParallelWorkerBase)` | Base class for lifecycle hooks. |
| | `async def on_rollout_start(...)` | Hook called before a rollout attempt begins. |
| | `async def on_rollout_end(...)` | Hook called after a rollout attempt completes. |
| **`PaginatedResult`**| `class PaginatedResult(BaseModel, Sequence[T_item])` | A container for paginated query results. |
| | `items: Sequence[T_item]`<br>`limit: int`<br>`offset: int`<br>`total: int` | Fields for the items and pagination metadata. |
| **`FilterOptions`** | `Mapping[str, Union[FilterField, ...]]` | A mapping to define query filters. |

