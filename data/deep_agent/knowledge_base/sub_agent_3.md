```mermaid
graph TD
    User[User Input] --> CLI_MAIN[main.py: cli_main()]
    CLI_MAIN --> ParseArgs[main.py: parse_args()]

    subgraph CLI Commands
        ParseArgs -- "Special Commands" --> ListAgents[agent.py: list_agents()]
        ParseArgs -- "Special Commands" --> ResetAgent[agent.py: reset_agent()]
        ParseArgs -- "Special Commands" --> SkillsCmd[skills.py: execute_skills_command()]
    end

    ParseArgs -- "Interactive Mode" --> MainAsync[main.py: main()]
    MainAsync -- "Create Model" --> CreateModel[config.py: create_model()]

    subgraph Sandbox Management
        MainAsync -- "Sandbox Type" --> CreateSandbox[sandbox_factory.py: create_sandbox()]
        CreateSandbox -- "Sandbox Backend" --> RunAgentSession[main.py: _run_agent_session()]
    end

    MainAsync -- "No Sandbox" --> RunAgentSession
    RunAgentSession -- "Create Agent" --> CreateCLIAgent[agent.py: create_cli_agent()]

    subgraph Agent Creation (create_cli_agent)
        CreateCLIAgent -- "Middleware Config" --> AgentMemoryMW[agent_memory.py: AgentMemoryMiddleware]
        CreateCLIAgent -- "Middleware Config" --> SkillsMW[skills.py: SkillsMiddleware]
        CreateCLIAgent -- "Middleware Config (Local Only)" --> ShellMW[shell.py: ShellMiddleware]
        CreateCLIAgent -- "Backend Config" --> CompositeBackend[deepagents.backends: CompositeBackend]
        CreateCLIAgent -- "Interrupt Config" --> InterruptOn[agent.py: _add_interrupt_on()]
    end

    CreateCLIAgent --> SimpleCLI[main.py: simple_cli()]
    SimpleCLI --> PromptSession[input.py: create_prompt_session()]
    PromptSession --> UserInput[User Input Field]
    UserInput -- "Text" --> HandleCmd[commands.py: handle_command()]
    UserInput -- "Text (!bash)" --> ExecuteBash[commands.py: execute_bash_command()]
    HandleCmd -- "Agent Input" --> ExecuteTask[execution.py: execute_task()]
    ExecuteBash -- "Agent Input" --> ExecuteTask

    subgraph Task Execution (execute_task)
        ExecuteTask -- "Stream Agent Response" --> AgentStream[Agent.astream()]
        AgentStream -- "Tool Call Chunks/Messages" --> DisplayTool[execution.py]
        AgentStream -- "Interrupt" --> PromptApproval[execution.py: prompt_for_tool_approval()]
        PromptApproval -- "User Decision" --> AgentStream[Resume Agent]
        AgentStream -- "Text/Markdown" --> ConsoleOutput[Console Output]
        AgentStream -- "Todos" --> RenderTodoList[ui.py]
        AgentStream -- "File Operations" --> RenderFileOp[ui.py]
    end

    DisplayTool --> ConsoleOutput
    RenderTodoList --> ConsoleOutput
    RenderFileOp --> ConsoleOutput

    AgentStream -- "Final Response" --> ConsoleOutput
```

# deepagents_cli_core Analysis

## 1. Overview
This module provides the core command-line interface (CLI) for DeepAgents, an AI coding assistant. It handles agent creation, lifecycle management, user interaction, command parsing, and task execution, including support for remote sandbox environments. The CLI allows users to interact with AI agents, manage their memory and skills, and execute code either locally or in a remote sandbox with human-in-the-loop approval for sensitive operations.

## 2. File-by-File Analysis

