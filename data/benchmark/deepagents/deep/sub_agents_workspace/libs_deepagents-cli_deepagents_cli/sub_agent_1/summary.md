'''
# Deep Agents CLI Documentation

## Overview

The `deepagents-cli` is a command-line AI coding assistant designed to run in a developer's terminal. It provides a conversational interface for interacting with an AI agent that can perform a variety of tasks, including file operations, code execution, web searches, and more. It is designed to be highly customizable through a system of "skills" and persistent memory, allowing it to adapt to specific projects and user preferences. The CLI can operate locally or utilize remote "sandboxes" for code execution, providing a safe and isolated environment.

## Entry Points

- **Main Executable**: The primary entry point for users is the `deepagents` or `deepagents-cli` command, defined in `pyproject.toml` under `[project.scripts]`. This command executes the `cli_main` function in `deepagents_cli/main.py`.
- **Initialization Function**: `cli_main()` is the starting point of the application logic. It handles command-line argument parsing (using `argparse`), checks for dependencies, and then calls the main asynchronous function `main()`.
- **Core Logic**: The `main()` function orchestrates the setup of the AI model, session state, and sandbox environment (if requested). It then calls `_run_agent_session()`, which creates the agent and starts the interactive chat loop in `simple_cli()`.

For a new developer, the best place to start is `deepagents_cli/main.py`, following the execution flow from `cli_main()` to `main()` and then to `simple_cli()` to understand the main loop.

## Key Concepts

- **Agent**: The core AI entity that processes user requests. It is created using the `create_cli_agent` function and consists of an LLM model, a set of tools, and a system prompt that defines its behavior.
- **Sandbox**: An isolated remote environment for executing code. The CLI supports multiple sandbox backends like "modal", "daytona", and "runloop". This prevents the agent from executing arbitrary code directly on the user's local machine. The `create_sandbox` factory in `integrations/sandbox_factory.py` is responsible for instantiating the correct sandbox.
- **Skill**: A reusable set of instructions that extends the agent's capabilities for specific tasks (e.g., "web-research"). Skills are defined in `SKILL.md` files and are discovered and loaded by the `SkillsMiddleware`. The agent only reads the full skill instructions when a task matches the skill's description, a pattern known as "progressive disclosure."
- **Memory**: The agent's ability to retain information across sessions. This is achieved through `agent.md` files located in a global `~/.deepagents/<agent_name>/` directory and a project-specific `.deepagents/` directory. The agent can read from and write to these files to remember user preferences, project context, and coding conventions.

## Dependencies & Relationships

- **What this component CALLS:**
    - `deepagents` (core library): The CLI is a wrapper around the main `deepagents` library, using its components to create and run the agent.
    - `langchain-openai`: To create the underlying language model (`ChatOpenAI`).
    - `tavily-python`: For the `web_search` tool.
    - Sandbox APIs: `modal`, `daytona`, `runloop-api-client` for remote code execution.
    - `rich`, `prompt-toolkit`: For the interactive terminal UI.

- **What CALLS this component:**
    - The user, by executing the `deepagents` or `deepagents-cli` command in their terminal.

- **External Libraries Used:**
    - `argparse`: For parsing command-line arguments.
    - `asyncio`: The entire application is built on an asynchronous event loop.
    - `requests`: For making HTTP requests (e.g., in the `http_request` tool).
    - `python-dotenv`: For loading environment variables from `.env` files.

## Patterns & Conventions

- **Asynchronous Execution**: The application heavily uses `asyncio` for all I/O-bound operations, including the main chat loop (`simple_cli`) and tool execution. This ensures the UI remains responsive.
- **Command-Line Interface (CLI) Parsing**: Standard `argparse` is used to define and parse subcommands (`list`, `reset`, `skills`) and flags (`--agent`, `--auto-approve`, `--sandbox`).
- **Dependency Management**: Python dependencies are managed in `pyproject.toml` and checked at runtime by `check_cli_dependencies()` to provide user-friendly installation instructions.
- **Factory Pattern**: The `create_sandbox` function acts as a factory, abstracting away the specific details of creating different types of sandbox backends.
- **Error Handling**: The main execution flow in `main.py` is wrapped in a `try...except` block that catches common exceptions (`KeyboardInterrupt`, `ImportError`, generic `Exception`) and prints user-friendly error messages instead of crashing with a traceback.

## Code Examples

### 1. Main Entry Point and Argument Parsing

```python
# In deepagents_cli/main.py
def cli_main() -> None:
    """Entry point for console script."""
    # ... (dependency checks and env setup)
    try:
        args = parse_args()

        if args.command == "help":
            show_help()
        # ... (other commands)
        else:
            # Create session state from args
            session_state = SessionState(auto_approve=args.auto_approve, no_splash=args.no_splash)

            # API key validation happens in create_model()
            asyncio.run(
                main(
                    args.agent,
                    session_state,
                    args.sandbox,
                    args.sandbox_id,
                    args.sandbox_setup,
                )
            )
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        console.print("\n\n[yellow]Interrupted[/yellow]")
        sys.exit(0)
```
**Why this matters:** This shows how the CLI is structured using `argparse` to handle different commands and flags. The `asyncio.run(main(...))` call is the bridge from the synchronous entry point to the async core of the application. The `try/except` block ensures a graceful exit on user interruption.

### 2. Conditional Sandbox Creation

```python
# In deepagents_cli/main.py
async def main(
    # ... args
) -> None:
    model = create_model()

    # Branch 1: User wants a sandbox
    if sandbox_type != "none":
        try:
            with create_sandbox(
                sandbox_type, sandbox_id=sandbox_id, setup_script_path=setup_script_path
            ) as sandbox_backend:
                # ...
                await _run_agent_session(
                    model,
                    assistant_id,
                    session_state,
                    sandbox_backend,
                    # ...
                )
        except (ImportError, ValueError, RuntimeError, NotImplementedError) as e:
            # ... (fail hard with error message)

    # Branch 2: User wants local mode
    else:
        await _run_agent_session(model, assistant_id, session_state, sandbox_backend=None)
```
**Why this matters:** This snippet demonstrates a key feature: conditional logic for local vs. remote execution. It uses a `with` statement and the `create_sandbox` factory to manage the lifecycle of the remote environment. This design pattern cleanly separates the sandbox setup from the core agent logic, which is handled by `_run_agent_session`.

### 3. Interactive CLI Loop

```python
# In deepagents_cli/main.py
async def simple_cli(
    # ... args
) -> None:
    # ... (startup messages)

    # Create prompt session and token tracker
    session = create_prompt_session(assistant_id, session_state)
    token_tracker = TokenTracker()

    while True:
        try:
            user_input = await session.prompt_async()
            # ...
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        # Check for slash commands, bash commands, or quit keywords
        # ...

        await execute_task(
            user_input, agent, assistant_id, session_state, token_tracker, backend=backend
        )
```
**Why this matters:** This is the heart of the user interaction. It shows the main `while` loop that listens for user input using `prompt_toolkit` (`session.prompt_async()`). It preprocesses the input to check for special commands (like `/help` or `!ls`) before passing the user's request to `execute_task` for the agent to handle. This structure is fundamental to any interactive CLI application.

## Tutorial Hints

- **Common Questions:**
    - "How do I add a new tool for the agent to use?" -> You can add new tool functions in `deepagents_cli/tools.py` and then append them to the `tools` list in `_run_agent_session` within `main.py`.
    - "What's the difference between local and sandbox mode?" -> Local mode executes shell commands directly on your machine (use with caution!), while sandbox mode executes them in a secure, remote environment defined by `--sandbox` flag.
    - "How can I make the agent always follow my project's coding style?" -> Create a `.deepagents/agent.md` file in your project root and describe your coding conventions there. The agent will read this file and use it as part of its system prompt.

- **Pitfalls & Gotchas:**
    - **API Keys**: The application will not work without the necessary API keys (e.g., `OPENAI_API_KEY`). These should be set as environment variables or placed in a `.env` file. The CLI will warn if the `TAVILY_API_KEY` is missing, disabling web search.
    - **macOS gRPC Issue**: On macOS, a specific environment variable (`GRPC_ENABLE_FORK_SUPPORT=0`) must be set for the gRPC dependencies used by some sandboxes to work correctly. This is handled automatically in `cli_main`.
    - **Auto-Approve**: Using `--auto-approve` is powerful but can be dangerous, as it allows the agent to modify files and run commands without user confirmation. Advise users to be cautious with this feature.

- **Prerequisites:**
    - A basic understanding of how to use a command-line terminal.
    - Familiarity with the concept of AI agents and Large Language Models (LLMs).
    - Python 3.11+ installed.
    - For sandbox usage, users will need accounts and API keys for the respective services (Modal, Daytona, etc.).
'''