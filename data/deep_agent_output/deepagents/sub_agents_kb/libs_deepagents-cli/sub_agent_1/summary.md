# DeepAgents CLI Knowledge Base

## 1. Overview

The `deepagents-cli` module serves as the primary command-line interface for interacting with DeepAgents, an AI coding assistant. Its main purpose is to provide an interactive environment where users can prompt an AI agent to perform coding and development tasks. It orchestrates argument parsing, dependency checking, agent creation, and the core conversational loop, including support for local execution or remote sandboxed environments.

This module integrates various functionalities such as agent memory management, custom skills, shell execution, web search, and crucial human-in-the-loop (HITL) approval mechanisms for potentially destructive or costly operations. It aims to offer a robust and user-friendly interface for leveraging AI capabilities in development workflows.

## 2. Key Components

### `main.py`

*   **`cli_main()`**: The absolute entry point for the DeepAgents CLI application. It sets up macOS-specific environment variables, checks for dependencies, parses command-line arguments, and dispatches to appropriate handlers or starts the main asynchronous event loop.
*   **`parse_args()`**: Utilizes `argparse` to define and process all command-line arguments, including subcommands like `list`, `help`, `reset`, `skills`, and various options for agent configuration (e.g., `--agent`, `--auto-approve`, `--sandbox`).
*   **`check_cli_dependencies()`**: Ensures that all optional but required Python packages for the CLI (e.g., `rich`, `requests`, `python-dotenv`, `tavily`, `prompt-toolkit`) are installed, guiding the user if any are missing.
*   **`main()`**: The asynchronous entry point that creates the LLM model, optionally sets up a remote sandbox environment, and then delegates to `_run_agent_session`.
*   **`simple_cli()`**: Implements the core interactive loop where user input is continuously processed. It displays the CLI splash, sandbox information, web search warnings, and user tips. It handles internal slash commands (`/`), direct bash commands (`!`), and delegates general user prompts to `execute_task`.

### `agent.py`

*   **`create_cli_agent()`**: This is a central function responsible for constructing and configuring the `deepagents` core agent (a `langgraph.pregel.Pregel` instance). It dynamically adds various middlewares (`AgentMemoryMiddleware`, `SkillsMiddleware`, `ShellMiddleware`) and tools based on the execution mode (local vs. sandbox) and user preferences (e.g., `enable_memory`, `enable_skills`, `auto_approve`).
*   **`get_system_prompt()`**: Generates the initial system message for the LLM agent, providing context about the working directory, skills directory, human-in-the-loop approval rules, web search usage, and todo list management. This prompt is critical for guiding the agent's behavior.
*   **`list_agents()`**: Provides a utility to list all agents (and their associated directories) that have been created and stored in the user's DeepAgents configuration directory.
*   **`reset_agent()`**: Allows users to delete and reinitialize an agent's state, either to a default configuration or by copying the prompt from an existing agent.
*   **`_add_interrupt_on()` / `_format_*_description()`**: A set of helper functions that define how various destructive tool calls (e.g., `shell`, `write_file`, `web_search`) are presented to the user for human-in-the-loop approval, including detailed descriptions and warnings.

### `commands.py`

*   **`handle_command()`**: Interprets and executes specific slash commands entered by the user (e.g., `/quit`, `/clear` to reset agent state, `/help`, `/tokens` to show usage). It directly manipulates the agent's internal state where necessary.
*   **`execute_bash_command()`**: Handles commands prefixed with `!` by executing them directly in the local shell using `subprocess.run`. It captures and displays stdout/stderr and exit codes, providing immediate feedback to the user.

### `execution.py`

