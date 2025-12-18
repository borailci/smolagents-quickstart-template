# DeepAgents CLI Skills and Tools Analysis

## 1. Overview
This set of modules (`commands.py`, `load.py`, `middleware.py` within `skills`, `tools.py`, and `ui.py`) collectively provides the core functionality for managing agent skills and integrating external tools within the DeepAgents CLI. It enables agents to discover, create, utilize, and display information about specialized "skills" (structured markdown files with instructions and supporting files) and external tools (like web search and HTTP requests). The design emphasizes a "progressive disclosure" model for skills, where agents are first presented with metadata and only access full instructions when needed. The `ui.py` module handles the user interface aspects, including formatting tool outputs and providing interactive help.

## 2. File-by-File Analysis

### `libs/deepagents-cli/deepagents_cli/skills/commands.py`
- **Purpose**: This module defines the command-line interface for managing DeepAgents skills. It provides subcommands for listing, creating, and displaying detailed information about skills.
- **Key Components**:
  - `_validate_name(name: str)`: Validates skill and agent names to prevent path traversal and enforce naming conventions (alphanumeric, hyphens, underscores).
  - `_validate_skill_path(skill_dir: Path, base_dir: Path)`: Ensures that a skill directory is safely contained within its designated base directory, protecting against malicious path manipulations.
  - `_list(agent: str, *, project: bool = False)`: Lists available skills, differentiating between user-level and project-level skills. It uses `deepagents_cli.skills.load.list_skills` to retrieve skill metadata.
  - `_create(skill_name: str, agent: str, project: bool = False)`: Creates a new skill directory and populates it with a template `SKILL.md` file. It enforces name and path validation.
  - `_info(skill_name: str, *, agent: str = "agent", project: bool = False)`: Displays detailed information about a specific skill, including its full `SKILL.md` content and any supporting files.
  - `setup_skills_parser(subparsers: Any)`: Configures an `argparse` parser for the `skills` subcommand, adding `list`, `create`, and `info` as sub-commands with their respective arguments.
  - `execute_skills_command(args: argparse.Namespace)`: Dispatches the execution to the appropriate skill management function based on the parsed command-line arguments.

### `libs/deepagents-cli/deepagents_cli/skills/load.py`
- **Purpose**: This module is responsible for scanning directories, parsing `SKILL.md` files, and loading skill metadata. It implements security checks to prevent path traversal.
- **Key Components**:
  - `SkillMetadata(TypedDict)`: Defines the structure for skill metadata, including `name`, `description`, `path` (to `SKILL.md`), and `source` (`user` or `project`).
  - `MAX_SKILL_FILE_SIZE`: A constant to prevent loading excessively large `SKILL.md` files, mitigating potential denial-of-service attacks.
  - `_is_safe_path(path: Path, base_dir: Path) -> bool`: A crucial security function that verifies if a given `path` is safely contained within `base_dir`, resolving symlinks and preventing directory traversal.
  - `_parse_skill_metadata(skill_md_path: Path, source: str) -> SkillMetadata | None`: Parses the YAML frontmatter from a `SKILL.md` file to extract `name` and `description`. Includes checks for file size and required fields.
  - `_list_skills(skills_dir: Path, source: str) -> list[SkillMetadata]`: Scans a specified directory for skill subdirectories, finds `SKILL.md` files, applies safety checks, and parses their metadata. This is an internal helper for `list_skills`.
  - `list_skills(*, user_skills_dir: Path | None = None, project_skills_dir: Path | None = None) -> list[SkillMetadata]`: The main function for skill discovery. It loads skills from both user-level and project-level directories, with project skills overriding user skills in case of name conflicts.

