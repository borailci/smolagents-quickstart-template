
# Client and Server Technical Analysis

## 1. Overview

The client-server architecture in `agentlightning` is designed to orchestrate distributed agent rollouts. The system is split into two primary roles: an "algorithm" side and a "runner" side. The algorithm side typically manages the overall process and serves as a central point of coordination, while the runner side consists of one or more workers that execute agent tasks.

The core component for this architecture is the `ClientServerExecutionStrategy`, which manages the lifecycle of these two roles. It can run them in separate processes on the same machine or allow them to run on different machines, communicating over HTTP. The runners themselves are implemented by `LitAgentRunner`, which is responsible for polling tasks, executing them with a `LitAgent`, and handling tracing, hooks, and heartbeats.

Communication and state sharing between the algorithm and runner processes are handled through a `LightningStore`, which is exposed as a web service by `LightningStoreServer` on the algorithm side and accessed by `LightningStoreClient` on the runner side.

## 2. File-by-File Analysis

### `agentlightning/execution/base.py`

- **Purpose**: This file defines the fundamental abstractions for all execution strategies in the framework.
- **Key Components**:
  - `ExecutionStrategy`: An abstract base class that defines the contract for orchestrating algorithm and runner bundles. Its primary method is `execute()`, which subclasses must implement to define how the bundles are run.
  - `AlgorithmBundle` (Protocol): A callable that encapsulates the algorithm's logic. It receives a `LightningStore` instance and a stop event.
  - `RunnerBundle` (Protocol): A callable that wraps the runner's setup and worker loop. It receives a `LightningStore`, a `worker_id`, and a stop event.

### `agentlightning/execution/client_server.py`

- **Purpose**: This file contains the `ClientServerExecutionStrategy`, which implements the `ExecutionStrategy` interface for a distributed, multi-process environment. It enables running the algorithm and runners as separate client-server processes communicating via HTTP.
- **Key Components**:
  - `ClientServerExecutionStrategy`: The central orchestrator. It can operate in three distinct roles:
    - `algorithm`: Runs the `LightningStoreServer` and the algorithm bundle.
    - `runner`: Connects to a remote store server and runs one or more runner bundles.
    - `both`: Spawns runner processes and then runs the algorithm and server on the same machine.
  - It manages the entire process lifecycle, including startup, graceful shutdown (with a four-step escalation from cooperative stop to `kill`), and error handling.

### `agentlightning/execution/inter_process.py`

- **Purpose**: This file serves as a placeholder for a future `InterProcessExecutionStrategy`.
- **Key Components**:
  - `InterProcessExecutionStrategy`: A non-functional placeholder class that reserves the `ipc` alias for a future implementation. It currently raises `NotImplementedError`.

### `agentlightning/runner/agent.py`

- **Purpose**: This module provides the concrete implementation of a runner, `LitAgentRunner`, which is designed to execute tasks defined by a `LitAgent`.
- **Key Components**:
  - `LitAgentRunner`: The primary worker class. Its responsibilities include:
    - Polling the `LightningStore` for new tasks.
    - Executing agent rollouts using the `LitAgent`'s logic.
    - Managing tracing via a `Tracer` instance, creating and storing spans for each rollout.
    - Invoking registered `Hook` callbacks at various stages of the execution lifecycle.
    - Sending periodic heartbeats to the `LightningStore` to signal that the worker is alive and report system metrics.

## 3. Integration and Data Flow

The `ClientServerExecutionStrategy` acts as the entry point. When its `execute` method is called, it receives an `AlgorithmBundle` and a `RunnerBundle`.

1.  **Role: `both` (Default)**
    - The strategy spawns `n_runners` new processes.
    - In each child process, the `RunnerBundle` is invoked, which typically starts a `LitAgentRunner`.
    - Each `LitAgentRunner` initializes a `LightningStoreClient` to connect to the server.
    - The main process then starts a `LightningStoreServer` and executes the `AlgorithmBundle` against it.
    - Runners poll the store for tasks, execute them, and write results (spans, rewards) back to the store.
    - The algorithm observes the store and coordinates the overall process.

2.  **Role: `algorithm`**
    - The strategy starts the `LightningStoreServer` and runs the `AlgorithmBundle` in the current process. It does not spawn any runners.

3.  **Role: `runner`**
    - The strategy spawns `n_runners` processes. Each process initializes a `LitAgentRunner` which connects as a client to an externally running `LightningStoreServer`.

The `LitAgentRunner` itself follows a clear lifecycle: `init` -> `init_worker` -> `iter` (or `run_once`) -> `teardown_worker` -> `teardown`. During its run, it uses a `Tracer` to trace agent execution and posts the resulting spans to the store.

