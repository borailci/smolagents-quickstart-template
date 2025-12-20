
# Core Agent Logic and Runner Analysis

## 1. Overview

This set of files forms the core execution engine of the Agent Lightning framework. The central concept is the separation of agent logic from the execution environment. A `LitAgent` encapsulates the business logic for performing a task, while a `Runner` is responsible for orchestrating the execution of that agent. This includes fetching tasks and resources from a persistent `LightningStore`, managing the lifecycle of the agent, handling tracing, and reporting results.

The system is designed for both synchronous and asynchronous operations and supports distributed execution through a worker model. Convenience decorators are provided to simplify the creation of agents from simple functions, lowering the barrier to entry for developers.

## 2. File-by-File Analysis

### `agentlightning/litagent/litagent.py`

- **Purpose**: Defines the fundamental `LitAgent` base class, which serves as the abstract interface for all agents in the framework.
- **Key Components**:
  - `LitAgent[T]`: A generic abstract base class. Subclasses must implement the `rollout` method (or its async/specialized variants) to define the agent's behavior. It provides a structured way to handle different execution stages like training and validation.
  - `rollout()`: The core method where the agent processes a `Task` using a given set of `NamedResources`.
  - `training_rollout()`, `validation_rollout()`: Specialized methods that default to calling `rollout()`, but can be overridden for stage-specific logic.
  - `is_async()`: A method to detect if the agent has implemented asynchronous rollout methods.
  - `set_trainer()`, `set_runner()`: Methods to link the agent to the broader `Trainer` and `Runner` infrastructure, allowing it to access system-level components like the `Tracer`.

### `agentlightning/litagent/decorator.py`

- **Purpose**: Provides high-level decorators to quickly create `LitAgent` instances from simple Python functions, abstracting away the boilerplate of subclassing `LitAgent`.
- **Key Components**:
  - `FunctionalLitAgent`: A wrapper class that adapts a standard Python function into a `LitAgent`. It inspects the function's signature to dynamically inject required resources like `llm` or `prompt_template`.
  - `@llm_rollout`: A decorator for functions that perform rollouts using an `LLM` resource.
  - `@prompt_rollout`: A decorator for functions that use a `PromptTemplate` resource, common in prompt optimization scenarios.
  - `@rollout`: A general-purpose decorator that automatically determines whether to act as an `@llm_rollout` or `@prompt_rollout` based on the wrapped function's signature.

### `agentlightning/runner/base.py`

- **Purpose**: Defines the abstract `Runner` base class, which specifies the contract for any process that executes `LitAgent` tasks.
- **Key Components**:
  - `Runner[T_task]`: An abstract generic class inheriting from `ParallelWorkerBase`, indicating its role in a distributed system. It defines the lifecycle (`init`, `init_worker`, `teardown`, `teardown_worker`) and execution methods (`iter`, `step`) that concrete runners must implement.
  - `run_context()`: A context manager for setting up and tearing down a runner in simple, standalone scenarios (e.g., for debugging).

### `agentlightning/runner/agent.py`

- **Purpose**: Contains `LitAgentRunner`, the primary, concrete implementation of the `Runner` interface. It orchestrates the entire lifecycle of a task execution.
- **Key Components**:
  - `LitAgentRunner`: Manages the end-to-end process of running an agent. Its key responsibilities include:
    - Polling a `LightningStore` for available tasks (`dequeue_rollout`).
    - Emitting heartbeats to the store to signal worker health (`_emit_heartbeat`).
    - Fetching required `Resources` for a task.
    - Setting up a `Tracer` context for observability.
    - Invoking the appropriate `rollout` method on the `LitAgent` (sync or async).
    - Post-processing the agent's return value (e.g., handling rewards or explicit spans).
    - Updating the task's status in the store (`succeeded` or `failed`).

### `agentlightning/client.py`

- **Purpose**: Provides legacy client utilities for interacting with older, HTTP-based Agent Lightning servers. This module is marked as deprecated.
- **Key Components**:
  - `AgentLightningClient`: A client that communicates with a remote server via HTTP to poll for tasks, fetch resources, and submit completed rollouts. It exists for backward compatibility.
  - `DevTaskLoader`: A local, in-memory mock of the client-server interaction, used for development and testing without needing a live server. It serves a predefined list of tasks and resources.