*   **`execute_task()`**: The main asynchronous function for processing a user's prompt through the configured AI agent. It streams the agent's thoughts and actions to the console in real-time, manages token tracking, and incorporates file operation tracking.
*   **`prompt_for_tool_approval()`**: A highly interactive function that prompts the user for approval or rejection of tool calls requiring human intervention. It uses terminal controls (`termios`, `tty`) for a rich, arrow-key navigable menu, displaying detailed previews of the action (e.g., file changes, shell commands, web search queries) and offering an "auto-approve all" option.
*   **Streaming Logic**: Contains sophisticated logic to handle `langgraph`'s dual-stream (`messages` and `updates`) output, distinguishing between agent text, tool calls (including partial chunks), todo list updates, and human-in-the-loop requests. It uses `rich` for formatting and rendering Markdown, tool icons, and file operation summaries.

## 3. Data Flow & Dependencies

### Overall Flow

1.  **Initialization (`main.py`)**: `cli_main()` -> `check_cli_dependencies()` -> `parse_args()`. If a command like `list` or `reset` is invoked, it's handled directly. Otherwise, `asyncio.run(main(...))` starts the asynchronous execution.
2.  **Agent Setup (`main.py`, `agent.py`)**: `main()` calls `_run_agent_session()`, which in turn calls `create_cli_agent()`. `create_cli_agent()` builds the `langgraph` agent, configuring its system prompt (from `get_system_prompt()`), tools, and middleware stack (memory, skills, shell) based on whether a sandbox is used and other flags. This also involves setting up a `CompositeBackend` for file operations, either locally (`FilesystemBackend`) or remotely (via `SandboxBackendProtocol`).
3.  **Interactive Loop (`main.py`)**: `simple_cli()` enters an infinite loop, continuously prompting the user for input.
4.  **Input Processing (`main.py`, `commands.py`)**:
    *   If input starts with `/`, `handle_command()` processes CLI-specific actions.
    *   If input starts with `!`, `execute_bash_command()` runs the command in the local shell.
    *   Otherwise, the input is passed to `execute_task()` for agent processing.
5.  **Agent Execution (`execution.py`)**: `execute_task()` receives the user's prompt (potentially augmented with file contents via `parse_file_mentions`). It then streams responses from the `langgraph` agent (`agent.astream(...)`).
6.  **Streaming Output & HITL (`execution.py`)**:
    *   The stream delivers `messages` (agent text, tool calls, tool results) and `updates` (e.g., interrupts, todo list changes).
    *   Agent text is buffered and rendered as Markdown.
    *   Tool calls are detected, displayed (with icons and formatted details), and tracked by `FileOpTracker`.
    *   Crucially, if a tool call requires human approval (configured via `interrupt_on` in `agent.py`), an `__interrupt__` is received. `execute_task()` then pauses, calls `prompt_for_tool_approval()` to solicit user input via an interactive menu. The agent resumes with the user's decision (`ApproveDecision` or `RejectDecision`).
    *   Todo list updates are also processed and rendered dynamically.
7.  **Exit**: The loop continues until the user types `quit`/`exit` or uses `/quit`, or an unhandled exception occurs.

### Key Dependencies and Interactions

*   **LangChain/LangGraph**: The core AI agent framework. `deepagents-cli` acts as a specialized client for a `LangGraph Pregel` agent, managing its state, input, and output streams.
*   **`deepagents.backends`**: Provides abstractions for file system interactions, either local (`FilesystemBackend`) or remote (`SandboxBackendProtocol` implementations like `ModalBackend`). The `CompositeBackend` allows routing operations.
*   **`rich`**: Used extensively for all console output, providing rich formatting, colors, panels, markdown rendering, and status spinners, significantly enhancing the user experience.
*   **`prompt_toolkit`**: Used by `create_prompt_session` for enhanced interactive command-line input (history, autocompletion).
*   **`subprocess`**: Essential for executing local bash commands.
*   **`termios`, `tty`**: Low-level modules for controlling terminal I/O, used to create the interactive menu for HITL approvals.

## 4. Code Deep Dive

### Snippet 1: CLI Main Loop (`simple_cli` in `main.py`)

This snippet illustrates the central interactive loop, showing how user input is categorized and dispatched.