## 4. Use Cases

-   **Local Development & Debugging**: Run a complete agent experiment on a single machine using `role="both"`. For easier debugging of the runner logic, one can use `main_process="runner"` (with `n_runners=1`), which runs the runner in the main process and the algorithm/server in a background process.
-   **Distributed Deployment**: Scale out the agent execution by deploying multiple runner instances. One machine is designated to run the `algorithm` role (the server), while multiple other machines run the `runner` role, connecting to the central server.
-   **Task-Specific Workers**: The architecture allows for different types of runners to connect to the same algorithm server, enabling heterogeneous worker pools.

## 5. API Reference

### `agentlightning.execution.client_server.ClientServerExecutionStrategy`

Orchestrates algorithm and runner bundles as separate processes communicating over HTTP.

| Method / Parameter | Type | Description |
| --- | --- | --- |
| **`__init__`** | | | 
| `role` | `Literal["algorithm", "runner", "both"] | None` | Which side(s) to run. Defaults to `AGL_CURRENT_ROLE` env var or `"both"`. |
| `server_host` | `str | None` | Server host to bind to. Defaults to `AGL_SERVER_HOST` or `"localhost"`. |
| `server_port` | `int | None` | Server port. Defaults to `AGL_SERVER_PORT` or `4747`. |
| `n_runners` | `int` | Number of runner processes to spawn. Default is `1`. |
| `graceful_timeout`| `float` | Seconds to wait for cooperative stop before escalating. Default is `10.0`. |
| `terminate_timeout`| `float` | Seconds to wait between `SIGINT`, `terminate()`, and `kill()`. Default is `10.0`. |
| `main_process` | `Literal["algorithm", "runner"]` | Which bundle runs on the main process when `role="both"`. Default is `"algorithm"`. |
| `managed_store` | `bool | None` | If `True` (default), the strategy automatically wraps the store in `LightningStoreClient`/`Server`. |
| `allowed_exit_codes` | `Iterable[int]` | Allowed exit codes for subprocesses. Default is `(0, -15)`. |
| **`execute`** | | Runs the provided bundles. |
| `algorithm` | `AlgorithmBundle` | The callable bundle for the algorithm. |
| `runner` | `RunnerBundle` | The callable bundle for runner workers. |
| `store` | `LightningStore` | The shared `LightningStore` instance. |
| *Returns* | `None` | | 

### `agentlightning.runner.agent.LitAgentRunner`

Executes `LitAgent` tasks, handling tracing, hooks, and store communication.

| Method / Parameter | Type | Description |
| --- | --- | --- |
| **`__init__`** | | |
| `tracer` | `Tracer` | The tracer instance for creating rollout spans. |
| `max_rollouts` | `int | None` | Optional cap on the number of rollouts to process. |
| `poll_interval` | `float` | Seconds to wait between polling the store for tasks. Default is `5.0`. |
| `heartbeat_interval`| `float` | Seconds between heartbeats. Default is `10.0`. |
| `interval_jitter`| `float` | Jitter factor for poll/heartbeat intervals. Default is `0.5`. |
| `heartbeat_launch_mode`| `Literal["asyncio", "thread"]` | Launch mode for the heartbeat loop. Default is `"thread"`. |
| `heartbeat_include_gpu`| `bool` | Whether to include GPU stats in heartbeats. Default is `False`. |
| **`init`** | | Initializes the runner with the agent. |
| `agent` | `LitAgent[T_task]` | The agent instance to be executed. |
| `hooks` | `Sequence[Hook] | None` | Callbacks invoked during the lifecycle. |
| *Returns* | `None` | |
| **`init_worker`** | | Initializes the runner for a specific worker process. |
| `worker_id` | `int` | The unique ID for this worker. |
| `store` | `LightningStore` | The store instance for this worker. |
| *Returns* | `None` | |
| **`teardown`** | | Cleans up all runner resources. |
| *Returns* | `None` | |
| **`teardown_worker`**| | Cleans up worker-specific resources. |
| `worker_id` | `int` | The ID of the worker being torn down. |
| *Returns* | `None` | |
| **`iter`** | | Asynchronously iterates over tasks from the store. |
| `store` | `LightningStore` | The store to poll for tasks. |
| `stop_evt` | `ExecutionEvent` | Event to signal cooperative shutdown. |
| *Returns* | `None` | |
| **`run_once`** | | Processes a single task from the store. |
| `store` | `LightningStore` | The store to poll for a task. |
| *Returns* | `Rollout | None` | The completed rollout, or `None` if no task was found. |
