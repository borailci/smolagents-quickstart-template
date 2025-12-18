# Interactive CLI and Human-in-the-Loop in DeepAgents

## 1. Goal
In this tutorial, you will learn how to effectively use the `deepagents-cli` for interactive agent interaction, focusing on essential slash commands and the crucial Human-in-the-Loop (HITL) approval process for sensitive operations. By the end, you will be comfortable navigating the CLI, managing agent state, and securely approving tool calls.

## 2. Prerequisites
- Basic understanding of command-line interfaces.
- A working installation of the DeepAgents framework.
- Familiarity with the concept of AI agents and their ability to use tools.

## 3. Architecture
The `deepagents-cli` is the primary interface for users to interact with the DeepAgents framework. It acts as a bridge between the user and the core agent logic, facilitating command execution, state management, and human intervention when necessary.

```mermaid
graph TD
    User[User] --> CLI[deepagents-cli]
    CLI -->|Text Input & Slash Commands| AgentCore[DeepAgents Core]
    AgentCore -->|Tool Calls (e.g., write_file, shell)| CLI
    CLI -->|Human-in-the-Loop Approval| User
    CLI -->|Output & Status| User
```

## 4. Using Slash Commands
The `deepagents-cli` provides several built-in slash commands to help you manage your interactive session and understand agent behavior. These commands are entered directly into the CLI prompt.

### `/help` - Get Assistance
To view a list of available commands and their descriptions, use `/help`. This is useful when you need a quick reminder of what you can do within the CLI.

```bash
$ deepagents-cli
> /help
```

### `/clear` - Reset the Conversation
Use `/clear` to clear the current conversation history. This can be helpful when you want to start fresh without restarting the entire CLI session.

```bash
> /clear
```

### `/tokens` - Monitor Token Usage
To keep track of the tokens consumed by the agent's interactions, use `/tokens`. This provides insights into the cost and verbosity of your agent's operations.

```bash
> /tokens
```

## 5. Human-in-the-Loop (HITL) Approval

One of the most critical features of the `deepagents-cli` is its robust Human-in-the-Loop (HITL) mechanism. This ensures that sensitive agent actions, such as executing shell commands or writing to files, are explicitly approved by a human user before they are performed. This prevents unintended consequences and provides a crucial layer of security and control.

### Why HITL is Important
AI agents, especially when equipped with powerful tools, can potentially make drastic changes to your system or data. HITL acts as a safeguard, allowing you to review and sanction proposed actions, maintaining human oversight over critical operations.

### How HITL Works
When an agent proposes a sensitive tool call, the CLI will pause execution and present you with an interactive prompt. This prompt details the proposed action and often includes a diff (difference) of any file modifications. You then have the option to:

- **Approve**: Allow the agent to proceed with the action.
- **Reject**: Prevent the agent from performing the action.
- **Auto-Accept**: Approve this type of action automatically for the current session (use with caution).

### Example: Approving a File Modification
Consider an agent tasked with refactoring a Python file. When the agent attempts to modify the file, the CLI will display a prompt similar to this:

```
⚠️ Tool Action Requires Approval
> edit_file(utils.py)
--- a/utils.py
+++ b/utils.py
@@ -1,3 +1,7 @@
 import random
 
def generate_id():
-  return random.randint(0, 1000)
+    return f"id_{random.randint(0, 1000)}"
+
+def calculate_average(numbers):
+    return sum(numbers) / len(numbers)

[Approve] | Reject | Auto-Accept
```

In this example:
- The `⚠️ Tool Action Requires Approval` warning clearly indicates a pending action.
- `> edit_file(utils.py)` shows the specific tool being called and its argument.
- The subsequent lines display a color-coded diff:
    - Lines starting with `---` or `+++` indicate the original and new files.
    - Lines starting with `-` (red) are removed lines.
    - Lines starting with `+` (green) are added lines.
    - Lines without a prefix are unchanged context lines.

To approve this change, you would typically type `Approve` (or its designated shortcut) and press Enter.

## 6. Skills Management Commands

Beyond interaction with the agent, the `deepagents-cli` also provides commands for managing the agent's capabilities, known as "skills". Skills are essentially structured instructions or custom tools that extend the agent's functionality.

### `skills list`
To see all the skills currently available to your agent, use the `skills list` command.

```bash
> skills list
```

### `skills create`
To add a new skill to your agent, you can use `skills create`. This typically involves creating a new Markdown file with YAML frontmatter defining the skill's properties and instructions.

```bash
> skills create --name my_new_skill --file_path ./my_new_skill.md
```

## 7. Conclusion
You've now learned how to effectively interact with the `deepagents-cli`, utilizing its slash commands for session management and understanding the critical role of Human-in-the-Loop approval for secure and controlled agent operations. The CLI empowers you to not only guide your agents but also to manage their capabilities, making it a powerful tool for developing and deploying AI solutions with confidence. Experiment with these features to gain a deeper understanding of how to build and control intelligent agents.