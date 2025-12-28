# Execution and Runner Technical Analysis

## 1. Overview

The Execution and Runner modules in `agentlightning` form the backbone for running agent tasks. They provide a flexible framework for orchestrating how and where agent logic is executed.

- **Execution Strategy (`agentlightning.execution`)**: This component defines the high-level orchestration model. It is responsible for managing processes, communication, and the overall lifecycle of a training or evaluation run. The primary implementation, `ClientServerExecutionStrategy`, allows for distributing the agent's core logic (the "algorithm") and the task executors (the "runners") across different processes or machines.

- **Runner (`agentlightning.runner`)**: This component is responsible for the concrete task execution loop. It fetches tasks from a shared `LightningStore`, executes them using a `LitAgent`, and reports the results back. The `LitAgentRunner` is the standard implementation, providing features like tracing, hooks, and worker heartbeats.

Together, an `ExecutionStrategy` consumes a `Runner` (wrapped in a `RunnerBundle`) and an `AlgorithmBundle` to create a complete, executable session.

## 2. File-by-File Analysis

### `agentlightning/execution/base.py`

- **Purpose**: This file establishes the fundamental contracts for all execution strategies. It defines the abstract `ExecutionStrategy` class and the protocols for the callable bundles that strategies orchestrate.
- **Key Components**:
  - `ExecutionStrategy`: An abstract base class that defines a single public method, `execute()`. Subclasses must implement this method to define how the `algorithm` and `runner` bundles are run. This abstraction separates the "what" (the agent logic) from the "how" (e.g., in-process, client-server).
  - `AlgorithmBundle`: A `Protocol` for a callable that encapsulates the agent's core algorithm logic, typically set up by the `Trainer`.
  - `RunnerBundle`: A `Protocol` for a callable that wraps the runner's setup and its worker loop.

### `agentlightning/execution/client_server.py`

- **Purpose**: This file provides a concrete, multi-process execution strategy that communicates over HTTP. It is designed for scalability and decoupling, allowing the algorithm and runners to run on separate machines.
- **Key Components**:
  - `ClientServerExecutionStrategy`: Implements the `ExecutionStrategy` interface. It can operate in one of three roles:
    - `algorithm`: Runs the algorithm bundle and a `LightningStoreServer` in the current process.
    - `runner`: Runs one or more runner bundle workers, which connect to the `LightningStoreServer` via `LightningStoreClient`.
    - `both`: Orchestrates the full loop locally, spawning runner processes and then running the algorithm and server.
  - **Process Management**: The strategy handles the spawning of runner processes and, in some configurations, the algorithm process. It includes a robust, four-step shutdown escalation to ensure clean resource release: cooperative stop, `SIGINT`, `terminate()`, and `kill()`.

### `agentlightning/runner/base.py`

- **Purpose**: This file defines the abstract `Runner` class, which serves as the interface for all agent task executors.
- **Key Components**:
  - `Runner[T_task]`: An abstract generic base class that defines the lifecycle and execution methods for a runner:
    - **Lifecycle**: `init()`, `init_worker()`, `teardown()`, `teardown_worker()`. These methods manage global and worker-specific resources.
    - **Execution**: `iter()` for continuously processing tasks from the store, and `step()` for executing a single, ad-hoc task. The `run()` method is deprecated.
  - `run_context()`: A context manager to simplify the setup and teardown of a runner for debugging and testing purposes.

### `agentlightning/runner/agent.py`

- **Purpose**: This is the primary, concrete implementation of the `Runner` interface, designed to work with `LitAgent` instances.
- **Key Components**:
  - `LitAgentRunner`: Manages the end-to-end process of executing a rollout. Its key responsibilities include:
    - **Task Polling**: In `iter()` mode, it continuously polls the `LightningStore` for new tasks using `dequeue_rollout`.
    - **Heartbeats**: It periodically sends worker health and system metrics to the store via `update_worker`. This can be run in a separate thread or as an asyncio task.
    - **Tracing**: It wraps the agent's rollout execution within a `Tracer` context, capturing and persisting spans.
    - **Hooks**: It triggers registered `Hook` callbacks at various points in the lifecycle (`on_rollout_start`, `on_trace_end`, etc.).
    - **Result Processing**: It takes the raw return value from the agent's rollout method and standardizes it, emitting reward spans and persisting trace data to the store.

## 3. Integration & Data Flow

1.  **Initialization**: The `Trainer` configures a `LitAgentRunner` and an `ExecutionStrategy` (e.g., `ClientServerExecutionStrategy`).
2.  **Bundling**: The `Trainer` creates an `AlgorithmBundle` and a `RunnerBundle`. The `RunnerBundle` wraps the configured `LitAgentRunner` instance.
3.  **Execution**: The `Trainer` calls `ExecutionStrategy.execute()`, passing it the two bundles and a `LightningStore` instance.
4.  **Process Spawning (`ClientServerExecutionStrategy`)**: In `"both"` mode, the strategy spawns `n_runners` child processes. Each child process will execute the `RunnerBundle`.
5.  **Server & Algorithm Start**: The main process (or a dedicated child process) starts the `LightningStoreServer` and then executes the `AlgorithmBundle`. The algorithm typically populates the store with initial tasks (rollouts) and resources.
6.  **Runner Execution**: Each runner process calls the `RunnerBundle`. Inside the bundle, `LitAgentRunner.iter()` is invoked.
7.  **Task Loop (`LitAgentRunner.iter`)**:
    - The runner calls `store.dequeue_rollout()` to acquire a task.
    - It calls `store.get_resources_by_id()` to fetch the required model weights or other assets.
    - It executes the agent's `training_rollout` or `validation_rollout` method within a tracing context.
    - It processes the result, adds spans to the store via `store.add_span()`, and updates the attempt status with `store.update_attempt()`.
    - The loop continues until no more tasks are available or a stop event is received.
