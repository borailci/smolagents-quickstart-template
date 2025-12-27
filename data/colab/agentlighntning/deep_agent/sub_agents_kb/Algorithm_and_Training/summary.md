'''
# Deep Technical Analysis: Algorithm and Training

## 1. Overview

The Algorithm and Training components form the core of the `agentlightning` framework, providing the mechanisms for training and optimizing agents. This system is designed around a flexible architecture where different optimization `Algorithm`s can be orchestrated by a `Trainer`. The `Trainer` manages the entire lifecycle, including data handling, agent execution via `Runner`s, and persistence through a `LightningStore`.

- **`Trainer`**: The central orchestrator that wires all components together. It manages the execution strategy (e.g., client-server), spawns agent runners, and drives the `Algorithm`.
- **`Algorithm`**: The "brain" of the training process. Subclasses implement specific optimization strategies. The key implementations analyzed are `APO` (a sophisticated prompt optimization algorithm) and `Baseline` (a simple data-flow-through algorithm for testing).
- **`LitAgent`**: The base class for user-defined agents. It defines the `rollout` methods where the agent's logic for processing a task is implemented.
- **`LightningStore`**: A key-value store abstraction for communication and state management between the `Trainer`, `Algorithm`, and `Runners`, handling rollouts, spans, and resources.

## 2. File-by-File Analysis

### `agentlightning/trainer/trainer.py`
- **Purpose**: This file contains the `Trainer` class, the primary entry point for users to configure and run a training job. It handles the setup of all components, including the algorithm, runners, store, and execution strategy.
- **Key Components**:
  - `Trainer`: A high-level class that orchestrates the entire training process. It initializes and connects the `Algorithm`, `Runner`, `LightningStore`, and `ExecutionStrategy`. Its main methods are `fit()` for running a full training process and `dev()` for quick, synchronous test runs.
  - **Component Initialization**: The `Trainer` uses a flexible `build_component` system (`_make_...` methods) that can instantiate components from classes, instances, dictionaries, or registry strings, providing significant configuration flexibility.

### `agentlightning/algorithm/apo/apo.py`
- **Purpose**: Implements the Automatic Prompt Optimization (`APO`) algorithm. This is an advanced, iterative algorithm designed to refine a prompt template by generating and evaluating variations based on performance.
- **Key Components**:
  - `APO(Algorithm)`: This class uses a beam search strategy to explore the space of possible prompts. In each round, it generates "textual gradients" (critiques) using an LLM, applies them as edits to create new candidate prompts, evaluates them on a validation set, and updates its beam with the best-performing prompts.
  - **Core Logic**: The process involves evaluating prompts on rollouts, sampling results to generate critiques (`compute_textual_gradient`), using another LLM call to apply the critique (`textual_gradient_and_apply_edit`), and managing the beam of candidate prompts across multiple rounds (`run`).

### `agentlightning/algorithm/fast.py`
- **Purpose**: Provides lightweight algorithms suitable for development, debugging, and establishing a baseline.
- **Key Components**:
  - `FastAlgorithm(Algorithm)`: A base class for algorithms optimized for quick developer feedback rather than full-scale training.
  - `Baseline(FastAlgorithm)`: A reference implementation that enqueues all tasks from a dataset, waits for them to be processed by runners, and logs the results. It serves as a simple "smoke test" to ensure the entire system (Trainer, Runner, Store) is connected and working correctly.

### `agentlightning/litagent/litagent.py`
- **Purpose**: Defines the `LitAgent` base class, which is the interface for users to implement their agent's core logic.
- **Key Components**:
  - `LitAgent`: An abstract base class that users subclass to create their own agents. The core of a `LitAgent` is the `rollout` method (and its async/training/validation variants), where the agent receives a task and performs its work. The `Trainer` and `Runner` infrastructure handles the execution and tracing of these methods.
  - **Rollout Methods**: Provides several `rollout` methods (`rollout`, `rollout_async`, `training_rollout`, `validation_rollout`) that allow developers to implement synchronous or asynchronous logic and to differentiate between training and validation behavior.

## 3. Integration & Data Flow

The `Trainer` acts as the central hub:
1.  **Initialization**: A user configures a `Trainer` with an `Algorithm` (e.g., `APO`), a `LitAgent` subclass, and datasets.
2.  **Execution Start**: The user calls `trainer.fit(agent, train_dataset, val_dataset)`.
3.  **Strategy Execution**: The `Trainer` delegates to an `ExecutionStrategy` (e.g., `ClientServerExecutionStrategy`) which spawns a process/thread for the `Algorithm` and multiple `Runner` processes.
4.  **Algorithm Run**: Inside its process, the `Algorithm.run()` method is called. It interacts with the `LightningStore` to enqueue rollouts (tasks) for the runners to pick up. For `APO`, it also adds `PromptTemplate` resources to the store.
5.  **Runner Execution**: Each `Runner` process loops, claiming queued rollouts from the `LightningStore`. For each rollout, it instantiates the user-provided `LitAgent` and calls the appropriate `rollout` method, passing the task input and any resources (like the prompt from `APO`).
6.  **Agent Logic & Tracing**: The `LitAgent`'s `rollout` method executes. Any interactions (e.g., LLM calls) are captured by a `Tracer` and sent back to the `LightningStore` as spans.
7.  **Algorithm Feedback**: The `Algorithm` waits for rollouts to complete by querying the `LightningStore`. It retrieves the resulting spans and rewards, adapts them, and uses this feedback to inform its next step (e.g., `APO` uses the results to generate a new prompt).
8.  **Iteration**: This loop continues until the algorithm's criteria are met (e.g., `beam_rounds` completed or dataset exhausted).

## 4. API Reference

### `agentlightning.trainer.trainer.Trainer`

| Method / Property | Signature / Type | Description |
|---|---|---|
| `__init__` | `(*, dev: bool, n_runners: int, max_rollouts: int, initial_resources: NamedResources, tracer: ..., adapter: ..., store: ..., runner: ..., strategy: ..., port: int, algorithm: ..., llm_proxy: ...)` | Configures the trainer with all necessary components. Most can be provided as instances, classes, or config dicts. |
| `fit` | `(self, agent: LitAgent[T_co], train_dataset: Dataset[T_co] = None, *, val_dataset: Dataset[T_co] = None) -> None` | Executes the full, potentially distributed, training loop using the configured algorithm and runners. |
| `dev` | `(self, agent: LitAgent[T_co], train_dataset: Dataset[T_co] = None, *, val_dataset: Dataset[T_co] = None) -> None` | Runs a fast, synchronous loop for debugging, typically with a `FastAlgorithm` like `Baseline`. |
| `algorithm` | `Optional[Algorithm]` | The algorithm instance used for training. |
| `store` | `LightningStore` | The store instance for state management. |
| `runner` | `Runner[Any]` | The runner instance that executes the agent. |
| `strategy` | `ExecutionStrategy` | The strategy for managing processes (e.g., client-server). |

### `agentlightning.algorithm.apo.apo.APO`

| Method / Property | Signature / Type | Description |
|---|---|---|
| `__init__` | `(self, async_openai_client: AsyncOpenAI, *, gradient_model: str, apply_edit_model: str, diversity_temperature: float, gradient_batch_size: int, val_batch_size: int, beam_width: int, branch_factor: int, beam_rounds: int, ...)` | Initializes the APO algorithm with its hyperparameters. |
| `run` | `(self, store: LightningStore, llm_proxy: LLMProxy, train_dataset: Dataset[T_task], val_dataset: Dataset[T_task]) -> None` | Main entry point to start the beam search optimization process. |
| `get_best_prompt` | `(self) -> PromptTemplate` | Returns the best prompt template discovered during the optimization run. |

### `agentlightning.algorithm.fast.Baseline`

| Method / Property | Signature / Type | Description |
|---|---|---|
| `__init__` | `(self, *, n_epochs: int, train_split: float, polling_interval: float, max_queue_length: int, span_verbosity: Literal["keys", "key_values", "none"])` | Initializes the baseline algorithm with configuration for data processing and logging. |
| `run` | `(self, store: LightningStore, llm_proxy: LLMProxy, train_dataset: Dataset[Any], val_dataset: Dataset[Any]) -> None` | Executes a simple loop that enqueues all tasks from the datasets and waits for them to complete, logging all results. |

### `agentlightning.litagent.litagent.LitAgent`

| Method / Property | Signature / Type | Description |
|---|---|---|
| `rollout` | `(self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | **[To be implemented by user]** Synchronous logic for processing a single task. Called for both training and validation if other methods are not overridden. |
| `rollout_async` | `async (self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | **[To be implemented by user]** Asynchronous version of `rollout`. |
| `training_rollout` | `(self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | Logic for a training-specific task. Defaults to `rollout`. |
| `validation_rollout` | `(self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | Logic for a validation-specific task. Defaults to `rollout`. |
| `trainer` | `Trainer` | Property to access the `Trainer` instance managing this agent. |
| `runner` | `Runner[T]` | Property to access the `Runner` instance executing this agent. |
| `tracer` | `Tracer` | Property to access the configured `Tracer`. |
'''