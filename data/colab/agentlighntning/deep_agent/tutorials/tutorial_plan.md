# AgentLightning Tutorial Plan

This document outlines a series of tutorials for learning the `agentlightning` library. The tutorials are designed to be followed in order, starting from a basic "Hello World" example and progressing to more advanced topics.

## Tutorial Checklist

### 1. Hello World: Your First AgentLightning Run

- **Filename**: `01-hello-world.md`
- **Description**: A minimal, end-to-end example demonstrating how to set up a `Trainer` with a `Baseline` algorithm and a simple `LitAgent`. The goal is to get a working example running as quickly as possible.
- **Knowledge Base Files**:
  - `executive_summary.md`
  - `Algorithm and Training.md`
- **Source Files**:
  - `pyproject.toml` (for package name and installation)
  - `agentlightning/trainer/trainer.py` (for `Trainer`)
  - `agentlightning/algorithm/fast.py` (for `Baseline` algorithm)
  - `agentlightning/litagent/litagent.py` (for `LitAgent`)

### 2. LitAgent Deep Dive

- **Filename**: `02-litagent-deep-dive.md`
- **Description**: An in-depth exploration of the `LitAgent` class. This tutorial will cover the differences between `rollout`, `rollout_async`, `training_rollout`, and `validation_rollout`. It will also show how to access contextual information like the `tracer` from within the agent.
- **Knowledge Base Files**:
  - `Algorithm and Training.md`
  - `Instrumentation and Utilities.md`
- **Source Files**:
  - `agentlightning/litagent/litagent.py`
  - `agentlightning/structs.py` (for `Rollout`, `RolloutRawResult`)

### 3. Automatic Prompt Optimization (APO)

- **Filename**: `03-automatic-prompt-optimization.md`
- **Description**: This tutorial introduces the `APO` algorithm for automatic prompt optimization. It will walk through setting up an experiment to refine a prompt template based on performance feedback.
- **Knowledge Base Files**:
  - `Algorithm and Training.md`
- **Source Files**:
  - `agentlightning/algorithm/apo/apo.py`
  - `agentlightning/algorithm/apo/prompt.py`

### 4. Distributed Execution

- **Filename**: `04-distributed-execution.md`
- **Description**: Learn how to scale `agentlightning` from local execution to a distributed client-server setup. This tutorial will explain how to configure and launch the algorithm server and multiple runners on different machines.
- **Knowledge Base Files**:
  - `Client and Server.md`
- **Source Files**:
  - `agentlightning/trainer/trainer.py` (focus on `strategy` parameter)
  - `agentlightning/execution/client_server.py`
  - `agentlightning/cli.py` (for CLI commands)

### 5. Data Handling and Storage

- **Filename**: `05-data-handling-and-storage.md`
- **Description**: A guide to the `LightningStore`, the key-value store for state management. This tutorial will cover the in-memory store and demonstrate how to configure a persistent MongoDB backend for storing rollouts, resources, and spans.
- **Knowledge Base Files**:
  - `Data Handling and Storage.md`
- **Source Files**:
  - `agentlightning/store/store.py`
  - `agentlightning/store/mongo.py`
  - `agentlightning/store/memory.py`

### 6. Monitoring and Debugging

- **Filename**: `06-monitoring-and-debugging.md`
- **Description**: This tutorial will focus on the monitoring and debugging capabilities of `agentlightning`. It will cover the use of the built-in dashboard for visualizing rollouts and resources, and explain how to leverage OpenTelemetry for custom tracing.
- **Knowledge Base Files**:
  - `Dashboard Frontend.md`
  - `Instrumentation and Utilities.md`
- **Source Files**:
  - `agentlightning/utils/telemetry/tracer.py`
  - `agentlightning/utils/telemetry/otlp.py`
  - `dashboard/*` (for understanding the dashboard components)