```python
async def simple_cli(
    # ... (function arguments)
) -> None:
    # ... (initial setup, splash screen, tips)

    while True:
        try:
            user_input = await session.prompt_async()
            # ... (handle exit hints)
            user_input = user_input.strip()
        except EOFError:
            break
        except KeyboardInterrupt:
            console.print("\nGoodbye!", style=COLORS["primary"])
            break

        if not user_input:
            continue

        # Check for slash commands first
        if user_input.startswith("/"):
            result = handle_command(user_input, agent, token_tracker)
            if result == "exit":
                console.print("\nGoodbye!", style=COLORS["primary"])
                break
            if result:
                continue # Command was handled, continue to next input

        # Check for bash commands (!)
        if user_input.startswith("!"):
            execute_bash_command(user_input)
            continue

        # Handle regular quit keywords
        if user_input.lower() in ["quit", "exit", "q"]:
            console.print("\nGoodbye!", style=COLORS["primary"])
            break

        await execute_task(
            user_input, agent, assistant_id, session_state, token_tracker, backend=backend
        )
```

**Explanation**: The `simple_cli` function is the heart of the CLI. It continuously awaits user input. Based on prefixes (`/` or `!`), it dispatches to `handle_command` (for internal CLI commands) or `execute_bash_command` (for shell commands). Any other input or known exit keywords lead to the `execute_task` function, which engages the AI agent. This structured approach ensures a clear separation of concerns for different types of user interactions.

### Snippet 2: Agent Creation with Middleware (`create_cli_agent` in `agent.py`)

This snippet demonstrates how the DeepAgent is instantiated, particularly highlighting the dynamic inclusion of middleware and backend configuration based on local or sandbox modes.

```python
def create_cli_agent(
    model: str | BaseChatModel,
    assistant_id: str,
    *,
    tools: list[BaseTool] | None = None,
    sandbox: SandboxBackendProtocol | None = None,
    # ... (other arguments)
) -> tuple[Pregel, CompositeBackend]:
    # ... (setup agent directory)

    agent_middleware = []

    if sandbox is None:
        # ========== LOCAL MODE ==========
        composite_backend = CompositeBackend(
            default=FilesystemBackend(),
            routes={}, # No virtualization
        )
        if enable_memory:
            agent_middleware.append(AgentMemoryMiddleware(settings=settings, assistant_id=assistant_id))
        if enable_skills:
            agent_middleware.append(SkillsMiddleware(skills_dir=skills_dir, assistant_id=assistant_id, project_skills_dir=project_skills_dir))
        if enable_shell:
            agent_middleware.append(ShellMiddleware(workspace_root=str(Path.cwd()), env=os.environ))
    else:
        # ========== REMOTE SANDBOX MODE ==========
        composite_backend = CompositeBackend(
            default=sandbox,
            routes={}, # No virtualization
        )
        if enable_memory:
            agent_middleware.append(AgentMemoryMiddleware(settings=settings, assistant_id=assistant_id))
        if enable_skills:
            agent_middleware.append(SkillsMiddleware(skills_dir=skills_dir, assistant_id=assistant_id, project_skills_dir=project_skills_dir))
        # Note: Shell middleware not used in sandbox mode

    # ... (get system prompt, configure interrupt_on)

    agent = create_deep_agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
        backend=composite_backend,
        middleware=agent_middleware,
        interrupt_on=interrupt_on,
        checkpointer=InMemorySaver(),
    ).with_config(config)
    return agent, composite_backend
```

**Explanation**: The `create_cli_agent` function is key to the agent's adaptability. It first determines whether to operate in `LOCAL MODE` or `REMOTE SANDBOX MODE` based on the `sandbox` argument. It then configures a `CompositeBackend` with either a `FilesystemBackend` (local) or the provided `SandboxBackendProtocol` (remote). Crucially, it appends a list of specialized middlewares (`AgentMemoryMiddleware`, `SkillsMiddleware`, `ShellMiddleware`) to the agent. `ShellMiddleware` is only enabled in local mode, as remote execution is handled by the sandbox backend itself. Finally, `create_deep_agent` is called with the model, system prompt, tools, backend, and the constructed middleware stack, along with `interrupt_on` settings for HITL.

