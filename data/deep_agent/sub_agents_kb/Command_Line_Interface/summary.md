
# Command Line Interface (CLI) Analysis

## 1. Overview

The `instructor` command-line interface (CLI) provides a suite of tools for developers to manage various aspects of their interactions with large language model providers like OpenAI and Anthropic. The CLI is built using the `typer` library, making it a robust and user-friendly tool. Its primary functions include managing fine-tuning jobs, handling batch processing, and interacting with provider-specific features. The main entry point for the CLI is `instructor`, as defined in the `pyproject.toml` file.

## 2. File-by-File Analysis

### `instructor/cli/cli.py`

- **Purpose**: This file serves as the main entry point for the entire CLI application. It aggregates command groups from other modules into a single, unified interface.
- **Key Components**:
  - `app: typer.Typer`: The central `Typer` application instance.
  - `app.add_typer(...)`: This function is used to register sub-commands from other files, including `jobs`, `files`, `usage`, `hub`, and `batch`.
  - `docs(query: Optional[str])`: A simple command that opens the official `instructor` documentation in a web browser. It can optionally include a search query.

### `instructor/cli/batch.py`

- **Purpose**: This module provides comprehensive functionality for managing batch jobs with providers like OpenAI and Anthropic. It allows for the creation, listing, monitoring, cancellation, and downloading of batch job data. It abstracts the provider-specific details using the `instructor.batch.BatchProcessor`.
- **Key Components**:
  - `app: typer.Typer`: A `Typer` instance for the `batch` sub-command.
  - `watch(...)`: Lists and monitors the status of batch jobs, with options for live polling and filtering by provider.
  - `create_from_file(...)`: Submits a new batch job from a pre-formatted file.
  - `create(...)`: Creates a batch job request file from a list of messages.
  - `cancel(...)`: Cancels a pending or running batch job.
  - `delete(...)`: Deletes a completed batch job.
  - `download_file(...)`: Downloads the output file of a completed batch job.
  - `results(...)`: Retrieves and saves the results from a completed batch job.

### `instructor/cli/jobs.py`

- **Purpose**: This module is dedicated to managing OpenAI fine-tuning jobs. It provides commands to create, list, monitor, and cancel fine-tuning jobs.
- **Key Components**:
  - `app: typer.Typer`: A `Typer` instance for the `jobs` sub-command.
  - `watch(...)`: Monitors the status of the most recent fine-tuning jobs with live updates.
  - `create_from_id(...)`: Creates a new fine-tuning job from an already uploaded file ID.
  - `create_from_file(...)`: Uploads a local file and then creates a fine-tuning job from it.
  - `cancel(...)`: Cancels a running fine-tuning job.

## 3. Public Interface & Use Cases

The `instructor` CLI is designed to be used directly from the terminal. The commands are organized hierarchically.

- **To get help**:
  ```bash
  instructor --help
  instructor batch --help
  instructor jobs --help
  ```
- **Common Use Cases**:
  - **Fine-tuning a model**: 
    1. Create a training data file (e.g., `train.jsonl`).
    2. Run `instructor jobs create-from-file train.jsonl --model gpt-3.5-turbo`.
    3. Monitor the job with `instructor jobs list`.

  - **Running a batch job**:
    1. Prepare a file with API requests (e.g., `requests.jsonl`).
    2. Submit the job: `instructor batch create-from-file --file-path requests.jsonl --model openai/gpt-4o-mini`.
    3. Monitor with `instructor batch list --live`.
    4. Once complete, download results: `instructor batch download-file --batch-id <ID> --download-file-path results.jsonl`.

## 4. Integration Points

- **`pyproject.toml`**: Defines the main entry point for the CLI via `instructor = "instructor.cli.cli:app"`.
- **`instructor.cli.cli.py`**: Acts as the central aggregator, importing and registering `Typer` apps from `jobs.py` and `batch.py`.
- **`instructor.batch.BatchProcessor`**: The `batch.py` CLI module is a client of the `BatchProcessor` class, which contains the core logic for interacting with different batch APIs.
- **`openai` & `anthropic` SDKs**: The CLI commands directly or indirectly use the official Python SDKs for OpenAI and Anthropic to make API calls.

## 5. API Reference

Below is a reference table for the main CLI commands.

| Command | Sub-Command | Description | Key Arguments |
|---|---|---|---|
| `instructor` | `docs` | Open the `instructor` documentation. | `[query]` (optional) |
| `instructor` | `jobs` | Manage OpenAI fine-tuning jobs. | `list`, `create-from-id`, `create-from-file`, `cancel` |
| `instructor jobs` | `list` | Monitor the status of recent fine-tuning jobs. | `--limit`, `--poll`, `--screen` |
| `instructor jobs` | `create-from-file` | Create a fine-tuning job from a local file. | `file`, `--model`, `--n-epochs`, `--batch-size` |
| `instructor jobs` | `cancel` | Cancel a fine-tuning job. | `id` |
| `instructor` | `batch` | Manage OpenAI and Anthropic batch jobs. | `list`, `create`, `create-from-file`, `cancel`, `delete`, `download-file`, `results` |
| `instructor batch` | `list` | See and monitor all existing batch jobs. | `--limit`, `--poll`, `--live`, `--provider` |
| `instructor batch` | `create-from-file` | Create a batch job from a file. | `--file-path`, `--model`, `--description` |
| `instructor batch` | `cancel` | Cancel a batch job. | `--batch-id`, `--provider` |
| `instructor batch` | `download-file` | Download the file associated with a batch job. | `--batch-id`, `--download-file-path`, `--provider` |
