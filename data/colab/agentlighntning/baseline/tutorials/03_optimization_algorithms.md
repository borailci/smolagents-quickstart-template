# Using Optimization Algorithms in AgentLightning

This tutorial demonstrates how to use the optimization algorithms available in AgentLightning, specifically focusing on Automatic Prompt Optimization (APO) and VERL for reinforcement learning.

## 1. Goal

The goal of this tutorial is to learn how to apply advanced optimization algorithms to improve the performance of AI agents. We will cover two main scenarios:

-   **Automatic Prompt Optimization (APO)**: How to automatically refine prompt templates to improve agent responses.
-   **Reinforcement Learning with VERL**: How to train an agent using Proximal Policy Optimization (PPO) for more complex tasks.

## 2. Prerequisites

-   `agentlightning` package installed.
-   An environment with the necessary dependencies for the chosen algorithm. For example, `poml` for APO and `verl` for VERL.

## 3. Architecture

Below is a diagram illustrating the workflow for both APO and VERL within the AgentLightning framework.

```mermaid
graph TD
    subgraph APO Workflow
        A[Start with a Seed Prompt] --> B{Evaluate Prompt on Validation Set};
        B --> C{Generate Textual Gradient (Critique)};
        C --> D{Apply Edit to Create New Prompt};
        D --> E{Add to Beam of Candidate Prompts};
        E --> F{Select Best Prompt from Beam};
        F --> B;
    end

    subgraph VERL Workflow
        G[Start with a Pre-trained Model] --> H{Rollout with Current Policy};
        H --> I{Collect Trajectories (state, action, reward)};
        I --> J{Compute Advantages};
        J --> K{Update Policy with PPO};
        K --> H;
    end

    A --> F;
    G --> K;
```

## 4. Implementation

### Using Automatic Prompt Optimization (APO)

APO is a powerful algorithm for optimizing prompt templates. It works by iteratively generating critiques (textual gradients) of a prompt based on its performance on a dataset and then using those critiques to refine the prompt.

Here's how you can use the `APO` algorithm in your training pipeline:

```python
from openai import AsyncOpenAI
from agentlightning.algorithm.apo import APO
from agentlightning.types import PromptTemplate, Dataset

# 1. Initialize the APO algorithm
# You need an AsyncOpenAI client for the LLM calls
async_openai_client = AsyncOpenAI(
    # your credentials here
)

apo_algorithm = APO(
    async_openai_client=async_openai_client,
    gradient_model="gpt-4",
    apply_edit_model="gpt-4",
    beam_width=2,
    branch_factor=2,
    beam_rounds=3,
)

# 2. Define your initial prompt and datasets
seed_prompt = PromptTemplate(template="Your initial prompt here: {input}", engine="f-string")
train_dataset: Dataset = [{"input": "example 1"}, {"input": "example 2"}]
val_dataset: Dataset = [{"input": "val example 1"}, {"input": "val example 2"}]

# 3. In a real scenario, you would use a Trainer to run the algorithm
# This is a conceptual example of how to execute the run method

# trainer.fit(apo_algorithm, train_dataset=train_dataset, val_dataset=val_dataset)

# The best prompt can be retrieved after the run
# best_prompt = apo_algorithm.get_best_prompt()
```

### Using Reinforcement Learning with VERL

VERL integrates a powerful PPO-based reinforcement learning pipeline into AgentLightning. This is suitable for tasks where the agent needs to learn a policy through trial and error.

Here's a conceptual example of how to configure and use the `VERL` algorithm. VERL is highly configurable and can be adapted to various scenarios.

```python
from agentlightning.algorithm.verl import VERL
from agentlightning.types import Dataset

# 1. Configure the VERL algorithm
# The configuration is a dictionary that mirrors the VERL CLI overrides.
verl_config = {
    "algorithm": {
        "adv_estimator": "grpo",
    },
    "data": {
        "train_batch_size": 32,
        "max_prompt_length": 4096,
        "max_response_length": 2048,
    },
    "actor_rollout_ref": {
        "model": {
            "path": "Qwen/Qwen2.5-1.5B-Instruct",
        },
    },
    "trainer": {
        "n_gpus_per_node": 1,
        "total_epochs": 2,
    },
}

verl_algorithm = VERL(config=verl_config)

# 2. Define your training and validation datasets
train_dataset: Dataset = [{"input": "training task 1"}, {"input": "training task 2"}]
val_dataset: Dataset = [{"input": "validation task 1"}, {"input": "validation task 2"}]

# 3. Use a Trainer to run the algorithm
# This is a conceptual example

# trainer.fit(verl_algorithm, train_dataset=train_dataset, val_dataset=val_dataset)
```

## 5. Conclusion

This tutorial provided an overview of how to use the `APO` and `VERL` optimization algorithms in AgentLightning. `APO` is ideal for prompt engineering, while `VERL` provides a robust solution for reinforcement learning-based training. By understanding and applying these algorithms, you can significantly enhance the capabilities of your AI agents.