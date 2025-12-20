
# How to Write Your First Algorithm

In `agent-lightning`, an `Algorithm` is the core component that orchestrates the agent's learning process. It defines the strategy for training and improving the agent over time. In this tutorial, you will learn how to create a custom algorithm from scratch.

## 1. Goal

By the end of this tutorial, you will have a clear understanding of the `Algorithm` class and be able to implement your own simple algorithm.

## 2. Prerequisites

- A basic understanding of Python.
- Familiarity with the concepts of agent-based systems is helpful but not required.

## 3. The `Algorithm` Base Class

The foundation of any custom algorithm is the `Algorithm` base class, located in `agentlightning.algorithm.base`. This class provides the essential structure and methods that your algorithm will use to interact with the rest of the `agent-lightning` framework.

Here's a simplified view of the `Algorithm` class:

```python
# agentlightning/algorithm/base.py

class Algorithm:
    """Algorithm is the strategy, or tuner to train the agent."""

    def run(
        self,
        train_dataset: Optional[Dataset[Any]] = None,
        val_dataset: Optional[Dataset[Any]] = None,
    ) -> Union[None, Awaitable[None]]:
        """Subclasses should implement this method to implement the algorithm."""
        raise NotImplementedError("Subclasses must implement run().")

    # ... other helper methods
```

The most important method to implement is `run()`. This is the entry point for your algorithm's logic.

## 4. Step 1: Creating Your Custom Algorithm

Let's create a new file named `my_simple_algorithm.py` and define our custom algorithm. It will inherit from `agentlightning.algorithm.Algorithm`.

```python
# my_simple_algorithm.py

from typing import Any, Optional
from agentlightning.algorithm import Algorithm
from agentlightning.types import Dataset

class SimpleAlgorithm(Algorithm):
    """A simple algorithm that prints a message."""

    def run(
        self,
        train_dataset: Optional[Dataset[Any]] = None,
        val_dataset: Optional[Dataset[Any]] = None,
    ) -> None:
        """The main logic of the algorithm."""
        print("Running the simple algorithm!")
        if train_dataset:
            print(f"Training on a dataset of length: {len(train_dataset)}")
        if val_dataset:
            print(f"Validating on a dataset of length: {len(val_dataset)}")

        # In a real algorithm, you would implement your training loop here.
        # For example, you might interact with the trainer to run agents,
        # collect feedback, and update the agent's parameters.
```

In this example, our `SimpleAlgorithm` overrides the `run` method to print some information about the datasets it receives. This is the starting point for any more complex training logic.

## 5. Step 2: Integrating with the Trainer

Now that we have our custom algorithm, we can use it with the `Trainer` to execute it.

```python
# main.py

from agentlightning import Trainer
from my_simple_algorithm import SimpleAlgorithm

# 1. Instantiate your algorithm
algorithm = SimpleAlgorithm()

# 2. (Optional) Create some dummy data
train_data = [1, 2, 3, 4, 5]
val_data = [6, 7, 8]

# 3. Instantiate the Trainer with your algorithm
trainer = Trainer(algorithm=algorithm)

# 4. Run the training process
if __name__ == "__main__":
    trainer.fit(train_dataset=train_data, val_dataset=val_data)
```

When you run `main.py`, you will see the output from your `SimpleAlgorithm`:

```
Running the simple algorithm!
Training on a dataset of length: 5
Validating on a dataset of length: 3
```

## 6. Conclusion

Congratulations! You have successfully created and run your first custom algorithm in `agent-lightning`. This is the fundamental skill you need to develop more sophisticated training strategies for your agents.

From here, you can explore:
- Using the `get_trainer()` method within your algorithm to interact with the training environment.
- Implementing more complex logic in the `run` method, such as reinforcement learning loops or fine-tuning strategies.
- Exploring the other algorithm examples provided in the `agentlightning/algorithm` directory to see more advanced implementations.