## 3. Architecture & Data Flow

The core workflow is orchestrated by the `LitAgentRunner` and revolves around a shared `LightningStore`.

1.  **Task Polling**: The `LitAgentRunner` continuously polls the `LightningStore` by calling `dequeue_rollout` to claim an available task.
2.  **Resource Fetching**: Once a task (`AttemptedRollout`) is acquired, the runner fetches the associated `NamedResources` from the store.
3.  **Agent Invocation**: The runner invokes the `rollout` method (or its async/training/validation variant) on the configured `LitAgent`, passing the task input and resources.
4.  **Execution & Tracing**: The agent executes its logic. All operations can be traced via the `Tracer` managed by the runner.
5.  **Result Processing**: The agent returns a result, which can be a reward (`float`), a list of spans, or `None`. The runner processes this result, standardizing it and ensuring any final rewards or spans are persisted.
6.  **Status Update**: The runner updates the status of the attempt in the `LightningStore` to "succeeded" or "failed".

## 4. Code Deep Dive

### Critical Snippet: `LitAgentRunner._step_impl`

This method in `agentlightning/runner/agent.py` is the heart of the execution loop. It encapsulates the logic for running a single task from start to finish.

```python
async def _step_impl(self, next_rollout: AttemptedRollout, raise_on_exception: bool = False) -> str:
    store = self.get_store()
    agent = self.get_agent()

    # ... Fetch resources ...

    try:
        # ... Trigger on_rollout_start hooks ...

        async with self._tracer.trace_context(
            name=rollout_id, rollout_id=rollout_id, attempt_id=next_rollout.attempt.attempt_id
        ):
            # ... Trigger on_trace_start hooks ...

            if agent.is_async():
                rollout_method = (
                    agent.training_rollout_async if next_rollout.mode == "train" else agent.validation_rollout_async
                )
                result = await rollout_method(
                    next_rollout.input, resources=resources_update.resources, rollout=next_rollout
                )
            else:
                rollout_method = (
                    agent.training_rollout if next_rollout.mode == "train" else agent.validation_rollout
                )
                result = rollout_method(
                    next_rollout.input, resources=resources_update.resources, rollout=next_rollout
                )

            # ... Trigger on_trace_end hooks ...

        trace_spans = await self._post_process_rollout_result(next_rollout, result)
        # ... Logging and finalization ...

    except Exception:
        # ... Exception handling ...
    finally:
        # ... Trigger on_rollout_end hooks and update attempt status in store ...

    return rollout_id
```

This snippet clearly shows the sequence of operations: resource fetching, trace context setup, dynamic dispatch to the correct sync/async agent method, result post-processing, and finalization with status updates.

## 5. Integration Points

- **Dependencies**: The core logic is heavily dependent on the `LightningStore` abstraction for persistence and coordination. It also relies on a `Tracer` for observability.
- **Public Interface / Entry Points**:
  - For creating agents: The main entry points are the decorators in `agentlightning.litagent.decorator` (`@rollout`, `@llm_rollout`).
  - For execution: The primary entry point for running agents is the `LitAgentRunner`, which is typically managed by a higher-level `Trainer` object (not shown in these files). For direct execution, `runner.iter()` (long-running) and `runner.step()` (single task) are used.

## 6. API Reference

| Class / Function | Signature | Purpose |
| --- | --- | --- |
| `LitAgent` | `class LitAgent(Generic[T])` | Abstract base class for all agents. |
| `LitAgent.rollout` | `rollout(self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | Executes a synchronous rollout. Must be implemented by subclasses. |
| `LitAgent.rollout_async` | `async rollout_async(self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | Executes an asynchronous rollout. |
| `@rollout` | `@rollout(func)` | Decorator to convert a function into a `FunctionalLitAgent`. |
| `Runner` | `class Runner(ParallelWorkerBase, Generic[T_task])` | Abstract base class for agent executors. |
| `LitAgentRunner` | `class LitAgentRunner(Runner[T_task])` | Concrete implementation for running `LitAgent` tasks. |
| `LitAgentRunner.iter` | `async iter(self, *, event: Optional[ExecutionEvent] = None) -> None` | Runs the runner continuously, polling the store for tasks. |
| `LitAgentRunner.step` | `async step(self, input: T_task, *, ...) -> Rollout` | Executes a single task directly. |