### `libs/deepagents-cli/deepagents_cli/main.py`
- **Purpose**: This file serves as the primary entry point for the `deepagents-cli` application. It sets up the argument parser, handles CLI commands like `list`, `reset`, and `skills`, and orchestrates the main interactive CLI loop (`simple_cli`). It also manages sandbox creation and dependency checks.
- **Key Components**:
  - `check_cli_dependencies()`: Verifies that all necessary optional Python packages for the CLI are installed.
  - `parse_args()`: Configures and parses command-line arguments, including subcommands for agent management and options for sandbox and auto-approval.
  - `simple_cli()`: The main asynchronous CLI loop that handles user input, processes slash commands, executes bash commands, and delegates tasks to the AI agent. It also manages the display of agent output, token tracking, and sandbox information.
  - `_run_agent_session()`: A helper function that creates the AI agent with appropriate tools and middleware, calculates baseline tokens, and then invokes `simple_cli`.
  - `main()`: The asynchronous main function that initializes the LLM model, handles conditional sandbox creation (Modal, Daytona, Runloop), and calls `_run_agent_session`.
  - `cli_main()`: The synchronous entry point that calls `parse_args` and then `asyncio.run(main())` to start the asynchronous CLI.

### `libs/deepagents-cli/deepagents_cli/agent.py`
- **Purpose**: This module is responsible for the creation, listing, and resetting of DeepAgents. It integrates with the `deepagents` library to construct the agent graph and configure its various middleware components, such as memory, skills, and shell execution, adapting to local or remote sandbox environments.
- **Key Components**:
  - `list_agents()`: Displays a list of all configured agents by iterating through the user's DeepAgents directory.
  - `reset_agent()`: Deletes an agent's directory and re-initializes its `agent.md` with either default instructions or content copied from another agent.
  - `get_system_prompt()`: Generates the base system prompt for the agent, dynamically including information about the current working directory, skills directory, and guidelines for human-in-the-loop approval, web search, and todo list management. This prompt adapts based on whether a remote sandbox is being used.
  - `_format_*_description()` functions: These private helper functions are used to format descriptions of various tool calls (e.g., `write_file`, `shell`, `web_search`) for human-in-the-loop approval prompts, providing clear summaries of the actions to be taken.
  - `_add_interrupt_on()`: Configures the `InterruptOnConfig` settings for `langchain.agents.middleware`, defining which tools require human approval and how their descriptions should be formatted.
  - `create_cli_agent()`: The core function for instantiating an AI agent. It sets up the `CompositeBackend` (for local filesystem or remote sandbox), adds various middleware (AgentMemoryMiddleware, SkillsMiddleware, ShellMiddleware), and constructs a `langgraph.pregel.Pregel` agent graph with a `InMemorySaver` for checkpointing.

### `libs/deepagents-cli/deepagents_cli/agent_memory.py`
- **Purpose**: This module defines the `AgentMemoryMiddleware`, which is responsible for loading and injecting agent-specific long-term memory into the system prompt. It supports both user-specific and project-specific memory, enabling the agent to retain context across sessions and projects.
- **Key Components**:
  - `AgentMemoryState` (TypedDict): Defines the structure for the agent's memory state, including `user_memory` and `project_memory`.
  - `AgentMemoryStateUpdate` (TypedDict): Defines the structure for updating the agent's memory state.
  - `LONGTERM_MEMORY_SYSTEM_PROMPT`: A multi-line string constant that provides detailed instructions to the agent on how to manage, read, and update its long-term memory, distinguishing between user and project-level memory files (`agent.md`). It also guides the agent on when to check memories and how to decide where to store different types of information.
  - `DEFAULT_MEMORY_SNIPPET`: A format string used to embed the user and project memory content into the system prompt.
  - `AgentMemoryMiddleware` (class):
    - `__init__()`: Initializes the middleware with settings, agent ID, and an optional system prompt template. It also sets up paths for user and project memory directories.
    - `before_agent()`: This method is called before agent execution. It loads `user_memory` and `project_memory` from `agent.md` files (if they exist and are not already in the state) and returns an `AgentMemoryStateUpdate`.
    - `_build_system_prompt()`: Constructs the complete system prompt by combining the base system prompt with the loaded user and project memories, and the `LONGTERM_MEMORY_SYSTEM_PROMPT` documentation.
    - `wrap_model_call()` and `awrap_model_call()`: These methods intercept model calls to inject the augmented system prompt (containing memory information) before the request is sent to the LLM.

