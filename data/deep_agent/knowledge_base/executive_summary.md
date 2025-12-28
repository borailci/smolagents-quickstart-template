## 1. High-Level Purpose
The `agentlightning` library is a comprehensive framework for building, training, and deploying AI agents. It provides a structured environment for optimizing agent performance, particularly through prompt engineering, and supports distributed execution to scale up training and inference. The framework is designed with observability as a first-class citizen, featuring a powerful tracing and instrumentation system based on OpenTelemetry. It includes a flexible data storage layer for persisting training artifacts, a sophisticated proxy for managing interactions with Large Language Models (LLMs), and a modular architecture that separates agent logic, optimization algorithms, and execution strategy.

## 2. Navigation Guide (Source Map)

| Topic / Component | Description | Source File |
| :--- | :--- | :--- |
| Core Components | Foundational infrastructure for client-server communication, configuration, and LLM interaction. | `Core Components.md` |
| Execution and Runner | Framework for orchestrating and executing agent tasks in various configurations (local, distributed). | `Execution and Runner.md` |
| Data Storage | Defines the storage layer for persisting rollouts, traces, and other training artifacts. | `Data Storage.md` |
| Instrumentation & Tracing | System for capturing and analyzing agent execution flow using OpenTelemetry. | `Instrumentation and Tracing.md` |
| Agent Algorithm & Training | Core logic for training and optimizing AI agents, including the `APO` algorithm. | `Agent Algorithm and Training.md` |
| Adapters & Data Types | Core data structures and utilities for transforming data between different formats. | `Adapters and Data Types.md` |

## 3. Key Architecture Modules
*   **`LitAgent`** (Source: `Agent Algorithm and Training.md`): The base class for user-defined agent logic. It abstracts the execution of a single task into a `rollout` method.
*   **`Algorithm` (e.g., `APO`)** (Source: `Agent Algorithm and Training.md`): Defines the optimization strategy that guides the agent's learning process. The `APO` (Automatic Prompt Optimization) algorithm uses textual gradients and beam search to iteratively improve prompts.
*   **`Trainer`** (Source: `Agent Algorithm and Training.md`): The main orchestrator that manages the training loop, connecting the `Algorithm`, `LitAgent`, and `LightningStore`.
*   **`LightningStore`** (Source: `Data Storage.md`): A flexible data storage layer for managing the state of training rollouts, including their execution attempts, telemetry data, and associated resources. It supports in-memory, MongoDB, and other backends.
*   **`ExecutionStrategy`** (Source: `Execution and Runner.md`): Defines the high-level orchestration model for running agent tasks. The `ClientServerExecutionStrategy` allows for distributing the algorithm and runners across different processes or machines.
*   **`LLMProxy`** (Source: `Core Components.md`): A powerful proxy for routing LLM requests, built on `litellm`. It integrates with the `LightningStore` for observability and can manage multiple LLM backends.
*   **`OtelTracer`** (Source: `Instrumentation and Tracing.md`): The primary implementation of the `Tracer` interface, using OpenTelemetry to capture and persist detailed execution traces to the `LightningStore`.

## 4. Common Use Cases
*   **Local Debugging** (Source: `Execution and Runner.md`): Run a full training loop on a single machine with a single runner process for easy debugging of the agent logic and algorithm.
*   **Single-Machine Parallelism** (Source: `Execution and Runner.md`): Leverage multiple CPU cores on a single machine by spawning multiple runner processes to execute rollouts in parallel.
*   **Distributed Training** (Source: `Execution and Runner.md`): Scale up the training process by deploying the system across multiple machines. A central server runs the algorithm and a `LightningStoreServer`, while multiple runner machines connect as clients to execute tasks in parallel.
*   **Prompt Optimization** (Source: `Agent Algorithm and Training.md`): Use the `APO` algorithm to automatically optimize a prompt template by iteratively generating and evaluating new prompt candidates based on agent performance.