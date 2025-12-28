'''
# Tutorial Plan

This document outlines the plan for creating a series of tutorials for the `agentlightning` library.

## 01_getting_started.md: Getting Started with Agent Lightning

*   **Synopsis**: This tutorial will guide you through the basics of `agentlightning`. You will learn how to define a simple `LitAgent`, create a `Trainer`, and run a basic training loop. This is the "Hello, World!" of `agentlightning`.
*   **Prerequisites**:
    *   `pip install agentlightning`
*   **Architecture**:

    ```mermaid
    graph TD
        A["Trainer"] --> B["LitAgent"]
    ```

*   **Implementation Steps**:
    1.  **Define the Agent**: Create a simple agent class that inherits from `agentlightning.litagent.LitAgent` and implements the `rollout` method.
    2.  **Instantiate the Trainer**: Create an instance of the `agentlightning.trainer.Trainer`.
    3.  **Run the Training**: Call the `fit` method on the trainer, passing in the agent and a simple dataset.
*   **Verification**: Check the logs for output indicating the training loop has run.
*   **Common Pitfalls**: Forgetting to implement the `rollout` method.
*   **Challenge Yourself**: Modify the `rollout` method to return a different reward and observe the change in the logs.

## 02_data_persistence.md: Data Persistence with LightningStore

*   **Synopsis**: Learn how to use `LightningStore` to save and load training data, including rollouts and traces. This is crucial for long-running training jobs and for later analysis.
*   **Prerequisites**: `01_getting_started.md`
*   **Architecture**:

    ```mermaid
    graph TD
        A["Trainer"] --> C["LightningStore"]
        B["LitAgent"] --> C
    ```

*   **Implementation Steps**:
    1.  **Configure the Store**: Show how to configure a `LightningStore`, for example, an in-memory store or a MongoDB store.
    2.  **Pass to Trainer**: Pass the configured store to the `Trainer`.
    3.  **Run Training**: Run the training loop as before.
*   **Verification**: Show how to inspect the `LightningStore` to see the saved rollouts.
*   **Common Pitfalls**: Configuration errors for the store backend.
*   **Challenge Yourself**: Configure a different backend for the `LightningStore`, such as the file system backend.
''''''
## 03_observability.md: Observability with OtelTracer

*   **Synopsis**: A deep dive into the tracing system. This tutorial will explain how to use `OtelTracer` to collect and interpret tracing data for debugging and performance analysis.
*   **Prerequisites**: `02_data_persistence.md`
*   **Architecture**:

    ```mermaid
    graph TD
        A["LitAgent"] -- "records traces" --> B["OtelTracer"]
        B -- "sends data to" --> C["LightningStore"]
    ```

*   **Implementation Steps**:
    1.  **Configure the Tracer**: Show how to configure the `OtelTracer`.
    2.  **Pass to Trainer**: Pass the tracer to the `Trainer`.
    3.  **Add Custom Spans**: Modify the `LitAgent` to add custom spans to the traces.
*   **Verification**: Show how to retrieve and inspect the traces from the `LightningStore`.
*   **Common Pitfalls**: Not configuring the tracer correctly, leading to no data being collected.
*   **Challenge Yourself**: Export the traces to an external observability platform like Jaeger or Zipkin.

## 04_cli_configuration.md: CLI Configuration

*   **Synopsis**: This tutorial will teach you how to use the `lightning_cli` utility to configure all components of a training run from the command line, making it easy to experiment with different configurations.
*   **Prerequisites**: `01_getting_started.md`
*   **Architecture**:

    ```mermaid
    graph TD
        A["lightning_cli"] -- "configures" --> B["Trainer"]
        A -- "configures" --> C["LitAgent"]
        A -- "configures" --> D["LightningStore"]
    ```

*   **Implementation Steps**:
    1.  **Create a Config File**: Show how to create a YAML configuration file for the `lightning_cli`.
    2.  **Run from CLI**: Demonstrate how to run the training using the `lightning_cli` with the configuration file.
*   **Verification**: Check the output of the CLI to confirm the training run was successful.
*   **Common Pitfalls**: Syntax errors in the YAML configuration file.
*   **Challenge Yourself**: Override a configuration parameter from the command line.

## 05_distributed_training.md: Distributed Training

*   **Synopsis**: Learn how to set up and run a distributed training job using the `ClientServerExecutionStrategy`. This is essential for scaling up training to multiple machines.
*   **Prerequisites**: `04_cli_configuration.md`
*   **Architecture**:

    ```mermaid
    graph TD
        A["Server"] -- "sends tasks" --> B["Runner"]
        B -- "executes tasks" --> C["LitAgent"]
        C -- "sends results" --> A
    ```

*   **Implementation Steps**:
    1.  **Configure the Strategy**: Show how to configure the `ClientServerExecutionStrategy` in the YAML file.
    2.  **Start the Server**: Start the `lightning_cli` in server mode.
    3.  **Start the Client**: Start one or more clients that connect to the server.
*   **Verification**: Check the logs on both the server and the clients to see the distributed training in action.
*   **Common Pitfalls**: Network configuration issues preventing clients from connecting to the server.
*   **Challenge Yourself**: Run the server and clients on different machines.

## 06_llm_proxy.md: LLM Proxy

*   **Synopsis**: This tutorial will cover how to configure and use the `LLMProxy` for advanced, observable interactions with various language models.
*   **Prerequisites**: `01_getting_started.md`
*   **Architecture**:

    ```mermaid
    graph TD
        A["LitAgent"] -- "makes LLM calls" --> B["LLMProxy"]
        B -- "routes to" --> C["Language Model"]
    ```

*   **Implementation Steps**:
    1.  **Configure the Proxy**: Show how to configure the `LLMProxy` with different LLM backends.
    2.  **Use in Agent**: Modify the `LitAgent` to use the `LLMProxy` to make language model calls.
*   **Verification**: Inspect the traces to see the LLM interactions captured by the proxy.
*   **Common Pitfalls**: API key or endpoint configuration errors for the language models.
*   **Challenge Yourself**: Add a new language model to the `LLMProxy` configuration.
'''