### `libs/deepagents-cli/deepagents_cli/commands.py`
- **Purpose**: This module provides handlers for various slash commands (e.g., `/clear`, `/help`, `/tokens`, `/quit`) and allows for the execution of arbitrary bash commands prefixed with `!`. It directly manipulates the agent's state (e.g., clearing conversation history) or interacts with the operating system.
- **Key Components**:
  - `handle_command()`: Processes slash commands entered by the user. It can reset the agent's conversation state (`/clear`), display help (`/help`), show token usage (`/tokens`), or exit the CLI (`/quit`).
  - `execute_bash_command()`: Executes a given bash command using `subprocess.run` and displays its stdout, stderr, and return code to the console.

### `libs/deepagents-cli/deepagents_cli/execution.py`
- **Purpose**: This module is central to the interactive operation of the CLI, handling the streaming of agent responses, human-in-the-loop (HITL) tool approval, and dynamic UI updates (like todo lists and file operations). It manages the complex interplay between the AI agent and the user interface during task execution.
- **Key Components**:
  - `prompt_for_tool_approval()`: Presents a rich, interactive prompt to the user for approving or rejecting tool actions. It displays a formatted description of the action, including diffs for file operations, and allows navigation via arrow keys.
  - `execute_task()`: The core asynchronous function for executing a user's task. It handles:
    - Parsing file mentions in the user input to inject file content as context.
    - Streaming agent responses and updates from `agent.astream` (messages, tool calls, reasoning blocks, todo list updates).
    - Managing the display of a spinning status indicator (`console.status`).
    - Buffering and flushing text content to render markdown.
    - Tracking and displaying file operations (`FileOpTracker`).
    - Handling `__interrupt__` events from the agent, which trigger HITL approval prompts via `prompt_for_tool_approval()`.
    - Managing `auto_approve` functionality, where tool calls are automatically approved without user interaction.
    - Gracefully handling `KeyboardInterrupt` and `asyncio.CancelledError` for user-initiated interruptions.

## 3. Architecture & Data Flow

```mermaid
graph TD
    User[User Input] --> CLI_MAIN[main.py: cli_main()]
    CLI_MAIN --> ParseArgs[main.py: parse_args()]

    subgraph CLI Commands
        ParseArgs -- "Special Commands" --> ListAgents[agent.py: list_agents()]
        ParseArgs -- "Special Commands" --> ResetAgent[agent.py: reset_agent()]
        ParseArgs -- "Special Commands" --> SkillsCmd[skills.py: execute_skills_command()]
    end

    ParseArgs -- "Interactive Mode" --> MainAsync[main.py: main()]
    MainAsync -- "Create Model" --> CreateModel[config.py: create_model()]

    subgraph Sandbox Management
        MainAsync -- "Sandbox Type" --> CreateSandbox[sandbox_factory.py: create_sandbox()]
        CreateSandbox -- "Sandbox Backend" --> RunAgentSession[main.py: _run_agent_session()]
    end

    MainAsync -- "No Sandbox" --> RunAgentSession
    RunAgentSession -- "Create Agent" --> CreateCLIAgent[agent.py: create_cli_agent()]

    subgraph Agent Creation (create_cli_agent)
        CreateCLIAgent -- "Middleware Config" --> AgentMemoryMW[agent_memory.py: AgentMemoryMiddleware]
        CreateCLIAgent -- "Middleware Config" --> SkillsMW[skills.py: SkillsMiddleware]
        CreateCLIAgent -- "Middleware Config (Local Only)" --> ShellMW[shell.py: ShellMiddleware]
        CreateCLIAgent -- "Backend Config" --> CompositeBackend[deepagents.backends: CompositeBackend]
        CreateCLIAgent -- "Interrupt Config" --> InterruptOn[agent.py: _add_interrupt_on()]
    end

    CreateCLIAgent --> SimpleCLI[main.py: simple_cli()]
    SimpleCLI --> PromptSession[input.py: create_prompt_session()]
    PromptSession --> UserInput[User Input Field]
    UserInput -- "Text" --> HandleCmd[commands.py: handle_command()]
    UserInput -- "Text (!bash)" --> ExecuteBash[commands.py: execute_bash_command()]
    HandleCmd -- "Agent Input" --> ExecuteTask[execution.py: execute_task()]
    ExecuteBash -- "Agent Input" --> ExecuteTask

    subgraph Task Execution (execute_task)
        ExecuteTask -- "Stream Agent Response" --> AgentStream[Agent.astream()]
        AgentStream -- "Tool Call Chunks/Messages" --> DisplayTool[execution.py]
        AgentStream -- "Interrupt" --> PromptApproval[execution.py: prompt_for_tool_approval()]
        PromptApproval -- "User Decision" --> AgentStream[Resume Agent]
        AgentStream -- "Text/Markdown" --> ConsoleOutput[Console Output]
        AgentStream -- "Todos" --> RenderTodoList[ui.py]
        AgentStream -- "File Operations" --> RenderFileOp[ui.py]
    end

    DisplayTool --> ConsoleOutput
    RenderTodoList --> ConsoleOutput
    RenderFileOp --> ConsoleOutput

    AgentStream -- "Final Response" --> ConsoleOutput
```

