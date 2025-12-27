## 1. High-Level Purpose

The `agentlightning` project is a comprehensive framework for training and optimizing AI agents in a distributed environment. It provides a client-server architecture to manage and execute agent "rollouts" (tasks) at scale. The system is built around a flexible and extensible design, allowing developers to implement custom agent logic (`LitAgent`), and plug in different optimization strategies (`Algorithm`). The framework includes robust support for data handling, persistent storage via in-memory or MongoDB backends (`LightningStore`), and detailed tracing and instrumentation using OpenTelemetry. A React-based dashboard is also provided for monitoring and visualizing training progress, rollouts, and resources.

## 2. Navigation Guide (Source Map)

| Topic / Component | Description | Source File |
| :--- | :--- | :--- |
| Core Architecture & Training | Describes the main entry points, including the `Trainer`, `Algorithm`, and `LitAgent` classes. | `Algorithm and Training.md` |
| Distributed Execution | Details the client-server architecture for running agents in a distributed manner. | `Client and Server.md` |
| Legacy Core Logic | Contains information about the deprecated client/server logic and core data types. | `Core Logic.md` |
| Dashboard Frontend | Explains the React-based dashboard for viewing rollouts and resources. | `Dashboard Frontend.md` |
| Data Storage | Covers the `LightningStore` abstraction and its in-memory and MongoDB implementations. | `Data Handling and Storage.md` |
| Instrumentation & Tracing | Details the tracing and instrumentation capabilities, including OpenTelemetry and `agentops` integration. | `Instrumentation and Utilities.md` |
| Compilation Plan | Outlines the plan for compiling the project. | `compilation_plan.md` |

## 3. Key Architecture Modules

*   **`Trainer`** (Source: `Algorithm and Training.md`): The central orchestrator for the entire training process. It is responsible for setting up the algorithm, runners, and storage backend.
*   **`Algorithm`** (Source: `Algorithm and Training.md`): The "brain" of the training process. The framework provides implementations like `APO` (Automatic Prompt Optimization) for advanced, iterative prompt refinement.
*   **`LitAgent`** (Source: `Algorithm and Training.md`): The base class for user-defined agents. Developers implement the `rollout` method to define the agent's logic for processing a task.
*   **`LightningStore`** (Source: `Data Handling and Storage.md`): A key-value store abstraction for communication and state management between the `Trainer`, `Algorithm`, and `Runners`. It has both in-memory and MongoDB backends.
*   **`ClientServerExecutionStrategy`** (Source: `Client and Server.md`): Manages the lifecycle of the algorithm and runner processes, enabling distributed execution. It can run both on a single machine or across multiple machines.
*   **`OtelTracer`** (Source: `Instrumentation and Utilities.md`): The core tracing implementation, which uses OpenTelemetry to create, manage, and export spans for detailed monitoring of agent execution.

## 4. Common Use Cases

*   **Local Development & Debugging** (Source: `Client and Server.md`): Run a complete agent experiment on a single machine using the `both` role in the `ClientServerExecutionStrategy`.
*   **Distributed Deployment** (Source: `Client and Server.md`): Scale out agent execution by deploying multiple runner instances on different machines, all connecting to a central algorithm server.
*   **Viewing Resources and Rollouts** (Source: `Dashboard Frontend.md`): Use the dashboard to view lists of all resources and rollouts, search for specific items, and view the details of each rollout.
*   **Automatic Prompt Optimization** (Source: `Algorithm and Training.md`): Utilize the `APO` algorithm to automatically refine and optimize prompt templates based on performance metrics.