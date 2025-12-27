
# DeepAgents Tutorial Plan

This document outlines a series of tutorials for learning the DeepAgents framework. The tutorials are designed to be followed in order, providing a progressive learning path from basic usage to advanced concepts.

---

### Tutorial 1: Getting Started with the DeepAgents CLI

-   **Filename**: `01-getting-started-cli.md`
-   **Description**: A beginner's guide to installing and running the DeepAgents command-line interface. This tutorial will cover the basic interactive mode, how to ask for help, and how to exit the application. It will provide a gentle introduction to the agent's capabilities.
-   **Knowledge Base Files**:
    -   `executive_summary.md`
    -   `CLI Main.md`
-   **Source Files**:
    -   `libs/deepagents-cli/pyproject.toml` (for installation/package name)
    -   `libs/deepagents-cli/deepagents_cli/main.py` (for CLI entry point and commands)

### Tutorial 2: Your First Deep Agent

-   **Filename**: `02-first-deep-agent.md`
-   **Description**: Learn the fundamentals of the `deepagents` library by creating a simple, non-CLI agent. This tutorial will introduce the `create_deep_agent` factory, the concept of middleware, and how to interact with an agent programmatically.
-   **Knowledge Base Files**:
    -   `DeepAgents Core.md`
-   **Source Files**:
    -   `libs/deepagents/pyproject.toml` (for installation/package name)
    -   `libs/deepagents/deepagents/factory.py` (for the core agent creation logic)

### Tutorial 3: Understanding Agent Memory

-   **Filename**: `03-agent-memory.md`
-   **Description**: An in-depth look at the hierarchical memory system. This tutorial will explain how the CLI agent persists and recalls information across sessions, covering both the global and project-specific memory stores. Readers will learn how to inspect and manage the agent's memory.
-   **Knowledge Base Files**:
    -   `CLI Agent.md`
-   **Source Files**:
    -   `libs/deepagents-cli/deepagents_cli/agent.py` (specifically `AgentMemoryMiddleware`)

### Tutorial 4: Mastering Agent Tools

-   **Filename**: `04-agent-tools.md`
-   **Description**: Explore the suite of tools available to DeepAgents. This tutorial will provide practical examples of using tools for file system operations, web searches, and running shell commands. It will emphasize the power and flexibility these tools provide.
-   **Knowledge Base Files**:
    -   `CLI Integrations & Tools.md`
-   **Source Files**:
    -   `libs/deepagents-cli/deepagents_cli/integrations/tools/` (directory containing tool implementations)

### Tutorial 5: Human-in-the-Loop (HITL) for Safe Execution

-   **Filename**: `05-human-in-the-loop.md`
-   **Description**: A crucial tutorial on the Human-in-the-Loop (HITL) safety feature. This lesson will explain why HITL is important, how it works, and how to approve or deny agent actions. It will also touch on how to run the agent in an auto-approved mode for automated workflows.
-   **Knowledge Base Files**:
    -   `CLI Commands & Execution.md`
-   **Source Files**:
    -   `libs/deepagents-cli/deepagents_cli/commands.py` (where the HITL prompt is implemented)

### Tutorial 6: Secure Agent Execution with Harbor

-   **Filename**: `06-secure-execution-harbor.md`
-   **Description**: An advanced tutorial on running agents in a secure, isolated sandbox environment using the Harbor backend. This will cover the setup and configuration required to use Harbor and the benefits of sandboxed execution for safety and reproducibility.
-   **Knowledge Base Files**:
    -   `Harbor Backend.md`
-   **Source Files**:
    -   `libs/harbor/pyproject.toml`
    -   `libs/harbor/harbor/backend.py` (the `HarborSandboxBackend` implementation)
    -   `libs/deepagents-cli/deepagents_cli/main.py` (to see how the backend is selected and configured)

