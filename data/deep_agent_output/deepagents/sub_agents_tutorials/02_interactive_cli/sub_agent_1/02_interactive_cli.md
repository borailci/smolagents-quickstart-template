'''
# Interactive Development with the `deepagents-cli`

Welcome to the next generation of development! The `deepagents-cli` is a powerful, interactive command-line tool that brings an AI coding assistant directly into your terminal. This tutorial will guide you through the essentials of using the CLI, focusing on its interactive shell, the critical Human-in-the-Loop (HITL) workflow, and the sandboxing features that keep your projects safe.

## The Interactive Shell

To get started, simply run the `deepagents-cli` in your terminal. You'll be greeted by the interactive shell, ready to accept your instructions.

```bash
npm install -g @deep/agents-cli
deepagents-cli
```

Once in the shell, you can interact with the agent conversationally. You can ask it to write code, refactor files, or even answer technical questions. The shell supports multi-line input, command history, and other familiar terminal features.

## Human-in-the-Loop (HITL): Your Safety Net

One of the most important features of the `deepagents-cli` is the Human-in-the-Loop (HITL) workflow. By default, the agent cannot make changes to your filesystem without your explicit approval. When the agent wants to perform a sensitive action, like writing to a file, the CLI will intercept the request and prompt you for confirmation.

This gives you complete control over your codebase and prevents the agent from making unwanted changes. You can approve or deny any action, ensuring that the AI works for you, not the other way around.

## A Practical Example: Refactoring Code

Let's walk through a common development task: refactoring a Python file. Suppose you have a file named `utils.py` with some poorly organized code:

```python
# utils.py

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b


def greet(name):
    print(f"Hello, {name}")
```

You can instruct the agent to refactor this file to be more modular. For example, you could ask:

> "Refactor `utils.py` to separate the math functions from the greeting function. Create a new file `greetings.py` for the `greet` function."

The agent will read `utils.py`, analyze the code, and propose a set of changes. When it's ready to write the new files, you'll see a HITL prompt:

```
🤖 The agent wants to write to the following files:

  - utils.py
  - greetings.py

Do you want to allow this? [y/N] y
```

After you approve, the agent will perform the refactoring. Your `utils.py` will now contain only the math functions, and a new `greetings.py` file will be created.

## The `FilesystemBackend` and `virtual_mode`

The agent's ability to interact with your files is powered by the `FilesystemBackend`. This component gives the agent the tools it needs to read, write, and list files. However, for safety, this access is almost always restricted by `virtual_mode`.

When `virtual_mode` is enabled, the agent's filesystem access is confined to a specific root directory. It cannot read or write files outside of this designated workspace. This creates a secure sandbox, preventing the agent from accessing sensitive system files or other projects on your machine.

Here's a diagram illustrating how this works:

```mermaid
graph TD
    A[Developer] --> B{deepagents-cli};
    B --> C[AI Agent];
    C --> D{FilesystemBackend (virtual_mode)};
    D --> E["/path/to/project"];
    D -.-> F(Other Files);
    subgraph "Workspace"
        E
    end
    subgraph "Your Computer"
        F
    end

    style F fill:#f77,stroke:#333,stroke-width:2px
```

This sandboxing is a core principle of the DeepAgents ecosystem, ensuring that you can leverage the power of AI without compromising on security.

## Advanced Usage

The `deepagents-cli` has many other features to explore:

*   **Shell commands:** Use the `/shell` command to execute shell commands directly within the interactive session. For example: `/shell ls -l`.
*   **Bash commands:** You can also run bash commands by prefixing them with `!`. For example: `!pip install numpy`.
*   **Help:** The `/help` command provides a list of all available commands and their descriptions.
*   **Auto-approve:** For trusted tasks, you can use the `--auto-approve` flag to disable HITL and allow the agent to run without prompts.

## Conclusion

The `deepagents-cli` is a versatile and secure tool for interactive AI-assisted development. Its conversational shell, combined with the safety of the HITL workflow and the `FilesystemBackend`'s `virtual_mode`, provides a powerful and safe environment for you to build, refactor, and innovate. Start using the `deepagents-cli` today and experience a new way of coding.
'''