## 4. Code Deep Dive

### `libs/deepagents-cli/deepagents_cli/main.py` - `simple_cli` loop (excerpt)
This snippet illustrates the core interactive loop, handling user input, command dispatch, and task execution.
```python
async def simple_cli(
    agent,
    assistant_id: str | None,
    session_state,
    baseline_tokens: int = 0,
    backend=None,
    sandbox_type: str | None = None,
    setup_script_path: str | None = None,
    no_splash: bool = False,
) -> None:
    # ... (initialization and splash screen)

    while True:
        try:
            user_input = await session.prompt_async()
            # ... (exit hint handling)
            user_input = user_input.strip()
        except EOFError:
            break
        except KeyboardInterrupt:
            console.print(
                "\nGoodbye!", style=COLORS["primary"]
            )
            break

        if not user_input:
            continue

        # Check for slash commands first
        if user_input.startswith("/ commenced "):
            result = handle_command(user_input, agent, token_tracker)
            if result == "exit":
                console.print(
                    "\nGoodbye!", style=COLORS["primary"]
                )
                break
            if result:
                # Command was handled, continue to next input
                continue

        # Check for bash commands (!)
        if user_input.startswith("!"):
            execute_bash_command(user_input)
            continue

        # Handle regular quit keywords
        if user_input.lower() in ["quit", "exit", "q"]:
            console.print(
                "\nGoodbye!", style=COLORS["primary"]
            )
            break

        await execute_task(
            user_input, agent, assistant_id, session_state, token_tracker, backend=backend
        )
```

### `libs/deepagents-cli/deepagents_cli/agent_memory.py` - `AgentMemoryMiddleware` `wrap_model_call` (excerpt)
This shows how the `AgentMemoryMiddleware` dynamically modifies the system prompt to include long-term memory before the LLM call.
```python
class AgentMemoryMiddleware(AgentMiddleware):
    # ... (other methods)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        system_prompt = self._build_system_prompt(request)
        return handler(request.override(system_prompt=system_prompt))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        system_prompt = self._build_system_prompt(request)
        return await handler(request.override(system_prompt=system_prompt))
```

