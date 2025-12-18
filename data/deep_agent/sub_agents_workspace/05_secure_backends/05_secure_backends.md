# Secure Backends and Remote Integrations

## 1. Goal
In this tutorial, you will learn how the DeepAgents framework provides secure and flexible backend operations, focusing on the `deepagents_backends` library and its role in routing file operations. We will explore the `SandboxBackendProtocol` for consistent execution environments and delve into using remote integrations like Modal and Daytona for sandboxed code execution. By the end, you will understand how to leverage these features for secure and scalable agent development.

## 2. Prerequisites
- Basic understanding of Python.
- Familiarity with command-line interfaces.
- An environment with the `deepagents-cli` installed.

## 3. Architecture
The DeepAgents framework separates backend operations from core agent logic, enabling secure and pluggable execution environments. The `CompositeBackend` acts as a router, directing file system operations to various backends (in-memory, local, or remote sandboxes) based on path prefixes. The `SandboxBackendProtocol` ensures a consistent interface for all sandbox implementations, abstracting away the complexities of different remote providers.

```mermaid
graph TD
    A[DeepAgents CLI] --> B{Agent Logic}
    B --> C[deepagents_backends]
    C --> D{CompositeBackend["CompositeBackend (Routes Operations)"]}
    D --> |"/workspace/*"| E[LocalBackend]
    D --> |"/memories/*"| F[InMemoryBackend]
    D --> |"Remote Sandbox e.g., /sandbox/*"| G[SandboxBackendProtocol]
    G --> H[ModalBackend]
    G --> I[DaytonaBackend]
    G --> J[RunloopBackend]
    H --> K[Modal SDK]
    I --> L[Daytona SDK]
    J --> M[Runloop API Client]

    subgraph Remote Integrations
        G
        H
        I
        J
        K
        L
        M
    end

    subgraph Local Backends
        E
        F
    end
```

## 4. Step 1: Understanding Pluggable Backends with `deepagents_backends`

The `deepagents_backends` library is the foundation for managing how your agents interact with their environment, particularly concerning file system operations and command execution. It introduces the concept of *pluggable backends*, allowing you to swap out storage and execution mechanisms without altering your agent's core logic.

### Why Pluggable Backends?

-   **Security**: By isolating file operations, you can restrict an agent's access to sensitive areas of your local machine. Remote sandboxes provide even stronger isolation.
-   **Flexibility**: Easily switch between different storage solutions (e.g., in-memory for testing, local disk for development, remote for production) or execution environments (e.g., local shell, Modal, Daytona).
-   **Consistency**: The `SandboxBackendProtocol` ensures that regardless of the underlying execution environment (local or remote sandbox), the interface for interacting with it remains the same.

## 5. Step 2: Routing Operations with `CompositeBackend`

The `CompositeBackend` is a powerful component that acts as a router for file operations. It allows you to configure different backends for different parts of your agent's workspace based on path prefixes.

For example, you might want:
-   Operations on `/workspace/*` to go to your local file system.
-   Operations on `/memories/*` to be handled by an in-memory backend (ephemeral).
-   Operations targeting `/sandbox/*` to be routed to a remote sandboxed environment.

This setup provides fine-grained control over where and how your agent stores and accesses data, enhancing both security and modularity.

## 6. Step 3: Secure Execution Environments with `SandboxBackendProtocol`

The `SandboxBackendProtocol` is a crucial abstraction that defines a consistent interface for secure and isolated code execution environments. It specifies methods for `execute`, `upload_files`, and `download_files`, ensuring that any backend implementing this protocol can be used interchangeably for sandboxed operations.

This protocol is implemented by various remote integration backends, such as `ModalBackend`, `DaytonaBackend`, and `RunloopBackend`, allowing the DeepAgents CLI to communicate with these services without needing to know their specific SDKs or APIs.

## 7. Step 4: Remote Integrations for Sandboxed Code Execution

DeepAgents supports integration with remote sandboxing platforms like Modal, Daytona, and Runloop. These platforms provide isolated, cloud-based environments where your agent's code can be executed securely, preventing potential harm to your local system.

### Modal
Modal provides serverless, cloud-based environments for running your code. The `ModalBackend` integrates with the Modal SDK to allow your agent to execute commands and manage files within a Modal sandbox.

### Daytona
Daytona offers development environments in the cloud. The `DaytonaBackend` enables your agent to interact with Daytona sandboxes, providing secure command execution and file transfer capabilities.

By leveraging these remote integrations, you can:
-   **Isolate risky operations**: Run potentially unsafe or untrusted code in a disposable, isolated environment.
-   **Scale execution**: Offload heavy computations to cloud resources.
-   **Maintain consistency**: Ensure that your agent's execution environment is consistent, regardless of your local setup.

## 8. Step 5: Launching the CLI with a Remote Sandbox

To connect the `deepagents-cli` to a remote sandbox, you use the `--sandbox` flag, specifying your desired provider (e.g., `modal`, `daytona`, `runloop`). You can also provide a setup script to configure your sandbox environment upon launch.

Here's how to launch the CLI and connect to a Modal sandbox:

```bash
deepagents-cli --sandbox modal --setup-script ./setup_modal.sh
```

In this command:
-   `--sandbox modal`: Instructs the CLI to use a Modal sandbox as its execution environment.
-   `--setup-script ./setup_modal.sh`: (Optional) Specifies a script to run inside the sandbox once it's launched. This is useful for installing dependencies or setting up the environment.

Example `setup_modal.sh`:

```bash
#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Create a working directory
mkdir -p /sandbox/my_project

echo "Modal sandbox setup complete!"
```

After running the `deepagents-cli` command, the CLI will manage the lifecycle of the Modal sandbox, ensuring it's ready before your agent starts interacting with it. All `execute`, `read_file`, `write_file`, and `edit_file` operations (if configured to be routed to the sandbox) will then occur within this isolated environment.

## 9. Conclusion

You've learned about the robust security and flexibility features of the DeepAgents framework, particularly how `deepagents_backends` and the `CompositeBackend` enable sophisticated routing of file operations. We've explored the importance of the `SandboxBackendProtocol` for consistent, secure execution and seen how remote integrations with platforms like Modal and Daytona provide isolated environments for your agent's code. By utilizing these features, you can build powerful, secure, and scalable AI agents.