### Snippet 3: Human-in-the-Loop Approval (`prompt_for_tool_approval` in `execution.py`)

This snippet highlights the interactive mechanism for user approval of sensitive tool actions.

```python
def prompt_for_tool_approval(
    action_request: ActionRequest,
    assistant_id: str | None,
) -> Decision | dict:
    description = action_request.get("description", "No description available")
    name = action_request["name"]
    args = action_request["args"]
    preview = build_approval_preview(name, args, assistant_id) if name else None

    body_lines = []
    if preview:
        body_lines.append(f"[bold]{preview.title}[/bold]")
        body_lines.extend(preview.details)
        if preview.error:
            body_lines.append(f"[red]{preview.error}[/red]")
    else:
        body_lines.append(description)

    console.print(
        Panel(
            "[bold yellow]⚠️  Tool Action Requires Approval[/bold yellow]\n\n"
            + "\n".join(body_lines),
            border_style="yellow",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )
    if preview and preview.diff and not preview.error:
        console.print()
        render_diff_block(preview.diff, preview.diff_title or preview.title)

    options = ["approve", "reject", "auto-accept all going forward"]
    selected = 0  # Start with approve selected

    try:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdout.write("\033[?25l") # Hide cursor
            # ... (interactive menu logic with arrow keys)
        finally:
            sys.stdout.write("\033[?25h") # Show cursor
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except (termios.error, AttributeError):
        # Fallback for non-Unix systems
        # ... (simplified text-based prompt)

    # Return decision based on selection
    if selected == 0:
        return ApproveDecision(type="approve")
    if selected == 1:
        return RejectDecision(type="reject", message="User rejected the command")
    return {"type": "auto_approve_all"}
```

**Explanation**: `prompt_for_tool_approval` is a critical security and control point. When the agent proposes a potentially "destructive" action (e.g., writing a file, executing a shell command, performing a web search), this function pauses the agent's execution. It dynamically constructs a rich `rich.Panel` showing the tool's details and potential impact, including a diff preview for file changes. It then presents an interactive, arrow-key navigable menu (leveraging `termios` and `tty` for advanced terminal control) allowing the user to `approve`, `reject`, or `auto-approve all` subsequent actions. This mechanism ensures that the user remains in control of significant agent actions, fostering trust and preventing unintended consequences.

## 5. Potential Pitfalls

*   **Dependency Management**: The `check_cli_dependencies` function is crucial but relies on `ImportError` checks, which might not catch all environment issues (e.g., mismatched versions). Users need to ensure `deepagents[cli]` is installed correctly.
*   **Sandbox Configuration**: Setting up remote sandboxes can be complex. Errors during sandbox creation (as handled in `main.py`) can lead to CLI termination. Users must have their sandbox providers correctly configured (e.g., Modal credentials).
*   **Human-in-the-Loop Overload**: While HITL is important, too many approval prompts can slow down the user's workflow. The "auto-approve all" option helps, but agents need to be designed to be judicious with tool usage, especially destructive ones.
*   **System Prompt Brittleness**: The `get_system_prompt` function generates a detailed prompt. While comprehensive, LLM behavior can be sensitive to prompt changes or misunderstandings, potentially leading to incorrect actions or inefficient problem-solving.
*   **Terminal Compatibility**: The interactive menu for tool approval relies on `termios` and `tty` for advanced terminal features. These modules are Unix-specific; a fallback is provided for other systems, but the experience might be degraded.
*   **File Path Ambiguity**: When operating in local mode, the system prompt emphasizes using absolute paths. Agents might still generate relative paths if not carefully constrained, which could lead to errors or unintended file operations if the working directory changes or if the agent misunderstands the context.
*   **Resource Usage**: Running complex agent tasks, especially with web search or shell execution, can consume API credits (e.g., Tavily) and local system resources. The `TokenTracker` helps monitor LLM usage, but overall resource consumption needs to be managed. Always be mindful of the "⚠️ This will use Tavily API credits" warning for web searches.