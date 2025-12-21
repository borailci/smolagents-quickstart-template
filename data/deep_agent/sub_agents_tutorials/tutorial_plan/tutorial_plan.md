
# Instructor Tutorial Series: From Beginner to Expert

This document outlines a comprehensive tutorial series for the `instructor` library, designed to guide developers from basic setup to advanced, real-world applications.

## Tutorial 1: Getting Started with Instructor

*   **File**: `01_getting_started.md`
*   **Synopsis**: Learn how to install `instructor`, patch your first OpenAI client, and get structured, validated data from an LLM in just a few lines of code. This tutorial answers the fundamental question: "How can I reliably get structured JSON from an LLM without writing complex parsing logic?"
*   **Prerequisites**:
    *   Python 3.9+
    *   An OpenAI API Key
*   **Architecture**:
    ```mermaid
    graph TD
        A["User with OpenAI Client"] --> B{"patch(client)"};
        B --> C["Patched Client"];
        C -->|`create(response_model=...)`| D["OpenAI API"];
        D --> E["LLM JSON Response"];
        E --> F["Pydantic Validation"];
        F --> G["Validated Pydantic Object"];
    ```
*   **Implementation Steps**:
    1.  Install `instructor` and `openai`.
    2.  Define a simple Pydantic model.
    3.  Create an OpenAI client and apply the `instructor.patch`.
    4.  Call the `client.chat.completions.create` method with the `response_model` parameter.
*   **Verification**: Print the resulting Pydantic object and its type to confirm it's not a dictionary but a rich Python object.
*   **Common Pitfalls**: Forgetting to `patch` the client before using `response_model`.
*   **Challenge Yourself**: Create a new Pydantic model with more complex types (e.g., `Enum`, `datetime`) and extract data for it.

## Tutorial 2: Core Concepts Deep Dive

*   **File**: `02_core_concepts.md`
*   **Synopsis**: Understand the "magic" behind `instructor`. This tutorial explores the core architecture, including the `patch` function, response validation, and the automatic retry mechanism. It explains how `instructor` ensures data quality and handles LLM inconsistencies.
*   **Prerequisites**: Completion of Tutorial 1.
*   **Architecture**:
    ```mermaid
    graph TD
        subgraph "Instructor's Role"
            A["client.chat.completions.create()"] --> B{Intercept Call};
            B --> C{Inject JSON Mode & Pydantic Schema};
            C --> D[LLM API Call];
            D --> E{LLM Response};
            E --> F{Is it valid JSON?};
            F -- No --> G{Retry with Error Message};
            G --> D;
            F -- Yes --> H{Parse to Pydantic Model};
            H --> I{Validation Error?};
            I -- Yes --> G;
            I -- No --> J[Return Validated Object];
        end
    ```
*   **Implementation Steps**:
    1.  Demonstrate a case where the LLM might return invalid data.
    2.  Show how to use a Pydantic `field_validator` to enforce custom business rules.
    3.  Explain the `max_retries` parameter by setting it to a specific number and observing the behavior.
*   **Verification**: Check the logs or output to see the validation errors and retry attempts made by `instructor`.
*   **Common Pitfalls**: Writing validators that are too strict, leading to excessive retries.
*   **Challenge Yourself**: Add a `BeforeValidator` to a Pydantic model to preprocess a string field before it's parsed.

## Tutorial 3: Advanced Features - Streaming, Validation, and Retries

*   **File**: `03_advanced_features.md`
*   **Synopsis**: Go beyond single-object extraction. This tutorial covers how to stream lists of objects, perform complex validations, and use the `CitationMixin` to ground LLM responses in source material.
*   **Prerequisites**: Completion of Tutorial 2.
*   **Architecture**:
    ```mermaid
    graph LR
        subgraph "Streaming with IterableModel"
            A["`create(response_model=IterableModel)`"] --> B{LLM streams JSON chunks};
            B --> C{Instructor assembles chunks};
            C --> D{"Yields complete Pydantic objects"};
        end
        subgraph "Grounding with CitationMixin"
            E["`response_model=MyModel.with_citation()`"] --> F{LLM must cite sources};
            F --> G["`response.citation` contains evidence"];
        end
    ```
*   **Implementation Steps**:
    1.  Use `instructor.dsl.IterableModel` to stream a list of `User` objects from a single prompt.
    2.  Implement the `instructor.dsl.CitationMixin` to force the model to cite its sources from a provided context.
    3.  Demonstrate parallel tool calling with `instructor.dsl.parallel`.
*   **Verification**: Iterate through the streamed response, printing each object as it becomes available. For the citation example, check that the `citation` attribute of the response is populated correctly.
*   **Common Pitfalls**: Not using `stream=True` when using `IterableModel`.
*   **Challenge Yourself**: Combine streaming and citation to build a system that extracts and verifies information from a document in real-time.

## Tutorial 4: Multi-Provider Support (Anthropic, Gemini, and more)

*   **File**: `04_multi_provider.md`
*   **Synopsis**: `instructor` is not limited to OpenAI. Learn how to use its powerful features with other major providers like Anthropic, Google Gemini, and others. The key is the provider-agnostic `patch` function.
*   **Prerequisites**: API keys for Anthropic, Google, or another supported provider.
*   **Architecture**:
    ```mermaid
    graph TD
        A["Anthropic Client"] --> C{"patch(client)"};
        B["Google Gemini Client"] --> C;
        C --> D["Patched `instructor` Client"];
        D --> E{Same `response_model` API};
        E --> F["Structured Output (Pydantic)"];
    ```
*   **Implementation Steps**:
    1.  Install the necessary client library (e.g., `anthropic`, `google-generativeai`).
    2.  Instantiate the provider's client (e.g., `Anthropic()`).
    3.  Patch the client using `instructor.from_anthropic()` or the equivalent `patch` call.
    4.  Run the same `response_model` query from Tutorial 1, now on the new provider.
*   **Verification**: The same Pydantic model should be returned, regardless of the underlying LLM provider.
*   **Common Pitfalls**: Mismatching the provider's message format (e.g., user/assistant roles).
*   **Challenge Yourself**: Create a function that takes a prompt and a provider name, and returns a structured response by dynamically switching between patched clients.

## Tutorial 5: Practical Applications - Building a RAG System

*   **File**: `05_practical_applications.md`
*   **Synopsis**: Apply everything you've learned to build a real-world Retrieval-Augmented Generation (RAG) system. This tutorial will use `instructor` to extract entities, generate search queries, and structure the final answer, ensuring it is grounded in the retrieved documents.
*   **Prerequisites**: Completion of all previous tutorials.
*   **Architecture**:
    ```mermaid
    graph TD
        A[User Question] --> B{"`instructor` to extract keywords"};
        B --> C[Keyword Query];
        C --> D[Vector Database];
        D --> E[Retrieve Documents];
        E --> F{Combine Question + Docs}; 
        F --> G{"`instructor` with `CitationMixin`"};
        G --> H["Grounded, Structured Answer"];
    ```
*   **Implementation Steps**:
    1.  **Query Expansion**: Use `instructor` to extract key entities from a user question into a `SearchQuery` model.
    2.  **Document Retrieval**: Perform a search against a simple document store.
    3.  **Answer Synthesis**: Use `instructor` and the `CitationMixin` to generate a final, structured answer that must cite the retrieved documents.
*   **Verification**: The final output should be a Pydantic object containing the answer and the specific text spans from the source documents that support it.
*   **Common Pitfalls**: Poor document retrieval leading to the LLM being unable to find an answer and failing validation.
*   **Challenge Yourself**: Use `instructor.batch` to process a large set of questions against your RAG system to evaluate its performance.
