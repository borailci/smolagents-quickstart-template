
# Technical Analysis of AgentLightning: Algorithm and Training

## 1. Overview

The analyzed modules form the core of the AgentLightning training and optimization framework. They establish a clear separation of concerns between the high-level orchestration (`Trainer`), the strategic logic for improvement (`Algorithm`), and the execution of agent tasks (`Runner`, not included in this analysis). The system is designed to be extensible, allowing developers to implement custom algorithms or use provided ones like Automatic Prompt Optimization (APO) and a simple `Baseline` for testing.

- **`trainer.py`**: The central conductor, responsible for setting up, wiring, and running the entire training process.
- **`algorithm/base.py`**: Defines the abstract `Algorithm` class, establishing the contract for all training strategies.
- **`algorithm/decorator.py`**: Provides a convenient `@algo` decorator to simplify algorithm creation from a single function.
- **`algorithm/fast.py`**: Contains lightweight algorithms (`Baseline`) intended for rapid development and debugging (`dev` mode).
- **`algorithm/apo/apo.py`**: A sophisticated algorithm for Automatic Prompt Optimization, which iteratively refines prompts using LLM-generated critiques.

## 2. File-by-File Analysis

### `agentlightning/trainer/trainer.py`

- **Purpose**: The `Trainer` class is the primary user-facing entry point for running a training or development session. It initializes and coordinates all major components: `Algorithm`, `Runner`, `LightningStore`, `Tracer`, and `ExecutionStrategy`.
- **Key Components**:
  - `Trainer`: The main class that orchestrates the training loop. It uses a flexible component-based initialization system (e.g., `_make_store`, `_make_algorithm`) that can instantiate components from classes, instances, or configuration dictionaries.
  - `fit()`: The main method to start a full training run. It prepares the algorithm and runner "bundles" and hands them off to the configured `ExecutionStrategy`.
  - `dev()`: A convenience method for rapid development and testing. It ensures that a `FastAlgorithm` is used, providing a quicker feedback loop. If no algorithm is specified, it defaults to `Baseline`.
  - `ExecutionStrategy`: The `Trainer` delegates process and communication management (e.g., `ClientServerExecutionStrategy`) to a strategy object, decoupling the training logic from the execution environment.

### `agentlightning/algorithm/base.py`

- **Purpose**: This file defines the fundamental interface for all algorithms in the system.
- **Key Components**:
  - `Algorithm`: An abstract base class that all specific algorithms must inherit from. It defines the core API that the `Trainer` uses to interact with an algorithm.
    - `run()`: The main method where the algorithm's logic is implemented. It receives the training and validation datasets.
    - `set_trainer()`, `set_store()`, `set_adapter()`, `set_llm_proxy()`: Methods used by the `Trainer` to inject necessary dependencies into the algorithm instance. It uses weak references (`weakref.ref`) for components like the `Trainer` to prevent circular dependencies.

### `agentlightning/algorithm/decorator.py`

- **Purpose**: To provide a simpler, functional way to define an algorithm without the boilerplate of creating a new class.
- **Key Components**:
  - `@algo` decorator: A decorator that wraps a function, turning it into a `FunctionalAlgorithm` instance.
  - `FunctionalAlgorithm`: A subclass of `Algorithm` that wraps a user-provided function. It inspects the function's signature to automatically inject dependencies like `store`, `train_dataset`, `llm_proxy`, etc., at runtime. This allows developers to write concise algorithms that only declare the arguments they need.

### `agentlightning/algorithm/fast.py`

- **Purpose**: To provide simple, lightweight algorithms suitable for developer workflows and testing.
- **Key Components**:
  - `FastAlgorithm`: A marker base class that inherits from `Algorithm`. The `Trainer.dev()` method requires algorithms to be instances of `FastAlgorithm` to ensure a responsive development experience.
  - `Baseline`: A concrete implementation of `FastAlgorithm`. Its primary role is to iterate through a dataset, enqueue rollouts for each data point, wait for completion, and log the results. It serves as a useful "smoke test" to verify that the entire platform (store, runners, tracing) is functioning correctly.

### `agentlightning/algorithm/apo/apo.py`

- **Purpose**: Implements Automatic Prompt Optimization (APO), a sophisticated algorithm for iteratively improving prompt templates based on performance.
- **Key Components**:
  - `APO`: A powerful algorithm that uses a beam search strategy to find the optimal prompt. The core loop involves:
    1.  **Evaluation**: Running the current set of candidate prompts against a validation dataset.
    2.  **Critique (Textual Gradient)**: Using an LLM to generate a "textual gradient" or critique based on the performance (rollout results) of a prompt.
    3.  **Edit**: Using another LLM to apply the critique to the prompt, generating a new, potentially improved version.
    4.  **Selection**: Keeping the best-performing prompts for the next round of the beam search.
  - `VersionedPromptTemplate`: A dataclass to track a prompt template, its unique version identifier, and its performance score.
  - `compute_textual_gradient()`: The method responsible for generating the critique from an LLM.
  - `textual_gradient_and_apply_edit()`: The method that orchestrates the critique and edit steps to produce a new prompt candidate.

## 3. Architecture and Data Flow

The general data flow is orchestrated by the `Trainer`:

1.  **Initialization**: A user configures a `Trainer` with an `Algorithm`, a `LitAgent`, datasets, and other components.
2.  **Execution Start**: The user calls `trainer.fit()` or `trainer.dev()`.
3.  **Strategy Execution**: The `Trainer` delegates to an `ExecutionStrategy` (e.g., `ClientServerExecutionStrategy`), which spawns processes/threads for the algorithm and multiple runners.
4.  **Algorithm Run**: The `Algorithm.run()` method is invoked. The algorithm typically iterates over a dataset.
5.  **Enqueue Rollout**: The algorithm uses the `LightningStore` to `enqueue_rollout()` for each task. This places a work item in a queue that runners can pull from.
6.  **Runner Execution**: `Runner` processes poll the store, claim rollouts, execute the `LitAgent` with the given input, and record detailed telemetry (`Spans`) back to the store.
7.  **Algorithm Monitoring**: The algorithm can monitor the status of rollouts via the store to get feedback. For example, `APO` waits for rollout completion to gather performance data for its optimization loop.
8.  **Termination**: The process ends when the algorithm completes, runners reach their `max_rollouts`, or an error occurs.

## 4. Code Deep Dive

### `Trainer` Component Initialization

The `Trainer` uses a robust pattern for component initialization, providing flexibility for the user. The `build_component` utility (defined in `init_utils`) is used to resolve a component from various specifications.

```python
# From agentlightning/trainer/trainer.py

class Trainer(TrainerLegacy):
    def __init__(
        self,
        *,
        # ... other components
        store: ComponentSpec[LightningStore] = None,
        strategy: ComponentSpec[ExecutionStrategy] = None,
        # ...
    ):
        # ...
        self.strategy = self._make_strategy(
            strategy,
            n_runners=self.n_runners,
            port=port,
        )
        self.store = self._make_store(store, self.strategy)
        # ...

    def _make_store(self, store: ComponentSpec[LightningStore], strategy: ExecutionStrategy) -> LightningStore:
        is_client_server = isinstance(strategy, ClientServerExecutionStrategy)
        default_store_factory = lambda: InMemoryLightningStore(thread_safe=is_client_server)
        return build_component(
            store,
            expected_type=LightningStore,
            spec_name="store",
            default_factory=default_store_factory,
            # ...
        )
```
This design allows a user to pass a concrete instance, a class, or a dictionary configuration for the `store`, and the `Trainer` will correctly instantiate it with appropriate defaults (e.g., ensuring the `InMemoryLightningStore` is thread-safe if using a client-server strategy).

### `APO` Textual Gradient Logic

The core innovation of `APO` is generating and applying critiques. This is a multi-LLM-call process.

```python
# From agentlightning/algorithm/apo/apo.py

async def textual_gradient_and_apply_edit(
    self,
    current_prompt: VersionedPromptTemplate,
    rollout: List[RolloutResultForAPO],
    *,
    prefix: Optional[str] = None,
) -> Optional[str]:
    # 1) Critique
    critique_text = await self.compute_textual_gradient(
        current_prompt,
        rollout,
        prefix=prefix,
    )
    if not critique_text:
        # ... handle error
        return current_prompt.prompt_template.template

    # 2) Apply edit
    ae_template = random.choice(APPLY_EDIT_PROMPT_FILES)
    ae_msg = poml.poml(
        ae_template,
        context={
            "prompt_template": current_prompt.prompt_template.template,
            "critique": critique_text,
        },
        format="openai_chat",
    )

    ae_response = await self.async_openai_client.chat.completions.create(
        model=self.apply_edit_model,
        messages=ae_msg["messages"],
        temperature=self.diversity_temperature,
    )
    new_prompt = ae_response.choices[0].message.content
    return new_prompt
```
This snippet clearly shows the two-step "gradient" and "apply" process. It relies on pre-defined `poml` templates to structure the LLM calls for generating the critique and then applying it to revise the prompt.

## 5. API Reference

| Class / Decorator | Method / Function | Signature |
|---|---|---|
| `Trainer` | `fit` | `(self, agent: LitAgent[T_co], train_dataset: Optional[Dataset[T_co]] = None, *, val_dataset: Optional[Dataset[T_co]] = None) -> None` |
| `Trainer` | `dev` | `(self, agent: LitAgent[T_co], train_dataset: Optional[Dataset[T_co]] = None, *, val_dataset: Optional[Dataset[T_co]] = None) -> None` |
| `Algorithm` | `run` | `(self, train_dataset: Optional[Dataset[Any]] = None, val_dataset: Optional[Dataset[Any]] = None) -> Union[None, Awaitable[None]]` |
| `@algo` | - | `algo(func: AlgorithmFunc) -> FunctionalAlgorithm` |
| `Baseline` | `__init__` | `(self, *, n_epochs: int = 1, polling_interval: float = 5.0, max_queue_length: int = 4, ...)` |
| `APO` | `__init__` | `(self, async_openai_client: AsyncOpenAI, *, gradient_model: str = "gpt-5-mini", apply_edit_model: str = "gpt-4.1-mini", beam_width: int = 4, beam_rounds: int = 3, ...)` |
| `APO` | `run` | `(self, train_dataset: Optional[Dataset[T_task]] = None, val_dataset: Dataset[T_task]) -> None` |