### `libs/deepagents-cli/deepagents_cli/skills/middleware.py`
- **Purpose**: This module provides a middleware component that integrates agent skills into the agent's system prompt, enabling "progressive disclosure" of skill instructions. It prepares skill metadata for the agent and injects relevant instructions into the prompt.
- **Key Components**:
  - `SkillsState(AgentState)`: Extends the base agent state to include `skills_metadata`, which stores the loaded skill information.
  - `SkillsStateUpdate(TypedDict)`: Defines the structure for updates to the `SkillsState`.
  - `SKILLS_SYSTEM_PROMPT`: A multi-line string constant that defines the template for the skills system documentation injected into the agent's system prompt. This prompt guides the agent on how to use skills effectively.
  - `SkillsMiddleware(AgentMiddleware)`: The core middleware class. Its responsibilities include:
    - Initializing with paths to user-level and project-level skills directories.
    - `_format_skills_locations()`: Formats the paths where skills are located for display in the system prompt.
    - `_format_skills_list(skills: list[SkillMetadata])`: Formats the list of available skills (name and description) for injection into the system prompt, grouped by source.
    - `before_agent(state: SkillsState, runtime: Runtime)`: This method is called at the beginning of an agent's session. It uses `deepagents_cli.skills.load.list_skills` to discover and load all available skills and updates the agent's state with this metadata. It reloads skills on every new interaction to capture changes.
    - `wrap_model_call(request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse])`: This method intercepts model calls. It retrieves the skill metadata from the agent's state, formats it into the `SKILLS_SYSTEM_PROMPT`, and injects this dynamically generated skills documentation into the model's system prompt before the call is made. This ensures the agent is always aware of its available skills and how to use them.
    - `awrap_model_call`: Asynchronous version of `wrap_model_call`.

### `libs/deepagents-cli/deepagents_cli/tools.py`
- **Purpose**: This module defines custom tools that the DeepAgents CLI agent can use, such as making HTTP requests and performing web searches.
- **Key Components**:
  - `tavily_client`: An instance of `TavilyClient`, initialized if the `TAVILY_API_KEY` environment variable is set. This client is used for web search functionality.
  - `http_request(url: str, method: str = "GET", ...)`: A tool that allows the agent to make arbitrary HTTP requests. It handles various HTTP methods, headers, data, parameters, and timeouts, returning a structured dictionary with response details or error information.
  - `web_search(query: str, max_results: int = 5, ...)`: A tool for performing web searches using the Tavily API. It takes a query and other optional parameters, returning a list of search results including title, URL, and content excerpts. It includes an important note for the agent to synthesize information and cite sources.
  - `fetch_url(url: str, timeout: int = 30)`: A tool to fetch content from a given URL and convert its HTML content into a clean Markdown format. This simplifies the processing of web pages for the agent.

### `libs/deepagents-cli/deepagents_cli/ui.py`
- **Purpose**: This module provides utilities for rendering and displaying information to the user in the DeepAgents CLI, including formatted tool outputs, file operation summaries, diffs, and interactive help messages.
- **Key Components**:
  - `truncate_value(value: str, max_length: int = MAX_ARG_LENGTH)`: Helper function to truncate long strings for display purposes.
  - `format_tool_display(tool_name: str, tool_args: dict) -> str`: Formats tool calls for concise display in the CLI. It uses tool-specific logic to show the most relevant arguments (e.g., just the filename for file operations, or the query for web search).
  - `format_tool_message_content(content: Any) -> str`: Converts `ToolMessage` content into a printable string, handling various content types (strings, lists, JSON).
  - `TokenTracker`: A class to track token usage (input and output) across the conversation, providing insights into the agent's context size and cost.
  - `render_todo_list(todos: list[dict])`: Renders a list of to-do items as a rich `Panel` with checkboxes, providing a structured way to display tasks.
  - `_format_line_span(start: int | None, end: int | None) -> str`: Helper for formatting line number spans in file operation summaries.
  - `render_file_operation(record: FileOperationRecord)`: Renders a concise summary of filesystem tool calls (read, write, edit), including metrics like lines read/written/added/removed.
  - `render_diff(record: FileOperationRecord)`: Renders a file diff associated with a `FileOperationRecord`.
  - `_wrap_diff_line(...)`: Internal helper for `format_diff_rich` to wrap long diff lines gracefully.
  - `format_diff_rich(diff_lines: list[str]) -> str`: Formats raw diff lines into a rich-formatted string with line numbers and syntax highlighting (additions, deletions, context).
  - `render_diff_block(diff: str, title: str)`: Renders a formatted diff within a console block, using `format_diff_rich`.
  - `show_interactive_help()`: Displays a list of interactive commands and editing features available in the CLI.
  - `show_help()`: Displays general help information for the DeepAgents CLI, including usage, options, examples, memory, and storage details.

## 3. Architecture & Data Flow

