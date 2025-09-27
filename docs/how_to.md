# How to Use This Project - Student Guide

This guide walks you through everything you can do with this Smolagents template, from basic usage to creating your own agents and tools.

## What's in This Project

**Current Setup (Single Agent):**
- `ExampleToolCallingAgent` - An agent with filesystem tools and a joke API tool
- Gradio chat UI for talking to the agent
- Example workspace with documents and code files
- File management tools (read, write, search, list directories)

**Optional Multi-Agent Setup:**
- `ExampleManagerAgent` - Coordinates other agents
- Shows how to delegate tasks between agents

## Project Structure

```
smolagents-quickstart-template/
├── agents/
│   ├── example_tool_calling_agent.py    # Worker agent with tools
│   ├── example_manager_agent.py         # Manager agent (optional)
│   └── base_agent.py                    # Base classes
├── toolkits/
│   ├── example_joke_toolkit.py          # Joke API tool
│   └── filesystem_toolkit.py            # File operations
├── data/agent_workspace/                # Agent's file workspace
│   ├── example_docs/alan_turing.md     # Sample document
│   └── example_codes/car.c             # Sample code file
├── ui/gradio_agent_ui.py               # Chat interface
├── main.py                             # App entry point
└── run.sh                              # Convenience script
```

## What You Can Ask the Agent

Once your agent is running, try these examples:

### File Operations
- "List files in my workspace"
- "Read the Alan Turing document"
- "Search for .c files"
- "Create a new file called hello.py with a simple Python program"
- "Show me the workspace structure as a tree"
- "Write a shopping list to a file called groceries.txt"

### Fun Interactions
- "Tell me a joke"
- "Get me a joke and then save it to a file"
- "Read the car.c file and explain what it does"

### Complex Tasks
- "Find all files in my workspace, read the Alan Turing document, and create a summary file"
- "Create a Python file that implements a simple calculator"

## Learning Exercises

### Exercise 1: Add a New Tool

Create a simple calculator tool in `toolkits/`:

1. Create a new file `toolkits/calculator_toolkit.py`:

```python
from smolagents import tool
from typing import List

@tool
def calculate(expression: str) -> float:
    """
    Evaluates a mathematical expression safely.
    
    Args:
        expression (str): Math expression like "2 + 3 * 4"
        
    Returns:
        float: Result of the calculation
    """
    try:
        # Use eval safely for basic math
        allowed_chars = set('0123456789+-*/.() ')
        if all(c in allowed_chars for c in expression):
            return eval(expression)
        else:
            return "Error: Invalid characters in expression"
    except Exception as e:
        return f"Error: {str(e)}"

class CalculatorToolkit:
    @staticmethod
    def get_tools() -> List:
        return [calculate]
```

2. Add it to your agent in `main.py`:

```python
from toolkits.calculator_toolkit import CalculatorToolkit

# In the main() function:
calc_tools = CalculatorToolkit.get_tools()
tool_calling_agent = ExampleToolCallingAgent(tools=joke_tools + filesystem_tools + calc_tools)
```

3. Now ask your agent: "Calculate 15 * 7 + 23"

### Exercise 2: Modify Agent Prompts

1. Open `prompts/prompts.py`
2. Modify the `EXAMPLE_TOOL_CALLING_AGENT` prompt:

```python
EXAMPLE_TOOL_CALLING_AGENT = """
You are a helpful assistant with access to file management and calculator tools. 
You're friendly and explain things clearly. When doing calculations, show your work.
Always be encouraging and educational in your responses.
"""
```

3. Restart the agent and notice how its personality changes!

### Exercise 3: Add Files to the Workspace

1. Create a new file in `data/agent_workspace/example_docs/`:

```bash
echo "# My Project Ideas

1. Build a weather app
2. Create a task manager
3. Make a simple game

## Notes
- Use Python for backend
- Consider using Flask or FastAPI
" > data/agent_workspace/example_docs/my_ideas.md
```

2. Ask the agent: "Read my project ideas file and help me plan the weather app"

### Exercise 4: Create a New Agent

1. Copy `agents/example_tool_calling_agent.py` to `agents/my_custom_agent.py`
2. Modify the name and description:

```python
class MyCustomAgent(BaseAgent):
    def __init__(self, tools: List[Tool]):
        super().__init__()

        self.agent = ToolCallingAgent(
            name="my_custom_agent",
            description="A custom agent that specializes in coding help.",
            tools=tools,
            model=LiteLLMModel(model_id=LITELLM_MODEL_ID, api_key=LITELLM_API_KEY),
            instructions="You are a coding mentor. Help users learn programming by giving clear explanations and examples."
        )
```

3. Use it in `main.py` instead of the original agent

## Enable Multi-Agent Mode

Want to see agents working together? Here's how:

1. Open `main.py`
2. Uncomment these lines:

```python
# A manager agent that manages other agents <-- uncomment for multi-agent orchestration
manager_agent: BaseAgent = ExampleManagerAgent(
    tools=[], managed_agents=[tool_calling_agent.agent]
)
```

3. Change the UI line:

```python
ui = GradioAgentUI(agent=manager_agent)  # Change from tool_calling_agent to manager_agent
```

4. Restart the app

Now you can ask: "Have your worker agent read the Alan Turing file and then create a summary"

The manager will delegate the task to the worker agent!

## Advanced Exercises

### Create a Web Search Tool

Add a tool that searches the internet:

```python
import requests
from smolagents import tool

@tool
def web_search(query: str) -> str:
    """
    Searches DuckDuckGo for information (simple implementation).
    
    Args:
        query (str): What to search for
        
    Returns:
        str: Search results
    """
    # This is a simplified example - in practice you'd use a proper API
    return f"Simulated search results for: {query}"
```

### Create a Note-Taking Agent

Build an agent that specializes in organizing notes and documents in the workspace.

### Build a Code Review Agent

Create an agent that reads code files and provides feedback and suggestions.

## Tips for Students

1. **Start small**: Begin with simple tools and gradually add complexity
2. **Read the code**: Look at existing agents and tools to understand patterns
3. **Experiment**: Try different prompts and see how agent behavior changes
4. **Use the workspace**: The agent can create and modify files - use this for projects!
5. **Combine tools**: Ask the agent to use multiple tools together for complex tasks

## Troubleshooting Common Issues

- **Agent doesn't use tools**: Check that tools are properly added to the agent in `main.py`
- **Import errors**: Make sure you're importing your new classes correctly
- **Agent gives wrong responses**: Try adjusting the prompt in `prompts/prompts.py`
- **File operations fail**: Check that `AGENT_WORKSPACE_PATH` is set correctly in `.env`

## Next Steps

- Try all the exercises above
- Create your own unique tools
- Experiment with different agent personalities
- Build a multi-agent system for a specific task
- Share your creations with other students!

