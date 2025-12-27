# Automatic Prompt Optimization (APO)

## 1. Goal

This tutorial demonstrates how to use the Automatic Prompt Optimization (APO) algorithm in `agentlightning` to automatically find the best prompt for your agent. Prompt engineering can be a tedious and time-consuming process. APO automates this by systematically exploring different prompt variations and selecting the one that performs best on a given task.

## 2. Prerequisites

To run the code in this tutorial, you need to install `agentlightning` with the `apo` extras:

```bash
pip install "agentlightning[apo]"
```

You also need to have an OpenAI API key and set it as an environment variable:

```bash
export OPENAI_API_KEY="your-api-key"
```

## 3. Architecture

The APO algorithm works by iteratively refining a prompt template. It uses a beam search strategy to explore the space of possible prompts. In each round, it generates "textual gradients" (critiques) using an LLM, applies them as edits to create new candidate prompts, evaluates them on a validation set, and updates its beam with the best-performing prompts.

```mermaid
graph TD
    A["Start with Seed Prompt"] --> B{Evaluate on Validation Set};
    B --> C{Generate Textual Gradients (Critiques)};
    C --> D{Apply Edits to Create New Prompts};
    D --> E{Evaluate New Prompts};
    E --> F{Select Best Prompts for Next Round};
    F --> C;
    F --> G["End: Best Prompt"];
```

## 4. Implementation

Here's a complete, runnable example that shows how to use APO to optimize a prompt for a simple math problem.

### Step 1: Define the LitAgent

First, we define a `LitAgent` that takes a math problem as input, uses a prompt to ask an LLM to solve it, and then scores the answer.

```python
import asyncio
from openai import AsyncOpenAI
from agentlightning.litagent import LitAgent
from agentlightning.types import Rollout, NamedResources, RolloutRawResult, PromptTemplate

class MathAgent(LitAgent[dict]):
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def rollout_async(
        self, task: dict, resources: NamedResources, rollout: Rollout
    ) -> RolloutRawResult:
        prompt_template = resources.get_typed("prompt", PromptTemplate)
        prompt = prompt_template.format(problem=task["problem"])

        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        answer = response.choices[0].message.content

        try:
            # Try to evaluate the answer as a Python expression
            is_correct = str(eval(answer)) == str(task["answer"])
        except Exception:
            is_correct = False

        return {"reward": 1.0 if is_correct else 0.0, "answer": answer}
```

### Step 2: Create the Datasets

Next, we create training and validation datasets. Each item in the dataset is a dictionary containing a math problem and its expected answer.

```python
# Datasets of math problems
train_dataset = [
    {"problem": "1+1", "answer": 2},
    {"problem": "2*3", "answer": 6},
    {"problem": "10-5", "answer": 5},
]

val_dataset = [
    {"problem": "5+5", "answer": 10},
    {"problem": "8/4", "answer": 2},
    {"problem": "2**3", "answer": 8},
]
```

### Step 3: Configure and Run the Trainer

Now, we configure the `Trainer` with the `APO` algorithm, our `MathAgent`, and the datasets. We also provide a seed prompt to start the optimization process.

```python
from agentlightning.trainer import Trainer
from agentlightning.algorithm.apo import APO
from agentlightning.adapter.messages import TraceToMessages

# The initial prompt to be optimized
seed_prompt = PromptTemplate(
    name="prompt",
    template='''Solve the following math problem: {{problem}}.
Your answer should be only the numerical result.''',
)

# Configure the APO algorithm
apo_algorithm = APO(
    async_openai_client=AsyncOpenAI(),
    beam_width=2,  # Keep the top 2 prompts in each round
    branch_factor=2,  # Generate 2 new prompts from each parent
    beam_rounds=2,  # Run for 2 rounds of optimization
)

# Configure the Trainer
trainer = Trainer(
    algorithm=apo_algorithm,
    adapter=TraceToMessages(),
    initial_resources={"prompt": seed_prompt},
    n_runners=2,  # Run 2 agents in parallel
)

# Create the agent instance
agent = MathAgent(client=AsyncOpenAI())

# Start the training
trainer.fit(agent, train_dataset=train_dataset, val_dataset=val_dataset)
```

### Step 4: Retrieve the Best Prompt

After the `fit` method completes, you can retrieve the best prompt found by the APO algorithm.

```python
# Get the best prompt
best_prompt = apo_algorithm.get_best_prompt()

print("Best prompt found:")
print(best_prompt.template)
```

*Verification*: After running the code, you should see the optimized prompt printed to the console. The prompt will be a variation of the seed prompt that performed best on the validation dataset.

## 5. Common Pitfalls

- **Incorrect `LitAgent` implementation**: The `rollout` or `rollout_async` method of your `LitAgent` must return a dictionary with a "reward" key. The reward should be a float that indicates the performance of the agent on the task. APO uses this reward to evaluate the prompts.
- **Missing seed prompt**: The `APO` algorithm requires a `PromptTemplate` in the `initial_resources` of the `Trainer`. This prompt is the starting point for the optimization.
- **Small datasets**: Using very small training or validation datasets might lead to overfitting, where the optimized prompt works well for the specific examples in the datasets but not for general cases.

## 6. Challenge Yourself

- **Try a different task**: Instead of math problems, try optimizing a prompt for a different task, like summarization or translation.
- **Implement a custom scoring function**: Modify the `MathAgent` to use a more sophisticated scoring function. For example, you could give partial credit for answers that are close but not exactly correct.
- **Experiment with hyperparameters**: Try changing the `beam_width`, `branch_factor`, and `beam_rounds` of the `APO` algorithm to see how it affects the optimization process.