# Getting Started with the DeepAgents CLI

The `deepagents-cli` is your command-line interface for interacting with DeepAgents, an AI coding assistant designed to help you with development tasks. It provides an interactive environment where you can prompt an AI agent to perform coding, analyze code, and manage development workflows. This tutorial will guide you through setting up and using the DeepAgents CLI.

## 1. Installation

To get started, you need to install the `deepagents-cli` package. It's recommended to install it in a virtual environment.

```bash
# Create a virtual environment
python -m venv deepagents-env

# Activate the virtual environment
source deepagents-env/bin/activate # On Linux/macOS
# deepagents-env\Scripts\activate # On Windows

# Install DeepAgents CLI with all its dependencies
pip install 'deepagents[cli]'
```

This command installs the core `deepagents` library along with the necessary components for the command-line interface, including dependencies for rich terminal output (`rich`), requests, dotenv, and interactive prompting (`prompt-toolkit`).

## 2. Basic Usage and Interaction

Once installed, you can launch the DeepAgents CLI by simply running:

```bash
deepagents
```

Upon starting, you'll be greeted by an interactive prompt. The CLI operates in a conversational loop, allowing you to interact with the AI agent.

### 2.1. Interacting with the Agent

You can type natural language prompts directly to the agent.

```bash
# Example interaction
deepagents
> Explain how to create a simple Python web server using Flask.
```

The agent will then process your request, potentially performing actions like searching the web, generating code, or reading files.

### 2.2. Special Commands

The DeepAgents CLI supports several special commands for controlling the environment and interacting with the agent:

*   **Slash Commands (`/`)**: These are internal CLI commands that control the agent's state or provide utility functions.
    *   `/quit` or `/exit`: Exits the CLI.
    *   `/help`: Displays available commands and usage information.
    *   `/clear`: Resets the agent's conversation history.
    *   `/tokens`: Shows token usage for the current session.
*   **Bash Commands (`!`)**: You can execute local shell commands directly from the CLI by prefixing them with `!`.
    ```bash
    > !ls -l
    ```
    This is useful for checking files, directories, or running quick local scripts without exiting the DeepAgents environment.

### 2.3. Human-in-the-Loop (HITL) Approval

A core feature of DeepAgents is Human-in-the-Loop (HITL) approval. For potentially destructive or costly operations (like writing files, executing complex shell commands, or performing web searches), the agent will pause and ask for your explicit approval.

```mermaid
graph TD
    UserInput[User Input] -->|Prompt| Agent[DeepAgents CLI]
    Agent -->|Task Analysis| AIModel[AI Agent Model]
    AIModel -->|Proposes Action| Agent
    Agent -->|Action Requires Approval| HITL[Human-in-the-Loop Approval]
    HITL -->|Approve/Reject/Auto-Approve| Agent
    Agent -->|Execute Action| ExternalTool[External Tool (e.g., Shell, Filesystem, Web Search)]
    ExternalTool -->|Result| Agent
    Agent -->|Display Output| UserOutput[Console Output]
```

When an action requires approval, you'll see a detailed preview of the action, and you can choose to:
*   **Approve**: Allow the agent to proceed with the action.
*   **Reject**: Stop the agent from executing the current action.
*   **Auto-approve all going forward**: Approve this action and similar future actions automatically for the current session.

This mechanism ensures you always have control over what the AI agent does, especially when it interacts with your local environment or external services.

## 3. A Simple Example: Creating a File

Let's walk through an example of using the DeepAgents CLI to create a new Python file.

1.  **Start the CLI:**
    ```bash
    deepagents
    ```

2.  **Prompt the agent to create a file:**
    ```bash
    > Create a Python file named 'hello.py' that prints "Hello, DeepAgents!".
    ```

3.  **Approve the action:**
    The agent will analyze your request and likely propose to create a file. You will see a prompt for approval, detailing the file name and its content.
    ```
    ┌──────────────────────────────────────────────────────────┐
    │ ⚠️  Tool Action Requires Approval                        │
    │                                                          │
    │ [bold]Write File: hello.py[/bold]                      │
    │ Details: This action will create/overwrite 'hello.py'.   │
    └──────────────────────────────────────────────────────────┘

    --- Diff ---
    +++ hello.py
    @@ -0,0 +1,1 @@
    +print("Hello, DeepAgents!")
    ---

    Approve  Reject  Auto-accept all going forward
    ```
    Use the arrow keys to select `Approve` and press Enter.

4.  **Verify the file:**
    After approval, the agent will execute the file creation. You can then use a bash command to confirm the file exists:
    ```bash
    > !cat hello.py
    ```
    You should see:
    ```
    print("Hello, DeepAgents!")
    ```

5.  **Clean up (optional):**
    You can also ask the agent to delete the file:
    ```bash
    > Delete the file 'hello.py'.
    ```
    Again, approve the `delete_file` action when prompted.

## 4. Understanding the Flow

The DeepAgents CLI orchestrates a complex flow to provide its interactive experience. Here's a simplified overview:

```mermaid
graph TD
    A[User starts CLI `deepagents`] --> B{Interactive Loop `simple_cli()`}
    B --> C{User Input}
    C --> |Prefix `/`| D[Handle CLI Command `handle_command()`]
    C --> |Prefix `!`| E[Execute Bash Command `execute_bash_command()`]
    C --> |No Prefix| F[Execute Agent Task `execute_task()`]

    F --> G[Create/Configure Agent `create_cli_agent()`]
    G --> H{Agent Execution (`langgraph`)}
    H --> I[Stream Output & Track Tools]
    I --> J{Tool Requires HITL?}
    J --> |Yes| K[Prompt for Approval `prompt_for_tool_approval()`]
    J --> |No| L[Continue Execution]
    K --> H
    L --> I

    D --> B
    E --> B
    K --> B
    I --> B
```

This diagram illustrates how your input is processed: either as a direct CLI command, a shell command, or a prompt for the AI agent. The agent's actions are then streamed back to you, with critical actions requiring your approval via the Human-in-the-Loop mechanism.

## Conclusion

The DeepAgents CLI provides a powerful and interactive way to leverage AI for your development tasks. By understanding its basic commands, interaction patterns, and the crucial Human-in-the-Loop approval system, you can effectively integrate AI assistance into your workflow while maintaining full control.