
# Tutorial Plan

This document outlines a series of tutorials for the `instructor` library, designed to guide learners from basic usage to advanced features.

## 01_getting_started.md

*   **Synopsis**: Introduce the core problem `instructor` solves: getting structured data from LLMs. Show a simple example of extracting a `User` object from a sentence using OpenAI.
*   **Prerequisites**: `instructor`, `openai`, `pydantic`
*   **Architecture**:
    ```mermaid
    graph TD
        A["User Input (str)"] --> B{"OpenAI's GPT-4"};
        B --> C{"Patched Client (instructor)"};
        C --> D["Pydantic Model (User)"];
    ```
*   **Implementation Steps**:
    1.  Install libraries: `pip install instructor openai pydantic`
    2.  Define a Pydantic `User` model.
    3.  Import `instructor` and `OpenAI`.
    4.  Patch the `OpenAI` client.
    5.  Call `client.chat.completions.create` with `response_model=User`.
*   **Verification**: Print the extracted `User` object and assert its type.
*   **Common Pitfalls**: Forgetting to set the `OPENAI_API_KEY` environment variable.
*   **Challenge Yourself**: Create a `Product` model with `name: str`, `price: float`, and `in_stock: bool` and extract it from a product description.

## 02_advanced_validation.md

*   **Synopsis**: Demonstrate how to use Pydantic validators to enforce complex rules on extracted data and how `max_retries` helps automatically correct errors.
*   **Prerequisites**: `01_getting_started.md`
*   **Architecture**:
    ```mermaid
    graph TD
        A["User Input (str)"] --> B{"OpenAI's GPT-4"};
        B --> C{"Patched Client (instructor)"};
        C -- "Validation Fails" --> E{"Retry Logic (max_retries)"};
        E -- "Re-prompt with error" --> B;
        C -- "Validation Succeeds" --> D["Validated Pydantic Model"];
    ```
*   **Implementation Steps**:
    1.  Create a `UserInfo` model with a validator for email format.
    2.  Use a prompt that might lead to an invalid email.
    3.  Call `client.chat.completions.create` with `response_model=UserInfo` and `max_retries=3`.
*   **Verification**: Show the logs of the retries and the final, validated object.
*   **Common Pitfalls**: Writing validators that are too strict and cause infinite retry loops.
*   **Challenge Yourself**: Add an `age` field to `UserInfo` with a validator to ensure the age is between 18 and 120.

## 03_other_providers.md

*   **Synopsis**: Show how to use `instructor` with other LLM providers like Anthropic and Gemini.
*   **Prerequisites**: `01_getting_started.md`
*   **Architecture**:
    ```mermaid
    graph TD
        subgraph "Anthropic"
            A1["User Input"] --> B1{"Claude 3"};
            B1 --> C1{"Patched Anthropic Client"};
            C1 --> D1["Pydantic Model"];
        end
        subgraph "Gemini"
            A2["User Input"] --> B2{"Gemini Pro"};
            B2 --> C2{"Patched Gemini Client"};
            C2 --> D2["Pydantic Model"];
        end
    ```
*   **Implementation Steps**:
    1.  Install necessary provider libraries: `pip install anthropic google-generativeai`
    2.  Show how to patch the `Anthropic` client and call it.
    3.  Show how to patch the `GenerativeModel` client for Gemini and call it.
*   **Verification**: Print the extracted objects from both providers.
*   **Common Pitfalls**: Provider-specific authentication and environment variable setup.
*   **Challenge Yourself**: Extract a `Recipe` model (ingredients, steps) using either Anthropic's Claude 3 Sonnet or Google's Gemini Pro.

## 04_streaming_lists.md

*   **Synopsis**: Teach how to stream a list of objects from a single LLM call using `IterableModel`.
*   **Prerequisites**: `01_getting_started.md`
*   **Architecture**:
    ```mermaid
    graph TD
        A["User Input (e.g., 'Extract all users from the text')"] --> B{"LLM"};
        B --> C{"Patched Client with IterableModel"};
        C --> D["Stream of Pydantic Objects"];
    ```
*   **Implementation Steps**:
    1.  Define a `User` model.
    2.  Import `IterableModel` from `instructor.dsl`.
    3.  Call `client.chat.completions.create` with `response_model=IterableModel[User]`.
    4.  Iterate over the resulting stream and process each `User` object.
*   **Verification**: Print each user object as it is received.
*   **Common Pitfalls**: Using a standard `List[User]` instead of `IterableModel[User]` for streaming.
*   **Challenge Yourself**: From a long text, stream a list of `Event` objects, each with a `title`, `date`, and `location`.

## 05_batch_processing.md

*   **Synopsis**: Explain how to process a large number of files asynchronously using `instructor`'s batch processing capabilities.
*   **Prerequisites**: `01_getting_started.md`
*   **Architecture**:
    ```mermaid
    graph TD
        A["List of Input Files"] --> B{"BatchProcessor"};
        B --> C{"Async Job Submission"};
        C --> D["Provider's Batch API"];
        D --> E{"Job Completion"};
        E --> F["Parsed Output Files"];
    ```
*   **Implementation Steps**:
    1.  Create a directory with multiple text files.
    2.  Define a Pydantic model for the data to be extracted.
    3.  Use `instructor.batch.processor` to create a batch processor.
    4.  Run the processor and await the results.
*   **Verification**: Check the output directory for the processed files containing the extracted, structured data.
*   **Common Pitfalls**: Incorrectly formatting the input files for the batch job.
*   **Challenge Yourself**: Use batch processing to summarize a collection of articles into a `Summary` model with `title`, `one_sentence_summary`, and `keywords`.

## 06_building_a_cli.md

*   **Synopsis**: Guide the user on building a command-line interface powered by `instructor`.
*   **Prerequisites**: `01_getting_started.md`
*   **Architecture**:
    ```mermaid
    graph TD
        A["Command Line Arguments"] --> B{"Typer App"};
        B --> C{"Instructor-powered function"};
        C --> D["LLM Call"];
        D --> E["Structured Output"];
        E --> F["CLI Output"];
    ```
*   **Implementation Steps**:
    1.  Install `typer`.
    2.  Create a Python script with a `typer` application.
    3.  Define a function that takes a string argument and uses `instructor` to extract information into a Pydantic model.
    4.  Print the structured output to the console.
*   **Verification**: Run the CLI tool from the command line with a sample input and check the output.
*   **Common Pitfalls**: Handling API keys and other secrets in a CLI environment.
*   **Challenge Yourself**: Build a CLI tool that takes a topic as input and generates a short quiz (questions and answers) using an LLM.
