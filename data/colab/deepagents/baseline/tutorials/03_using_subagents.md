# Mastering Task Delegation with Sub-Agents in `deepagents`

## 1. Goal

This tutorial will teach you how to use the powerful sub-agent feature in the `deepagents` library. Sub-agents allow your main agent to delegate complex, independent tasks to specialized, isolated agents. This improves organization, efficiency, and enables more complex workflows by breaking them down into smaller, manageable parts.

By the end of this tutorial, you will know how to:
- Use the default `general-purpose` sub-agent.
- Define and use custom sub-agents with specific tools and instructions.
- Integrate pre-built `LangGraph` runnables as sub-agents.

## 2. Prerequisites

- The `deepagents` library installed (`pip install deepagents`).
- An LLM provider configured (e.g., set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`).

## 3. Architecture: The Sub-Agent Workflow

The main agent acts as an orchestrator, using the built-in `task` tool to spawn one or more sub-agents. Each sub-agent operates in an isolated environment, completes its assigned task, and returns a single result to the main agent. The main agent can then synthesize these results to form a final response.

```mermaid
graph TD
    A[Main Agent] -- Delegates "Research X" --> B{Task Tool};
    B -- Spawns --> C[Sub-Agent: Researcher];
    C -- Executes research steps --> C;
    C -- Returns findings --> D[Result];
    D -- Incorporated by --> A;
    A -- Presents final answer --> E[User];
```

This pattern is incredibly useful for:
- **Parallelization**: Running multiple independent research tasks concurrently.
- **Isolation**: Preventing large, context-heavy tasks (like analyzing a large codebase) from overwhelming the main agent's context window.
- **Specialization**: Creating expert agents with specific tools and instructions for a given domain (e.g., a "DatabaseAdmin" agent).

## 4. Implementation

Let's dive into the code. The primary way to configure sub-agents is through the `subagents` parameter in `create_deep_agent`.

### Using the Default `general-purpose` Sub-Agent

Every agent created with `create_deep_agent` has access to a `task` tool by default. This tool can launch a `general-purpose` sub-agent that inherits the main agent's tools and model. It's perfect for isolating complex, multi-step tasks without needing custom configuration.

```python
import os
from deepagents import create_deep_agent

# Make sure your API key is set
# os.environ["ANTHROPIC_API_KEY"] = "your-api-key"

# The default agent comes with the `task` tool to spawn a general-purpose sub-agent
agent = create_deep_agent(
    system_prompt="You are a helpful assistant."
)

# The agent will automatically use the sub-agent for complex, independent tasks.
result = agent.invoke({
    "messages": [
        {
            "role": "user", 
            "content": "Please research the main features of LangGraph and also find out who the original author of the `glob` library is."
        }
    ]
})

print(result['messages'][-1].content)
```

In the example above, the agent can choose to use the `task` tool to spawn two `general-purpose` sub-agents in parallel: one to research LangGraph, and another to find the author of `glob`.

### Defining Custom Sub-Agents

For more advanced use cases, you can define your own specialized sub-agents. This is done by passing a list of `SubAgent` dictionaries to `create_deep_agent`.

Each dictionary defines the sub-agent's `name`, `description` (which helps the main agent decide when to use it), `prompt`, and `tools`.

```python
import os
from deepagents import create_deep_agent
from langchain_core.tools import tool

# A custom tool for our researcher
@tool
def internet_search(query: str) -> str:
    """Runs a fake internet search."""
    if "langgraph" in query.lower():
        return "LangGraph is a library for building stateful, multi-actor applications with LLMs."
    return "No results found."

# Define a specialized sub-agent for research
research_subagent = {
    "name": "research-agent",
    "description": "Used to research in-depth questions on any topic.",
    "prompt": "You are an expert researcher. Use your tools to find the most accurate information.",
    "tools": [internet_search],
    # You can optionally specify a different model
    # "model": "openai:gpt-4o",
}

# The main agent will now have access to this custom sub-agent via the `task` tool
agent = create_deep_agent(
    subagents=[research_subagent]
)

result = agent.invoke({
    "messages": [
        {
            "role": "user", 
            "content": "Can you use your researcher to tell me about LangGraph?"
        }
    ]
})

print(result['messages'][-1].content)
```

### Using a Pre-Compiled LangGraph as a Sub-Agent

If you have an existing `LangGraph` agent, you can integrate it directly as a sub-agent using the `CompiledSubAgent` class. This allows you to reuse complex, pre-built graphs within the `deepagents` framework.

```python
import os
from deepagents import create_deep_agent, CompiledSubAgent
from langchain_core.runnables import RunnableLambda

# Imagine this is your pre-built LangGraph agent
def my_data_analysis_graph(state):
    # Complex logic here...
    return {"messages": [{"role": "assistant", "content": "Analyzed data: 42"}]}

# Wrap your runnable in a CompiledSubAgent
data_analyzer_subagent = CompiledSubAgent(
    name="data-analyzer",
    description="A specialized agent for performing data analysis.",
    runnable=RunnableLambda(my_data_analysis_graph)
)

agent = create_deep_agent(
    subagents=[data_analyzer_subagent]
)

result = agent.invoke({
    "messages": [
        {
            "role": "user", 
            "content": "Please analyze my data."
        }
    ]
})

print(result['messages'][-1].content)

```

## 5. Conclusion

You've learned how to leverage sub-agents in `deepagents` to build more modular and powerful agentic systems. By delegating tasks to default, custom, or pre-compiled sub-agents, you can create sophisticated workflows that are efficient, scalable, and easier to manage.