```mermaid
graph TD
    CLI_User[CLI User] --> |Commands| CLI_Entrypoint(deepagents CLI)

    subgraph Skills Management
        CLI_Entrypoint --> |"skills list/create/info"| CommandsPy(skills/commands.py)
        CommandsPy --> |Uses| LoadPy(skills/load.py)
        LoadPy --> |Reads SKILL.md| Filesystem[Filesystem (SKILL.md)]
        Filesystem --> |Provides Skill Metadata| LoadPy
        LoadPy --> |Returns SkillMetadata| CommandsPy
        CommandsPy --> |Displays Info| UIPy(ui.py)
    end

    subgraph Agent Interaction
        CLI_Entrypoint --> Agent[DeepAgents Agent (LangChain/LangGraph)]
        Agent --> MiddlewarePy(skills/middleware.py)
        MiddlewarePy --> |Loads Skills (once/session)| LoadPy
        LoadPy --> |Returns SkillMetadata| MiddlewarePy
        MiddlewarePy --> |Injects Skill Docs into System Prompt| Agent
        Agent --> |Tool Call (e.g., web_search)| ToolsPy(tools.py)
        ToolsPy --> |External APIs (Tavily, Requests)| External_APIs[External APIs]
        External_APIs --> |Results| ToolsPy
        ToolsPy --> |Tool Output| Agent
        Agent --> |Displays to User| UIPy
    end

    UIPy --> CLI_User

    style CommandsPy fill:#f9f,stroke:#333,stroke-width:2px
    style LoadPy fill:#ccf,stroke:#333,stroke-width:2px
    style MiddlewarePy fill:#bbf,stroke:#333,stroke-width:2px
    style ToolsPy fill:#dfd,stroke:#333,stroke-width:2px
    style UIPy fill:#fcf,stroke:#333,stroke-width:2px
```

**Data Flow Explanation:**
1.  **CLI User Interaction**: The user interacts with the `deepagents` CLI, invoking commands like `deepagents skills list` or interacting with the agent itself.
2.  **Skills Command Execution**: When `deepagents skills` commands are run, `commands.py` acts as the entry point. It uses `load.py` to discover and parse `SKILL.md` files from the filesystem.
3.  **Skill Loading (`load.py`)**: This module is critical for securely reading `SKILL.md` files, parsing their YAML frontmatter for metadata, and returning a structured `SkillMetadata` list. It performs path validation to prevent security vulnerabilities.
4.  **Agent Middleware (`middleware.py`)**: Before the agent begins its work, the `SkillsMiddleware` loads the available skills via `load.py`. This metadata (name, description, path) is then injected into the agent's system prompt. This allows the agent to be aware of its capabilities without having to read the full skill instructions immediately (progressive disclosure).
5.  **Agent Tool Usage (`tools.py`)**: When the agent decides a tool is necessary (e.g., `web_search` or `http_request`), it calls functions defined in `tools.py`. These tools interact with external APIs (like Tavily for web search or generic HTTP endpoints) and return structured results to the agent.
6.  **User Interface (`ui.py`)**: `ui.py` is responsible for formatting all outputs for the CLI user, including:
    *   Formatted skill lists and info from `commands.py`.
    *   Cleanly displayed tool outputs from the agent.
    *   Summaries and diffs for file operations.
    *   Interactive help messages and token usage tracking.

## 4. Code Deep Dive

### Skill Name Validation (`commands.py`)
The `_validate_name` function is crucial for maintaining security and consistency in skill and agent naming. It prevents common vulnerabilities like path traversal.
```python
def _validate_name(name: str) -> tuple[bool, str]:
    """Validate name to prevent path traversal attacks.

    Args:
        name: The name to validate

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    # Check for empty or whitespace-only names
    if not name or not name.strip():
        return False, "cannot be empty"

    # Check for path traversal sequences
    if ".." in name:
        return False, "name cannot contain '..' (path traversal)"

    # Check for absolute paths
    if name.startswith(("/", "\\")):
        return False, "name cannot be an absolute path"

    # Check for path separators
    if "/" in name or "\\" in name:
        return False, "name cannot contain path separators"

    # Only allow alphanumeric, hyphens, underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return False, "name can only contain letters, numbers, hyphens, and underscores"

    return True, ""
```

