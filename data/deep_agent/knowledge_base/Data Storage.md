
# Data Storage Analysis

## 1. Overview

The `agentlightning.store` module provides a flexible data storage layer for the `agentlightning` package. It is designed to manage the state of training rollouts, including their execution attempts, telemetry data (spans), and associated resources. The storage system is built around an abstract base class, `LightningStore`, which defines a contract for various storage backends. The package includes three concrete implementations: an in-memory store for simple use cases, a MongoDB-based store for persistent and scalable storage, and a generic collection-based implementation that can be extended to support other backends.

## 2. File-by-File Analysis

### `agentlightning/store/base.py`

- **Purpose**: This file defines the core interface for all data storage implementations. It introduces the `LightningStore` abstract base class, which specifies the methods that any concrete storage backend must implement.
- **Key Components**:
  - `LightningStore`: An abstract class that defines the API for managing rollouts, attempts, spans, and resources. It includes methods for creating, querying, updating, and deleting these entities.
  - `LightningStoreCapabilities`: A `TypedDict` that describes the capabilities of a `LightningStore` implementation (e.g., thread-safety, async-safety).
  - `LightningStoreStatistics`: A `TypedDict` for reporting statistics about the store.
  - Helper functions like `is_queuing`, `is_running`, and `is_finished` to check the status of a rollout.

### `agentlightning/store/collection_based.py`

- **Purpose**: This file provides a generic implementation of `LightningStore` that uses a collection-based approach. The `CollectionBasedLightningStore` class implements the `LightningStore` interface by delegating the actual data operations to a `LightningCollections` object.
- **Key Components**:
  - `CollectionBasedLightningStore`: A generic class that implements the `LightningStore` interface. It handles the business logic of managing rollouts and attempts, while the `LightningCollections` object handles the data persistence.
  - Decorators:
    - `@tracked`: A decorator for tracking the execution time and status of store methods using a metrics backend.
    - `@healthcheck_before`: A decorator that triggers a health check to identify and handle unhealthy (e.g., timed-out) rollouts before executing a store method.

### `agentlightning/store/memory.py`

- **Purpose**: This file contains an in-memory implementation of the `LightningStore`. It is suitable for single-process applications or testing environments where data persistence is not required.
- **Key Components**:
  - `InMemoryLightningStore`: A subclass of `CollectionBasedLightningStore` that uses `InMemoryLightningCollections` as its data backend. It includes a memory management mechanism to evict old span data when memory usage exceeds a configured threshold, preventing the application from running out of memory.

### `agentlightning/store/mongo.py`

- **Purpose**: This file provides a `LightningStore` implementation that uses MongoDB for data persistence.
- **Key Components**:
  - `MongoLightningStore`: A subclass of `CollectionBasedLightningStore` that uses `MongoLightningCollections` to store data in a MongoDB database. This implementation is suitable for distributed applications where multiple processes need to share and persist the state of training rollouts.

## 3. Architecture & Data Flow

The storage architecture is designed to be modular and extensible. The `LightningStore` class defines a clear API, and the `CollectionBasedLightningStore` provides a solid foundation for creating new storage backends. The data flow can be summarized as follows:

1.  **Rollout Creation**: An algorithm or a user creates a new rollout by calling `start_rollout` or `enqueue_rollout` on a `LightningStore` instance.
2.  **Rollout Execution**: A runner process dequeues a rollout, executes it, and reports its progress by adding spans to the store.
3.  **State Management**: The store manages the lifecycle of rollouts and attempts, transitioning them through various statuses (e.g., `queuing`, `running`, `succeeded`, `failed`).
4.  **Data-Access**: Algorithms can query the store to retrieve the results of rollouts, analyze their performance, and make decisions for subsequent training steps.

## 4. Integration Points

- **Verified Dependencies**:
    - `agentlightning.types`: The store module heavily relies on the data structures defined in this module (e.g., `Rollout`, `Attempt`, `Span`).
    - `opentelemetry.sdk.trace`: Used for handling OpenTelemetry spans.
    - `pymongo`: The `MongoLightningStore` uses this library to interact with MongoDB.
    - `psutil`: The `InMemoryLightningStore` uses this library to detect the total system memory.

## 5. API Reference

### `agentlightning.store.base.LightningStore`

| Method | Signature | Description |
|---|---|---|
| `start_rollout` | `(self, input: TaskInput, mode: RolloutMode = None, resources_id: str = None, config: RolloutConfig = None, metadata: Dict[str, Any] = None, worker_id: str = None) -> AttemptedRollout` | Registers and starts a new rollout immediately. |
| `enqueue_rollout` | `(self, input: TaskInput, mode: Literal["train", "val", "test"] = None, resources_id: str = None, config: RolloutConfig = None, metadata: Dict[str, Any] = None) -> Rollout` | Adds a new rollout to the queue for later execution. |
| `dequeue_rollout` | `(self, worker_id: Optional[str] = None) -> Optional[AttemptedRollout]` | Claims the oldest queued rollout for execution. |
| `add_span` | `(self, span: Span) -> Optional[Span]` | Persists a telemetry span. |
| `query_rollouts` | `(self, *, status_in: Optional[Sequence[RolloutStatus]] = None, rollout_id_in: Optional[Sequence[str]] = None, ...) -> Sequence[Rollout]` | Queries for rollouts based on various filter criteria. |
| `update_rollout` | `(self, rollout_id: str, status: RolloutStatus | Unset = UNSET, ...) -> Rollout` | Updates the properties of a rollout. |
| `update_attempt` | `(self, rollout_id: str, attempt_id: str \| Literal["latest"], status: AttemptStatus \| Unset = UNSET, ...) -> Attempt` | Updates the properties of an attempt. |

### `agentlightning.store.memory.InMemoryLightningStore`

A concrete implementation of `LightningStore` that stores data in memory.

### `agentlightning.store.mongo.MongoLightningStore`

A concrete implementation of `LightningStore` that uses MongoDB for data persistence.
