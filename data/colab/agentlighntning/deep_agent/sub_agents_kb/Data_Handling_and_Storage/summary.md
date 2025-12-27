
# Technical Analysis of `agentlightning.store`

## 1. Overview

The `agentlightning.store` module provides a flexible and extensible data storage layer for the `agentlightning` platform. It is designed to manage the lifecycle of rollouts, attempts, telemetry spans, and other critical data required for coordinating distributed AI agent training and evaluation.

The architecture is centered around the `LightningStore` abstract base class, which defines the high-level API contract for all storage operations. This abstraction is then implemented using different backends. The codebase provides two primary implementations:

1.  **In-Memory Storage**: A non-persistent, in-memory backend suitable for local development, testing, and simple single-process applications.
2.  **MongoDB Storage**: A persistent backend using MongoDB, designed for scalable, distributed, and production environments.

This layered design allows developers to switch between storage backends with minimal code changes.

## 2. Components

### `agentlightning.store.base.LightningStore` (Abstract Base Class)

This is the central abstraction for the entire storage module. It defines the methods that the rest of the `agentlightning` application uses to interact with the data store. Its responsibilities include:

-   **Rollout Lifecycle Management**: Enqueuing, dequeuing, starting, and updating rollouts.
-   **Attempt Tracking**: Creating and updating execution attempts for each rollout.
-   **Span Ingestion**: Storing telemetry data (spans) from rollouts.
-   **Resource Management**: Storing and versioning named resources like model checkpoints or prompts.
-   **Worker Tracking**: Managing the state of worker processes.

### `agentlightning.store.collection.base.LightningCollections` (Abstract Base Class)

This class provides a lower-level abstraction that groups different types of data collections. It serves as a foundation for concrete `LightningStore` implementations. It defines properties for accessing collections of:

-   `rollouts`: `Collection[Rollout]`
-   `attempts`: `Collection[Attempt]`
-   `spans`: `Collection[Span]`
-   `resources`: `Collection[ResourcesUpdate]`
-   `workers`: `Collection[Worker]`
-   `rollout_queue`: `Queue[str]`
-   `span_sequence_ids`: `KeyValue[str, int]`

It also defines an `atomic` context manager for transactional operations.

### `agentlightning.store.collection.memory.MemoryLightningCollections`

This class provides an in-memory implementation of `LightningCollections`. It uses standard Python objects for storage:

-   `ListBasedCollection`: Implements the `Collection` interface using a `list` and `dict` for O(1) primary-key lookups.
-   `ListBasedQueue`: Implements the `Queue` interface using `collections.deque`.
-   `DictBasedKeyValue`: Implements the `KeyValue` interface using a standard `dict`.

This implementation is simple, fast, and has no external dependencies, making it ideal for testing and lightweight use cases.

### `agentlightning.store.collection.mongo.MongoLightningCollections`

This class provides a MongoDB-backed implementation of `LightningCollections`. It maps the collection interfaces to MongoDB operations:

-   `MongoBasedCollection`: Implements the `Collection` interface, mapping queries and updates to MongoDB queries.
-   `MongoBasedQueue`: Implements the `Queue` interface using a dedicated MongoDB collection.
-   `MongoBasedKeyValue`: Implements the `KeyValue` interface.

This implementation is designed for persistence, scalability, and use in distributed systems. It includes features like a connection pool (`MongoClientPool`) and robust error handling for MongoDB-specific issues.

## 3. Public Interface

The primary public interface is the `LightningStore` abstract base class defined in `agentlightning/store/base.py`. Any application code should be written against this interface.

## 4. Integration Patterns

A concrete `LightningStore` implementation is instantiated and passed to the core components of the `agentlightning` application. The choice of implementation (`Memory` vs. `Mongo`) is typically determined at application startup based on configuration. This dependency injection pattern ensures that the application logic remains decoupled from the specific storage backend.

## 5. Use Cases

-   **In-Memory Store (`MemoryLightningCollections`)**: Recommended for scenarios where data persistence is not required. This includes unit tests, integration tests, local development, and running simple, single-process experiments.

-   **MongoDB Store (`MongoLightningCollections`)**: The recommended choice for production and distributed environments. It provides the necessary data persistence, scalability, and transactional support for coordinating multiple workers and preserving experiment results.

## 6. API Reference

This section details the most important classes and their public methods.

### `agentlightning.store.base.LightningStore`

| Method Signature | Description |
|---|---|
| `async def start_rollout(...) -> AttemptedRollout` | Registers a rollout and immediately creates its first attempt. |
| `async def enqueue_rollout(...) -> Rollout` | Persists a rollout in a `queuing` state for later execution. |
| `async def dequeue_rollout(...) -> Optional[AttemptedRollout]` | Claims the oldest queued rollout and transitions it to `preparing`. |
| `async def add_span(span: Span) -> Optional[Span]` | Persists a pre-constructed span. |
| `async def add_otel_span(...) -> Optional[Span]` | Converts and persists an OpenTelemetry span. |
| `async def query_rollouts(...) -> Sequence[Rollout]` | Retrieves rollouts with filtering, sorting, and pagination. |
| `async def query_attempts(...) -> Sequence[Attempt]` | Retrieves all attempts for a given rollout. |
| `async def query_spans(...) -> Sequence[Span]` | Retrieves spans for a rollout, with optional filtering. |
| `async def add_resources(resources: NamedResources) -> ResourcesUpdate` | Persists a new snapshot of named resources. |
| `async def update_rollout(rollout_id: str, ...)` | Updates a rollout's metadata and status. |
| `async def update_attempt(rollout_id: str, attempt_id: str, ...)` | Updates an attempt's metadata and status. |
| `async def query_workers(...) -> Sequence[Worker]` | Queries all registered workers. |

### `agentlightning.store.collection.base.Collection[T]`

| Method Signature | Description |
|---|---|
| `async def size() -> int` | Returns the number of items in the collection. |
| `async def query(...) -> PaginatedResult[T]` | Queries the collection with filtering, sorting, and pagination. |
| `async def get(...) -> Optional[T]` | Gets the first item matching the filter. |
| `async def insert(items: Sequence[T]) -> None` | Adds items to the collection. |
| `async def update(items: Sequence[T], ...)` | Updates items in the collection. |
| `async def upsert(items: Sequence[T], ...)` | Inserts or updates items in the collection. |
| `async def delete(items: Sequence[T]) -> None` | Deletes items from the collection. |

### `agentlightning.store.collection.base.Queue[T]`

| Method Signature | Description |
|---|---|
| `async def enqueue(items: Sequence[T]) -> Sequence[T]` | Appends items to the end of the queue. |
| `async def dequeue(limit: int = 1) -> Sequence[T]` | Pops items from the front of the queue. |
| `async def size() -> int` | Returns the number of items in the queue. |

### `agentlightning.store.collection.base.KeyValue[K, V]`

| Method Signature | Description |
|---|---|
| `async def get(key: K, default: V) -> V` | Gets the value for a given key. |
| `async def set(key: K, value: V) -> None` | Sets the value for a given key. |
| `async def inc(key: K, amount: V) -> V` | Increments a numeric value for a given key. |
