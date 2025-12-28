'''
# Agent Algorithm and Training Analysis

## 1. Overview

The Agent Algorithm and Training modules form the core of the `agentlightning` library, providing a structured framework for training and optimizing AI agents. The system is designed around four key components:

- **`LitAgent`**: The user-defined agent logic, responsible for executing a "rollout" for a given task.
- **`Algorithm`**: The optimization strategy that guides the agent's learning process. This includes algorithms like Automatic Prompt Optimization (`APO`).
- **`Trainer`**: The orchestrator that manages the training loop, connecting the `Algorithm`, `LitAgent`, and data.
- **`LightningStore`**: A storage backend for persisting training artifacts like rollouts, traces, and resources.

The typical workflow involves a `Trainer` using an `Algorithm` to iteratively improve an agent's performance. The `Algorithm` enqueues rollouts (tasks) into the `LightningStore`. `Runners` (managed by the `Trainer`) pick up these rollouts and execute them using the `LitAgent`, and the results (traces and rewards) are written back to the store. The `Algorithm` then analyzes these results to update its strategy, for example, by generating a better prompt.

## 2. File-by-File Analysis

### `agentlightning/litagent/litagent.py`

- **Purpose**: Defines the `LitAgent` base class, which is the primary interface for users to implement their agent's logic. It abstracts the execution of a single task into a `rollout` method.
- **Key Components**:
  - `LitAgent`: A generic base class that users must subclass. It provides a structured way to define the agent's behavior for training and validation rollouts, in both synchronous and asynchronous contexts.
  - `rollout()`: The core method to be implemented by the user. It takes a task and a set of resources (like prompt templates) and executes the agent's logic, returning a result (e.g., reward or spans).
  - `training_rollout()` / `validation_rollout()`: Specific methods for training and validation, which default to calling the main `rollout()` method. This allows for different logic during training and validation if needed.

### `agentlightning/algorithm/base.py`

- **Purpose**: Provides the abstract `Algorithm` base class. All training strategies, such as `APO` or a simple `Baseline`, must inherit from this class.
- **Key Components**:
  - `Algorithm`: An abstract class that defines the contract for all training algorithms. It includes methods for setting and getting the `Trainer`, `LLMProxy`, `LightningStore`, and `TraceAdapter`.
  - `run()`: The main entry point for the algorithm's logic. The `Trainer` calls this method to start the training process. The algorithm implementation within `run()` is responsible for interacting with the `LightningStore` to enqueue rollouts and analyze results.

### `agentlightning/algorithm/apo/apo.py`

- **Purpose**: Implements the Automatic Prompt Optimization (`APO`) algorithm. This is a sophisticated algorithm for iteratively improving a prompt template based on agent performance.
- **Key Components**:
  - `APO`: A concrete implementation of the `Algorithm` class. It uses a beam search strategy to find the optimal prompt.
  - **Textual Gradients**: The core idea of `APO`. It uses an LLM to generate "critiques" (textual gradients) of a prompt based on the agent's performance on a set of rollouts.
  - **Apply Edit**: After generating a critique, another LLM is used to "apply the edit" to the prompt, creating a new candidate prompt.
  - **Beam Search**: `APO` maintains a "beam" of the best-performing prompts. In each round, it generates new candidate prompts from the current beam, evaluates them on a validation set, and selects the best ones for the next round.

### `agentlightning/trainer/trainer.py`

- **Purpose**: The `Trainer` is the main orchestrator of the training process. It wires together the `Algorithm`, the `LitAgent`, the `LightningStore`, and the data.
- **Key Components**:
  - `Trainer`: A high-level class that manages the entire training lifecycle. It is responsible for initializing all components (runners, store, algorithm, etc.).
  - `fit()`: The primary method to start a full training run. It takes an `agent` and datasets, and then uses the configured `ExecutionStrategy` to run the `Algorithm` and `Runners`.
  - `dev()`: A convenience method for running a fast, synchronous dry-run, useful for debugging.
  - **Component Injection**: The `Trainer` is responsible for instantiating and injecting dependencies. For example, it ensures the `Algorithm` and `Runners` have access to the same `LightningStore` instance.

## 3. Architecture & Data Flow

1.  A user instantiates a `Trainer` with an `Algorithm` (e.g., `APO`), a `LitAgent`, and datasets.
2.  The user calls `trainer.fit(agent, train_dataset, val_dataset)`.
3.  The `Trainer` initializes the `ExecutionStrategy` (e.g., `ClientServerExecutionStrategy`), which starts the `Algorithm` and one or more `Runners` in separate processes/threads.
4.  The `Algorithm` (e.g., `APO`) starts its `run` method. It takes the initial prompt and enqueues rollouts on the `LightningStore` for the validation dataset.
5.  The `Runners` are in a loop, polling the `LightningStore` for new rollouts.
6.  A `Runner` receives a rollout, which contains the task and the ID of the resources to use (e.g., the prompt version).
7.  The `Runner` executes the `LitAgent.rollout()` method with the task and resources.
8.  The `LitAgent` performs the task, and its interactions are captured by a `Tracer`.
9.  The `Runner` reports the results (spans, reward) back to the `LightningStore`.
10. The `Algorithm` waits for the rollouts to complete, then fetches the results from the `LightningStore`.
11. The `APO` algorithm analyzes the results, computes textual gradients, generates new prompts, and starts a new round of the beam search.
12. This loop continues for a configured number of rounds.

## 4. Integration Points

- **`Trainer` -> `Algorithm`**: The `Trainer` instantiates and runs the `Algorithm`, injecting the `LightningStore`, `TraceAdapter`, and `LLMProxy`.
- **`Trainer` -> `Runner`**: The `Trainer` spawns `Runner` instances, which are responsible for executing the agent logic.
- **`Runner` -> `LitAgent`**: The `Runner` instantiates the user-provided `LitAgent` and calls its `rollout` methods.
- **`Algorithm` <-> `LightningStore`**: The `Algorithm` uses the `LightningStore` to enqueue rollouts and read their results.
- **`Runner` <-> `LightningStore`**: `Runners` use the `LightningStore` to claim rollouts and write back the results.

## 5. API Reference

### `agentlightning.litagent.LitAgent`

| Method                  | Signature                                                              | Description                                                                                                                                 |
| ----------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `rollout`               | `(self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | Synchronously executes a rollout for a given task. Must be implemented by subclasses.                                                      |
| `rollout_async`         | `async (self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | Asynchronously executes a rollout.                                                                                                         |
| `training_rollout`      | `(self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | Executes a training rollout. Defaults to `rollout()`.                                                                                       |
| `validation_rollout`    | `(self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | Executes a validation rollout. Defaults to `rollout()`.                                                                                     |
| `training_rollout_async`| `async (self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | Asynchronously executes a training rollout. Defaults to `rollout_async()`.                                                                   |
| `validation_rollout_async`| `async (self, task: T, resources: NamedResources, rollout: Rollout) -> RolloutRawResult` | Asynchronously executes a validation rollout. Defaults to `rollout_async()`.                                                               |

### `agentlightning.algorithm.base.Algorithm`

| Method | Signature | Description |
| --- | --- | --- |
| `run` | `(self, train_dataset: Optional[Dataset[Any]] = None, val_dataset: Optional[Dataset[Any]] = None) -> Union[None, Awaitable[None]]` | Abstract method that must be implemented by subclasses to define the algorithm's logic. |

### `agentlightning.algorithm.apo.APO`

| Method | Signature | Description |
| --- | --- | --- |
| `run` | `async (self, store: LightningStore, llm_proxy: Optional[LLMProxy], train_dataset: Optional[Dataset[T_task]] = None, val_dataset: Optional[Dataset[T_task]] = None) -> None` | Executes the APO algorithm, performing beam search with textual gradients to optimize a prompt. |
| `get_best_prompt` | `(self) -> PromptTemplate` | Returns the best prompt template found during the optimization process. |

### `agentlightning.trainer.trainer.Trainer`

| Method | Signature | Description |
| --- | --- | --- |
| `fit` | `(self, agent: LitAgent[T_co], train_dataset: Optional[Dataset[T_co]] = None, *, val_dataset: Optional[Dataset[T_co]] = None) -> None` | Executes the full training loop using the configured algorithm and runners. |
| `dev` | `(self, agent: LitAgent[T_co], train_dataset: Optional[Dataset[T_co]] = None, *, val_dataset: Optional[Dataset[T_co]] = None) -> None` | Executes a fast, synchronous dry-run for debugging purposes. | 
'''