8.  **Shutdown**: When the algorithm finishes or an interrupt is received, the `ExecutionStrategy` coordinates a graceful shutdown of all spawned processes.

## 4. Use Cases

- **Local Debugging**: Use `ClientServerExecutionStrategy(role="both", main_process="runner", n_runners=1)` to run a single runner in the main process for easy debugging, while the algorithm and store server run in a background process.
- **Single-Machine Parallelism**: Use `ClientServerExecutionStrategy(role="both", n_runners=N)` to leverage multiple CPU cores on a single machine. Each runner runs in an isolated process.
- **Distributed Execution**: Deploy the system across multiple machines:
  - **Machine A (Algorithm Server)**: Run with `role="algorithm"`. This machine will host the `LightningStoreServer` and run the main algorithm logic.
  - **Machines B, C, ... (Runner Workers)**: Run with `role="runner"`, configured with the host and port of Machine A. These machines will connect as clients and execute tasks in parallel.

## 5. API Reference

### `agentlightning.execution.base.ExecutionStrategy`

| Method | Signature | Description |
|---|---|---|
| `execute` | `(self, algorithm: AlgorithmBundle, runner: RunnerBundle, store: LightningStore) -> None` | Abstract method to run the provided bundles using a specific orchestration model. |

### `agentlightning.execution.client_server.ClientServerExecutionStrategy`

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self, role: Literal["algorithm", "runner", "both"] \| None = None, server_host: str \| None = None, server_port: int \| None = None, n_runners: int = 1, graceful_timeout: float = 10.0, terminate_timeout: float = 10.0, main_process: Literal["algorithm", "runner"] = "algorithm", managed_store: bool \| None = None, allowed_exit_codes: Iterable[int] = (0, -15)) -> None` | Configures the client-server strategy. |
| `execute` | `(self, algorithm: AlgorithmBundle, runner: RunnerBundle, store: LightningStore) -> None` | Implements the multi-process execution logic based on the configured `role`. |

### `agentlightning.runner.base.Runner`

| Method | Signature | Description |
|---|---|---|
| `init` | `(self, agent: LitAgent[T_task], **kwargs: Any) -> None` | Abstract method to prepare the runner. Called once for all workers. |
| `init_worker` | `(self, worker_id: int, store: LightningStore, **kwargs: Any) -> None` | Abstract method to configure worker-local state. Called once per worker. |
| `teardown` | `(self, *args: Any, **kwargs: Any) -> None` | Abstract method to release global resources. |
| `teardown_worker`| `(self, worker_id: int, *args: Any, **kwargs: Any) -> None` | Abstract method to release per-worker resources. |
| `iter` | `async (self, *, event: Optional[ExecutionEvent] = None) -> None` | Abstract method to run the runner continuously, processing tasks from the store. |
| `step` | `async (self, input: T_task, *, resources: Optional[NamedResources] = None, mode: Optional[RolloutMode] = None, event: Optional[ExecutionEvent] = None) -> Rollout` | Abstract method to execute a single task directly. |
| `run_context` | `(self, *, agent: LitAgent[T_task], store: LightningStore, hooks: Optional[Sequence[Hook]] = None, worker_id: Optional[int] = None) -> Iterator[Runner[T_task]]` | Context manager for simplified setup and teardown in debugging. |

### `agentlightning.runner.agent.LitAgentRunner`

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self, tracer: Tracer, max_rollouts: Optional[int] = None, poll_interval: float = 5.0, heartbeat_interval: float = 10.0, interval_jitter: float = 0.5, heartbeat_launch_mode: Literal["asyncio", "thread"] = "thread", heartbeat_include_gpu: bool = False) -> None` | Initializes the agent runner with tracing, polling, and heartbeat configurations. |
| `init` | `(self, agent: LitAgent[T_task], *, hooks: Optional[Sequence[Hook]] = None, **kwargs: Any) -> None` | Initializes the runner with the agent and registers hooks. |
| `init_worker` | `(self, worker_id: int, store: LightningStore, **kwargs: Any) -> None` | Initializes the runner for a specific worker with its ID and store connection. |
| `teardown` | `(self, *args: Any, **kwargs: Any) -> None` | Cleans up all runner resources, including the tracer. |
| `teardown_worker`| `(self, worker_id: int, *args: Any, **kwargs: Any) -> None` | Cleans up worker-specific resources. |
| `iter` | `async (self, *, event: Optional[ExecutionEvent] = None) -> None` | Runs a loop to continuously poll the store for rollouts and execute them. |
| `step` | `async (self, input: T_task, *, resources: Optional[NamedResources] = None, mode: Optional[RolloutMode] = None, event: Optional[ExecutionEvent] = None) -> Rollout` | Executes a single task directly and returns the completed rollout. |
| `get_agent` | `(self) -> LitAgent[T_task]` | Returns the managed `LitAgent` instance. |
| `get_store` | `(self) -> LightningStore` | Returns the `LightningStore` for the current worker. |
| `get_worker_id`| `(self) -> str` | Returns the formatted worker ID string. |






