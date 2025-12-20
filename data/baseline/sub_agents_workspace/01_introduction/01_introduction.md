
# Introduction to Agent Lightning

Welcome to the world of Agent Lightning! In this tutorial, we will introduce you to the core concepts of Agent Lightning and show you how to get started with this powerful tool.

## 1. Goal

By the end of this tutorial, you will be able to:

*   Understand what Agent Lightning is and the problems it solves.
*   Explain the architecture of Agent Lightning.
*   Install Agent Lightning and its dependencies.
*   Run a simple "Hello World" example.

## 2. What is Agent Lightning?

Agent Lightning is a powerful framework that allows you to optimize your AI agents with almost zero code changes. It is designed to work with any agent framework, including LangChain, OpenAI Agent SDK, AutoGen, and more. With Agent Lightning, you can selectively optimize one or more agents in a multi-agent system using algorithms like Reinforcement Learning, Automatic Prompt Optimization, and Supervised Fine-tuning.

### Core Features

*   **Zero Code Change (almost!):** Turn your agent into an optimizable powerhouse with minimal modifications.
*   **Framework Agnostic:** Build with any agent framework you prefer, or even without one.
*   **Selective Optimization:** Target and optimize specific agents in a complex multi-agent system.
*   **Algorithm-Driven:** Leverage powerful algorithms like Reinforcement Learning, Automatic Prompt Optimization, and more.

## 3. Architecture

Agent Lightning's architecture is designed to be simple and flexible. It consists of a few key components that work together to optimize your agents.

```mermaid
graph TD
    A["Your Agent"] -->|Events (Prompts, Tool Calls, Rewards)| B["LightningStore"];
    B -->|Traces| C["Algorithm"];
    C -->|Updated Resources (Prompt Templates, Policy Weights)| B;
    B -->|Updated Resources| D["Inference Engine"];
    D --> A;
```

*   **Your Agent:** This is the agent you want to optimize. It can be built with any framework.
*   **LightningStore:** A central hub that stores tasks, resources, and traces of your agent's activities.
*   **Algorithm:** This is where the optimization happens. You can choose from a variety of built-in algorithms or create your own.
*   **Inference Engine:** This component is updated with the improved resources from the algorithm, which in turn improves your agent's performance.

## 4. Installation

To get started with Agent Lightning, you need to install the `agentlightning` package. You can do this using `pip`:

```bash
pip install agentlightning
```

This will install the core Agent Lightning package and its dependencies.

## 5. "Hello World" Example

Now that you have Agent Lightning installed, let's create a simple "Hello World" example to see it in action. We'll create a basic agent and use Agent Lightning to capture its actions.

First, let's create a Python file named `hello_agent.py`:

```python
import agentlightning as agl

# 1. Initialize the emitter
agl.init()

@agl.instrument
def my_agent(prompt: str):
    print(f"Agent received prompt: {prompt}")
    return "Hello from the agent!"

if __name__ == "__main__":
    response = my_agent("Hello, world!")
    print(f"Agent returned: {response}")
```

In this example:

1.  We import the `agentlightning` library.
2.  We initialize Agent Lightning using `agl.init()`.
3.  We decorate our agent function `my_agent` with `@agl.instrument`. This decorator automatically captures the function's inputs and outputs.

When you run this script, Agent Lightning will be active in the background, tracing the execution of your agent. This is the first step to enabling powerful optimizations for your agents.

## 6. Conclusion

You have now taken your first steps with Agent Lightning! You have learned about its core concepts, architecture, and how to set it up in your project. In the next tutorials, we will dive deeper into the capabilities of Agent Lightning and show you how to apply different optimization algorithms to your agents.