### `libs/deepagents-cli/deepagents_cli/execution.py` - `prompt_for_tool_approval` (excerpt)
This is a critical section for human-in-the-loop interaction, displaying a rich prompt and capturing user decisions for tool execution.
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
            sys.stdout.write("\033[?25l")  # Hide cursor
            sys.stdout.flush()

            first_render = True

            while True:
                if not first_render:
                    sys.stdout.write("\033[3A\r")  # Move cursor up

                first_render = False

                for i, option in enumerate(options):
                    sys.stdout.write("\r\033[K")  # Clear line

                    if i == selected:
                        sys.stdout.write(f"[bold green]> {option} [/bold green]")
                    else:
                        sys.stdout.write(f"  {option}")

                sys.stdout.flush()

                char = sys.stdin.read(1)

                if char == "\x1b":  # ESC sequence (arrow keys)
                    next1 = sys.stdin.read(1)
                    next2 = sys.stdin.read(1)
                    if next1 == "[":
                        if next2 == "B":  # Down arrow
                            selected = (selected + 1) % len(options)
                        elif next2 == "A":  # Up arrow
                            selected = (selected - 1) % len(options)
                elif char in {"\r", "\n"}:  # Enter
                    sys.stdout.write("\r\n")
                    break
                elif char == "\x03":  # Ctrl+C
                    sys.stdout.write("\r\n")
                    raise KeyboardInterrupt
                elif char.lower() == "a":
                    selected = 0
                    sys.stdout.write("\r\n")
                    break
                elif char.lower() == "r":
                    selected = 1
                    sys.stdout.write("\r\n")
                    break

        finally:
            sys.stdout.write("\033[?25h")  # Show cursor
            sys.stdout.flush()
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    except (termios.error, AttributeError):
        # Fallback for non-Unix systems
        console.print(
            "\n[bold yellow]⚠️  Tool Action Requires Approval[/bold yellow]"
        )
        choice = console.input("[bold]Approve? (y/n/a - yes/no/auto-approve all): [/bold]").lower()
        if choice == "y":
            selected = 0
        elif choice == "n":
            selected = 1
        elif choice == "a":
            selected = 2
        else:
            console.print("[red]Invalid choice. Rejecting by default.[/red]")
            selected = 1

    # Return decision based on selection
    if selected == 0:
        return ApproveDecision(type="approve")
    if selected == 1:
        return RejectDecision(type="reject", message="User rejected the command")
    return {"type": "auto_approve_all"}

```

## 5. Integration Points
- **Dependencies**:
  - `main.py` depends on `deepagents.backends.protocol`, `deepagents_cli.agent`, `deepagents_cli.commands`, `deepagents_cli.config`, `deepagents_cli.execution`, `deepagents_cli.input`, `deepagents_cli.integrations.sandbox_factory`, `deepagents_cli.skills`, `deepagents_cli.tools`, and `deepagents_cli.ui`.
  - `agent.py` depends on `deepagents`, `deepagents.backends`, `langchain.agents.middleware`, `langchain_core.language_models`, `langgraph.checkpoint.memory`, `langgraph.pregel`, `langgraph.runtime`, `deepagents_cli.agent_memory`, `deepagents_cli.config`, `deepagents_cli.integrations.sandbox_factory`, `deepagents_cli.shell`, and `deepagents_cli.skills`.
  - `agent_memory.py` depends on `langchain.agents.middleware`, `langgraph.runtime`, and `deepagents_cli.config`.
  - `commands.py` depends on `langgraph.checkpoint.memory`, `deepagents_cli.config`, and `deepagents_cli.ui`.
  - `execution.py` depends on `langchain.agents.middleware.human_in_the_loop`, `langchain_core.messages`, `langgraph.types`, `pydantic`, `rich`, `rich.markdown`, `rich.panel`, `deepagents_cli.config`, `deepagents_cli.file_ops`, `deepagents_cli.input`, and `deepagents_cli.ui`.
- **Dependents**:
  - `main.py` is the entry point for the entire CLI application.
  - `agent.py`'s `create_cli_agent` is a core function called by `main.py` to set up the agent.
  - `agent_memory.py`'s `AgentMemoryMiddleware` is used by `agent.py` when constructing the agent.
  - `commands.py`'s `handle_command` and `execute_bash_command` are called by `main.py` during the interactive loop.
  - `execution.py`'s `execute_task` is called by `main.py` to run agent tasks, and `prompt_for_tool_approval` is used by `execute_task` for HITL.
