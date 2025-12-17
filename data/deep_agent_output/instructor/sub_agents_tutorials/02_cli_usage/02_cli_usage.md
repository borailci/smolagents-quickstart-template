# Using the instructor CLI

## Goal
This tutorial will guide you through the command-line interface (CLI) of the `instructor` library, demonstrating how to leverage its various subcommands to interact with OpenAI services for managing fine-tuning jobs, files, API usage, batch operations, and accessing documentation.

## Prerequisites
Before you begin, ensure you have:
*   A basic understanding of command-line interfaces.
*   Python installed on your system.
*   The `instructor` library installed. You can install it using pip:
    ```bash
    pip install instructor
    ```

## Overview of the `instructor` CLI

The `instructor` CLI is built using `Typer`, a modern library for building CLIs in Python. It provides a structured way to interact with different aspects of OpenAI's API directly from your terminal. The main command is `instructor`, which is then followed by subcommands for specific functionalities.

Here's a high-level overview of the `instructor` CLI structure:

```mermaid
graph TD
    A[instructor] --> B[jobs]
    A --> C[files]
    A --> D[usage]
    A --> E[batch]
    A --> F[docs]
    A --> G[hub (Deprecated)]
```

Let's explore each of these subcommands in detail.

## Core Commands and Examples

### 1. `instructor jobs` - Monitor and Create Fine-Tuning Jobs

This subcommand allows you to manage your OpenAI fine-tuning jobs. You can list existing jobs, retrieve details about a specific job, or create new ones.

**Example: Listing fine-tuning jobs**
```bash
instructor jobs list
```

**Example: Creating a new fine-tuning job (hypothetical)**
While the exact parameters for creating a job would depend on the `jobs` subcommand's implementation, it would typically involve specifying a training file and a model.

```bash
# This is a hypothetical example. Refer to 'instructor jobs --help' for actual usage.
instructor jobs create --training-file file-xxxxxxxxxxxx --model gpt-3.5-turbo
```

### 2. `instructor files` - Manage Files on OpenAI's Servers

The `files` subcommand enables you to upload, list, and delete files stored on OpenAI's platform, which are often used for fine-tuning or other API operations.

**Example: Listing uploaded files**
```bash
instructor files list
```

**Example: Uploading a file (hypothetical)**
```bash
# This is a hypothetical example. Refer to 'instructor files --help' for actual usage.
instructor files upload --purpose fine-tune --file training_data.jsonl
```

### 3. `instructor usage` - Check OpenAI API Usage Data

This command helps you monitor your OpenAI API usage, providing insights into your consumption patterns.

**Example: Checking overall API usage**
```bash
instructor usage
```

### 4. `instructor batch` - Manage OpenAI Batch Jobs

The `batch` subcommand is for managing OpenAI's batch processing feature, allowing you to submit and monitor large sets of API requests asynchronously.

**Example: Listing batch jobs**
```bash
instructor batch list
```

**Example: Creating a batch job (hypothetical)**
```bash
# This is a hypothetical example. Refer to 'instructor batch --help' for actual usage.
instructor batch create --input-file batch_requests.jsonl --endpoint /v1/chat/completions --completion-window 24h
```

### 5. `instructor docs` - Open the instructor Documentation Website

This convenient command directly opens the official `instructor` documentation in your web browser. You can even search the documentation directly.

**Example: Opening the documentation homepage**
```bash
instructor docs
```

**Example: Searching the documentation for a specific topic**
```bash
instructor docs "extraction"
```

### 6. `instructor hub` - (Deprecated)

Note that the `hub` subcommand is deprecated and no longer available.

## Conclusion

The `instructor` CLI provides a powerful and convenient way to manage various aspects of your OpenAI interactions directly from the command line. By understanding and utilizing these subcommands, you can streamline your development workflow and efficiently manage your OpenAI resources. For more detailed information on any subcommand, use the `--help` flag (e.g., `instructor jobs --help`).