### Safe Path Resolution (`load.py`)
To prevent directory traversal attacks, `_is_safe_path` in `load.py` resolves paths to their canonical form and ensures the target path is a subpath of the base directory. This is vital when dealing with user-provided skill directories.
```python
def _is_safe_path(path: Path, base_dir: Path) -> bool:
    """Check if a path is safely contained within base_dir.

    This prevents directory traversal attacks via symlinks or path manipulation.
    The function resolves both paths to their canonical form (follows symlinks)
    and verifies that the target path is within the base directory.

    Args:
        path: The path to validate
        base_dir: The base directory that should contain the path

    Returns:
        True if the path is safely within base_dir, False otherwise
    """
    try:
        # Resolve both paths to their canonical form (follows symlinks)
        resolved_path = path.resolve()
        resolved_base = base_dir.resolve()

        # Check if the resolved path is within the base directory
        resolved_path.relative_to(resolved_base)
        return True
    except ValueError:
        return False
    except (OSError, RuntimeError):
        return False
```

### Skills Injection into System Prompt (`middleware.py`)
The `wrap_model_call` method in `SkillsMiddleware` demonstrates how the dynamically loaded skill information is integrated into the agent's operational context.
```python
def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Inject skills documentation into the system prompt.

        This runs on every model call to ensure skills info is always available.

        Args:
            request: The model request being processed.
            handler: The handler function to call with the modified request.

        Returns:
            The model response from the handler.
        """
        # Get skills metadata from state
        skills_metadata = request.state.get("skills_metadata", [])

        # Format skills locations and list
        skills_locations = self._format_skills_locations()
        skills_list = self._format_skills_list(skills_metadata)

        # Format the skills documentation
        skills_section = self.system_prompt_template.format(
            skills_locations=skills_locations,
            skills_list=skills_list,
        )

        if request.system_prompt:
            system_prompt = request.system_prompt + "\n\n" + skills_section
        else:
            system_prompt = skills_section

        return handler(request.override(system_prompt=system_prompt))
```

### Formatted Tool Display (`ui.py`)
The `format_tool_display` function in `ui.py` is a good example of how the CLI prioritizes user readability by intelligently summarizing complex tool arguments.
```python
def format_tool_display(tool_name: str, tool_args: dict) -> str:
    """Format tool calls for display with tool-specific smart formatting.

    Shows the most relevant information for each tool type rather than all arguments.

    Args:
        tool_name: Name of the tool being called
        tool_args: Dictionary of tool arguments

    Returns:
        Formatted string for display (e.g., "read_file(config.py)")
    """

    def abbreviate_path(path_str: str, max_length: int = 60) -> str:
        """Abbreviate a file path intelligently - show basename or relative path."""
        try:
            path = Path(path_str)
            if len(path.parts) == 1:
                return path_str
            try:
                rel_path = path.relative_to(Path.cwd())
                rel_str = str(rel_path)
                if len(rel_str) < len(path_str) and len(rel_str) <= max_length:
                    return rel_str
            except (ValueError, Exception):
                pass
            if len(path_str) <= max_length:
                return path_str
            return path.name
        except Exception:
            return truncate_value(path_str, max_length)

    if tool_name in ("read_file", "write_file", "edit_file"):
        path_value = tool_args.get("file_path")
        if path_value is None:
            path_value = tool_args.get("path")
        if path_value is not None:
            path = abbreviate_path(str(path_value))
            return f"{tool_name}({path})"

    elif tool_name == "web_search":
        if "query" in tool_args:
            query = str(tool_args["query"])
            query = truncate_value(query, 100)
            return f'{tool_name}("{query}")'

    # ... (other tool-specific formatting logic)

    # Fallback: generic formatting for unknown tools
    args_str = ", ".join(f"{k}={truncate_value(str(v), 50)}" for k, v in tool_args.items())
    return f"{tool_name}({args_str})"
```

## 5. Integration Points
- **Dependencies**:
  - `deepagents_cli.config`: Used across modules for settings, colors, and console output.
  - `deepagents_cli.skills.load`: Central for skill discovery and parsing, used by `commands.py` and `middleware.py`.
  - `argparse`: For CLI argument parsing (`commands.py`).
  - `re` (regular expressions), `pathlib.Path`: For path manipulation and validation across multiple modules.
  - `requests`, `markdownify`, `tavily`: External libraries for web functionality (`tools.py`).
  - `langchain.agents.middleware.types`, `langgraph.runtime`: Core components for agent middleware integration (`middleware.py`).
  - `rich`: For rich terminal output and UI elements (`ui.py`).

- **Dependents**:
  - The main DeepAgents CLI entrypoint (`cli.py`, not provided) would depend on `commands.py` for setting up CLI commands and `middleware.py` for integrating skills into the agent runtime.
  - Any module invoking agent tools would rely on the definitions in `tools.py`.
  - UI components throughout the CLI would use `ui.py` for consistent and readable output.