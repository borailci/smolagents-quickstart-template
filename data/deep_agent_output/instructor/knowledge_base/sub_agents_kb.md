# Provider Clients Analysis

## 1. Overview
The `instructor/providers` directory serves as the integration layer for various Large Language Model (LLM) providers within the `instructor` library. Its primary purpose is to extend the capabilities of native LLM clients (e.g., Anthropic, Gemini, OpenAI, Cohere, Mistral) to enable structured output generation and reasking mechanisms. Each provider module typically exposes a `from_<provider_name>` function that wraps the provider's client into an `instructor.Instructor` or `instructor.AsyncInstructor` instance, allowing for schema-guided responses.

## 2. Key Components
-   `from_anthropic(client, mode, beta, **kwargs)`: Initializes an `Instructor` or `AsyncInstructor` for Anthropic clients, supporting various Anthropic modes like `ANTHROPIC_TOOLS` and `ANTHROPIC_JSON`.
-   `from_gemini(client, mode, use_async, **kwargs)`: Initializes an `Instructor` or `AsyncInstructor` for Gemini's `genai.GenerativeModel`, supporting `GEMINI_JSON` and `GEMINI_TOOLS` modes. (Note: This function is deprecated in favor of `from_genai` or `from_provider`).
-   `from_cohere(client, mode, **kwargs)`: Initializes an `Instructor` or `AsyncInstructor` for Cohere clients (v1 and v2, sync and async), supporting `COHERE_TOOLS` and `COHERE_JSON_SCHEMA`.
-   `from_mistral(client, mode, use_async, **kwargs)`: Initializes an `Instructor` or `AsyncInstructor` for Mistral clients, supporting `MISTRAL_TOOLS` and `MISTRAL_STRUCTURED_OUTPUTS`.
-   `instructor.patch()`: A crucial utility used across providers to wrap the original client's generation method (e.g., `client.messages.create`, `client.chat.complete`) with `instructor`'s logic for structured output and reasking.
-   `instructor.Mode`: An enumeration defining different operational modes for each provider, dictating how structured output is achieved (e.g., via tool calls, JSON schema, markdown JSON).
-   `OPENAI_HANDLERS`: A dictionary in `openai/utils.py` mapping `instructor.Mode` values to specific `reask` and `response` handler functions for OpenAI. These handlers manage how prompts are modified for reasking and how the client's `kwargs` are prepared for different modes (e.g., adding `tools` or `response_format`).
-   `reask_*` functions (e.g., `reask_tools`, `reask_md_json`, `reask_default`): Functions within `openai/utils.py` that modify the `kwargs['messages']` to include user feedback when validation errors occur, guiding the model to correct its output.
-   `handle_*` functions (e.g., `handle_parallel_tools`, `handle_tools_strict`, `handle_json_modes`): Functions within `openai/utils.py` that prepare the client's `kwargs` (e.g., adding `tools`, `tool_choice`, `response_format`) based on the specified `instructor.Mode` and `response_model`.

## 3. Data Flow
1.  **Client Initialization**: The user instantiates a native LLM client (e.g., `anthropic.Anthropic()`).
2.  **Instructor Wrapper**: The native client is passed to a provider-specific `from_<provider_name>` function (e.g., `instructor.from_anthropic(client)`). This function performs several steps:
    *   Validates the `mode` and client type.
    *   Determines if the client is synchronous or asynchronous.
    *   Wraps the client's message creation method (e.g., `client.messages.create`, `client.chat.complete`, `client.generate_content`) using `instructor.patch()`. This patching injects `instructor`'s logic for handling `response_model` and reasking.
    *   Returns an `instructor.Instructor` or `instructor.AsyncInstructor` instance, which now acts as the enhanced client.
3.  **Structured Call**: When the wrapped `Instructor` instance's `create` method is called with a `response_model` (e.g., a Pydantic model), `instructor` intervenes.
    *   For OpenAI, the `OPENAI_HANDLERS` dictionary is consulted based on the `mode` to apply appropriate `response` handlers. These handlers transform the `response_model` into the LLM's specific mechanism for structured output (e.g., tool/function schemas, `response_format`).
    *   The modified request is sent to the LLM.
4.  **Response Processing and Reasking**: Upon receiving a response from the LLM:
    *   `instructor` attempts to parse the response into the specified `response_model`.
    *   If parsing fails (e.g., due to validation errors), and a reasking mechanism is configured (common in OpenAI integrations), the `reask` handler (e.g., `reask_tools`) modifies the original `messages` in the `kwargs` to include feedback about the validation error. This new set of messages is then used for a subsequent call to the LLM, prompting it to correct its output. This cycle continues until a valid response is obtained or a maximum number of retries is reached.

## 4. Code Deep Dive

**Example: `from_anthropic` patching**
```python
def from_anthropic(
    client: (
        anthropic.Anthropic
        | anthropic.AsyncAnthropic
        | anthropic.AnthropicBedrock
        | anthropic.AsyncAnthropicBedrock
        | anthropic.AsyncAnthropicVertex
        | anthropic.AnthropicVertex
    ),
    mode: instructor.Mode = instructor.Mode.ANTHROPIC_TOOLS,
    beta: bool = False,
    **kwargs: Any,
) -> instructor.Instructor | instructor.AsyncInstructor:
    # ... (mode and client validation)

    if beta:
        create = client.beta.messages.create
    else:
        create = client.messages.create

    if isinstance(
        client,
        (anthropic.Anthropic, anthropic.AnthropicBedrock, anthropic.AnthropicVertex),
    ):
        return instructor.Instructor(
            client=client,
            create=instructor.patch(create=create, mode=mode),
            provider=instructor.Provider.ANTHROPIC,
            mode=mode,
            **kwargs,
        )
    else:
        return instructor.AsyncInstructor(
            client=client,
            create=instructor.patch(create=create, mode=mode),
            provider=instructor.Provider.ANTHROPIC,
            mode=mode,
            **kwargs,
        )
```

**Example: `handle_tools` in OpenAI utilities**
```python
def handle_tools(
    response_model: type[Any] | None, new_kwargs: dict[str, Any]
) -> tuple[type[Any] | None, dict[str, Any]]:
    if response_model is None:
        return None, new_kwargs

    new_kwargs["tools"] = [
        {
            "type": "function",
            "function": generate_openai_schema(response_model),
        }
    ]
    new_kwargs["tool_choice"] = {
        "type": "function",
        "function": {"name": generate_openai_schema(response_model)["name"]},
    }
    return response_model, new_kwargs
```

## 5. Tutorial Hints
*   **Basic Structured Output**: Demonstrate how to use `instructor.from_anthropic` (or any other provider) with a simple Pydantic model to extract structured data from a natural language prompt.
*   **Reasking Mechanism**: Create a tutorial showing a scenario where the LLM initially provides invalid data, and how `instructor` automatically re-prompts the model using the `reask` functionality to get a correct response.
*   **Different Modes**: Illustrate the usage of various `instructor.Mode` options for a single provider (e.g., `ANTHROPIC_TOOLS` vs. `ANTHROPIC_JSON`, or OpenAI's `TOOLS` vs. `JSON_SCHEMA`) and explain when to use each.
*   **Asynchronous Usage**: Provide examples of using the `AsyncInstructor` for non-blocking operations with async LLM clients.
*   **Parallel Tool Calls (OpenAI)**: Show how to extract multiple structured objects concurrently using `Mode.PARALLEL_TOOLS` with OpenAI. Attached to this file the `summary.md` you asked for. `summary.md` will contain the full summary of the provider clients. If you would like to know anything else, feel free to ask. Otherwise, use `final_answer` to close the conversation. Good luck!