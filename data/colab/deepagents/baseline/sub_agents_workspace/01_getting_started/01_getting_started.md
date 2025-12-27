'''
# Getting Started with Deep Agents

## 1. Goal

This tutorial will guide you through the basics of the `deepagents` Python package. You will learn how to create a "Deep Agent" capable of complex, multi-step tasks by leveraging planning, tool use, and even sub-agents.

Deep Agents are designed to overcome the limitations of simple, single-shot agents by providing them with a richer set of capabilities to reason and act over longer tasks.

## 2. Prerequisites

Before you begin, you need to have the `deepagents` package installed.

```bash
# Using pip
pip install deepagents

# Using uv
uv add deepagents
```

You will also need an LLM provider. For this tutorial, we'll use Tavily for web searches, so you'll need to install its client and get an API key.

```bash
pip install tavily-python
```

Make sure to set your `TAVILY_API_KEY` environment variable.

## 3. Architecture

A Deep Agent is not just a single LLM call. It's a system composed of several components that work together. The main agent can use a planner to break down tasks, use tools to interact with the outside world, manage a file system for memory, and delegate tasks to specialized sub-agents.

Here is a conceptual diagram of the architecture:

```mermaid
graph TD
    A[User Request] --> B{Deep Agent};
    B --> C[Planner (write_todos)];
    B --> D[Tools (e.g., internet_search)];
    B --> E[File System (ls, read, write)];
    B --> F[Sub-Agents];
    C --> B;
    D --> B;
    E --> B;
    F --> B;
    B --> G[Final Response];
```

## 4. Implementation

Let's create a simple research agent. This agent will use the `internet_search` tool to answer a question.

First, we define our tool and the system prompt that instructs the agent on its role and how to use the tool.

```python
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

# Ensure your TAVILY_API_KEY is set in your environment variables
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# 1. Define a tool for the agent to use
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )


# 2. Create a system prompt to guide the agent
research_instructions = """You are an expert researcher. Your job is to conduct thorough research and write a polished report.

You have access to an internet search tool as your primary means of gathering information.

## `internet_search`

Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
"""

# 3. Create the deep agent
agent = create_deep_agent(
    tools=[internet_search],
    system_prompt=research_instructions,
)

# 4. Invoke the agent with a user request
result = agent.invoke({"messages": [{"role": "user", "content": "What is LangGraph?"}]})

# The result will contain the agent's final answer and intermediate steps
print(result['messages'][-1].content)

```

When you run this code, the `deepagents` library constructs a LangGraph graph that orchestrates the agent's execution. The agent will receive the user's question, recognize that it needs to use the `internet_search` tool, call it, and then use the results to formulate a final answer.

## 5. Core Capabilities

The `create_deep_agent` factory automatically includes powerful middleware that gives your agent its "deep" capabilities:

- **Planning (`TodoListMiddleware`)**: The agent gets a `write_todos` tool to break down complex tasks and track its progress.
- **File System (`FilesystemMiddleware`)**: The agent can use `ls`, `read_file`, `write_file`, and `edit_file` to manage a virtual filesystem. This is crucial for handling large amounts of information without overflowing the context window.
- **Sub-Agents (`SubAgentMiddleware`)**: The agent can delegate specific tasks to other, more specialized agents, keeping the main agent's focus clean and organized.

These features are available out-of-the-box and can be customized or extended as needed. You can start with this simple example and progressively add more tools, sub-agents, and complex instructions to build highly sophisticated autonomous agents.
'''