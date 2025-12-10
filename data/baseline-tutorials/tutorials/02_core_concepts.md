# Core Concepts: Building a Basic Agent

Welcome to the second tutorial in our series on the `deepagents` library. In this guide, we'll explore the fundamental components of the library and walk through creating and running a basic agent. By the end, you'll understand the roles of `Agent` and its configuration, and you'll have a runnable example to build upon.

## The Core Components

The `deepagents` library is designed for creating sophisticated, autonomous agents that can perform complex tasks. The primary entrypoint for this is the `create_deep_agent` function, which can be thought of as the configuration and assembly point for an agent.

### `create_deep_agent`: The Agent Factory

Instead of a rigid `Agent` class that you subclass, `deepagents` provides a powerful factory function called `create_deep_agent`. This function takes numerous arguments to configure and build a highly customized agent. This approach offers flexibility and simplifies the process of creating agents with different capabilities.

You can find the `create_deep_agent` function in `libs/deepagents/deepagents/graph.py`.

### Agent Configuration

When you call `create_deep_agent`, you are essentially defining the configuration for your agent. Some of the key parameters include:

- `model`: The underlying language model to use (e.g., `ChatAnthropic`, `ChatOpenAI`).
- `tools`: A list of tools the agent can use to interact with its environment (e.g., search tools, file system tools).
- `system_prompt`: A set of instructions that define the agent's goals, personality, and constraints.
- `middleware`: A list of `AgentMiddleware` that can intercept and modify the agent's behavior.
- `subagents`: A list of specialized agents that the main agent can delegate tasks to.

Think of the arguments to `create_deep_agent` as the "AgentConfig." They are the blueprint that the factory uses to construct the final, runnable agent.

### The `Agent`: A Compiled State Graph

The object returned by `create_deep_agent` is a `CompiledStateGraph` from the LangGraph library. This is your `Agent`. It's a state machine that can execute tasks, use tools, and manage its internal state. You interact with this agent by invoking it with a task.

## Architecture Diagram

This Mermaid diagram illustrates the relationship between your script, the `create_deep_agent` function, and the resulting agent:

```mermaid
graph TD
    subgraph Your Application
        A[main.py] --> B{create_deep_agent};
    end

    subgraph Configuration
        C[AgentConfig: model, tools, prompt, etc.] -- Passed as arguments --> B;
    end

    subgraph DeepAgents Library
        B -- Returns --> D[Agent (CompiledStateGraph)];
    end

    subgraph Execution
        A -- Invokes with a task --> D;
        D -- Executes task --> E[Output];
    end
```

## Building a Basic Agent: A Runnable Example

Now, let's put these concepts into practice. Here is a simple Python script that creates a basic agent and asks it to perform a task. For this example, we will not be giving the agent any tools, so it will have to rely on its own knowledge.

### `main.py`

```python
from deepagents import create_deep_agent

def main():
    """
    This example demonstrates how to create a basic agent and have it perform a task.
    """

    # 1. Create the Agent
    # We are using the default model (Claude Sonnet 4) and no extra tools.
    # The system_prompt gives the agent its instructions.
    agent = create_deep_agent(
        system_prompt="You are a helpful assistant. Please be concise.",
    )

    # 2. Define the Task
    # The task is a simple question.
    task = {
        "messages": [
            {
                "role": "user",
                "content": "What is the capital of France?",
            }
        ]
    }

    # 3. Invoke the Agent and Get the Result
    # The agent will process the task and return the result.
    result = agent.invoke(task)

    # 4. Print the Output
    # The final message from the assistant is in the 'messages' list.
    print(result['messages'][-1].content)

if __name__ == "__main__":
    main()

```

### How to Run the Script

To run this script, you'll need to have the `deepagents` library and its dependencies installed. You will also need to have your Anthropic API key set as an environment variable.

```bash
export ANTHROPIC_API_KEY="your-api-key"
python main.py
```

### Expected Output

The agent will respond to the question, and you should see the following output:

```
The capital of France is Paris.
```

## Conclusion

In this tutorial, you've learned about the core components of the `deepagents` library. You now understand that:

- Agents are created using the `create_deep_agent` factory function.
- The arguments to `create_deep_agent` serve as the agent's configuration.
- The returned agent is a `CompiledStateGraph` that you can invoke with tasks.

You have also seen a simple, runnable example that you can use as a starting point for your own projects. In the next tutorial, we will explore how to add tools to an agent to give it more capabilities.