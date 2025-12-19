# Provider Integrations Analysis

## 1. Overview
This document analyzes the integration of different AI providers (Anthropic, OpenAI, and Gemini) within the `instructor` library. The `instructor` library extends the capabilities of these AI clients by patching their `create` methods to enable structured output extraction, reasking for validation, and handling various response formats.

Each provider has a dedicated client integration module responsible for adapting the provider's API to the `instructor`'s unified interface. This involves handling different modes of operation (e.g., JSON, tools), managing client types (sync/async), and applying specific response handling and reasking logic.

## 2. File-by-File Analysis

### `instructor/providers/anthropic/client.py`
- **Purpose**: This module provides the integration logic for Anthropic clients (sync and async). It defines the `from_anthropic` function, which patches an Anthropic client to work with `instructor`'s structured output capabilities.
- **Key Components**:
  - `from_anthropic()`: A highly overloaded function that takes an Anthropic client instance and a `mode` (e.g., `ANTHROPIC_TOOLS`, `ANTHROPIC_JSON`). It validates the client type and mode, then patches the client's `messages.create` or `beta.messages.create` method with `instructor.patch` to inject structured output handling. It returns either an `instructor.Instructor` or `instructor.AsyncInstructor` instance.

### `instructor/providers/openai/utils.py`
- **Purpose**: This module contains OpenAI-specific utilities for handling structured outputs, reasking mechanisms, and various response formats. It defines a set of functions for reasking when validation fails and functions for handling different OpenAI modes (e.g., `TOOLS`, `JSON`, `PARALLEL_TOOLS`).
- **Key Components**:
  - `reask_tools()`: Handles reasking for OpenAI tools mode by appending tool response messages with validation errors.
  - `reask_responses_tools()`: Handles reasking for OpenAI responses tools mode by appending user messages with validation errors.
  - `reask_md_json()`: Handles reasking for OpenAI JSON modes by asking the model to correct its JSON response.
  - `reask_default()`: A generic reask handler for default OpenAI mode.
  - `handle_parallel_tools()`: Configures `kwargs` for `PARALLEL_TOOLS` mode, enabling concurrent function calls with multiple function schemas. It validates against streaming.
  - `handle_functions()`: (Deprecated) Configures `kwargs` for the legacy `FUNCTIONS` mode, adding function schema and forcing a function call.
  - `handle_tools_strict()`: Configures `kwargs` for `TOOLS_STRICT` mode, adding a strict function schema and forcing a tool call.
  - `handle_tools()`: Configures `kwargs` for `TOOLS` mode, adding a function schema and forcing a tool call.
  - `handle_responses_tools()`: Configures `kwargs` for `RESPONSES_TOOLS` mode, including conversion of `max_tokens` to `max_output_tokens` and definition of a tool.
  - `handle_responses_tools_with_inbuilt_tools()`: Similar to `handle_responses_tools` but allows for the inclusion of pre-existing tools.
  - `handle_json_o1()`: Handles OpenAI o1 JSON mode, appending a user message with the JSON schema and validating against system messages.
  - `handle_json_modes()`: A general handler for OpenAI JSON, MD_JSON, and JSON_SCHEMA modes. It modifies `response_format` and/or `messages` to guide the model towards generating structured JSON outputs.
  - `handle_openrouter_structured_outputs()`: Configures `kwargs` for OpenRouter structured outputs, adding a `response_format` with a strict JSON schema.
  - `OPENAI_HANDLERS`: A dictionary mapping `instructor.Mode` values to their corresponding reask and response handling functions.

### `instructor/providers/gemini/client.py`
- **Purpose**: This module provides the integration logic for Google Gemini clients. It defines the `from_gemini` function, which is responsible for patching a `genai.GenerativeModel` instance to enable structured output extraction with `instructor`. This function is marked as deprecated in favor of `from_genai` or `from_provider`.
- **Key Components**:
  - `from_gemini()`: An overloaded function that takes a `genai.GenerativeModel` client, a `mode` (e.g., `GEMINI_JSON`, `GEMINI_TOOLS`), and an `use_async` flag. It validates the client type and mode. Based on `use_async`, it patches either `client.generate_content_async` or `client.generate_content` with `instructor.patch` to handle structured outputs. It returns either an `instructor.Instructor` or `instructor.AsyncInstructor` instance.

## 3. Architecture & Data Flow

The `instructor` library acts as an intermediary layer between the user's code and the AI provider's client. The core idea is to "patch" the `create` (or equivalent) method of the provider's client. This patching mechanism allows `instructor` to inject logic for schema validation, reasking, and structured output processing.

```mermaid
graph TD
    A[User Code] -->|Calls instructor.from_provider/from_anthropic/from_gemini| B(Instructor Integration Functions)
    B -->|Patches Provider Client's Create Method| C{Provider Client (Anthropic, OpenAI, Gemini)}
    C -->|AI Model Call (with structured output instructions)| D[AI Model]
    D -->|Raw AI Response| C
    C -->|Instructor Patched Logic (Validation, Reask, Deserialization)| E(Structured Output)
    E -->|Returns to User Code| A

    subgraph Reasking Flow
        E --X|Validation Fails| F{Reask Logic (e.g., reask_tools, reask_md_json)}
        F -->|Modifies Kwargs/Messages| C
    end

    subgraph OpenAI Specific Modes
        C -- OpenAI Mode --> G{OpenAI Handlers (e.g., handle_tools, handle_json_modes)}
        G -->|Transforms Kwargs for specific modes| C
    end
```

## 4. Code Deep Dive

### Anthropic `from_anthropic` patching:
```python
# From instructor/providers/anthropic/client.py
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
    # ... validation logic ...

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
    # ... async client handling ...
```
This snippet demonstrates how `instructor.patch` is used to wrap the `create` method of the Anthropic client. The `mode` parameter passed to `instructor.patch` dictates how `instructor` will handle the response and structure the output.

### OpenAI `reask_md_json` for JSON correction:
```python
# From instructor/providers/openai/utils.py
def reask_md_json(
    kwargs: dict[str, Any],
    response: Any,
    exception: Exception,
    failed_attempts: list[Any] | None = None,  # noqa: ARG001
):
    kwargs = kwargs.copy()
    reask_msgs = [dump_message(response.choices[0].message)]

    reask_msgs.append(
        {
            "role": "user",
            "content": f"Correct your JSON ONLY RESPONSE, based on the following errors:\n{exception}",
        }
    )
    kwargs["messages"].extend(reask_msgs)
    return kwargs
```
This function illustrates a reasking mechanism for OpenAI JSON modes. If a validation error occurs, it constructs a new user message containing the error and appends it to the conversation history (`kwargs["messages"]`). This prompts the AI model to correct its previous JSON output.

### OpenAI `handle_parallel_tools` for concurrent calls:
```python
# From instructor/providers/openai/utils.py
def handle_parallel_tools(
    response_model: type[Any], new_kwargs: dict[str, Any]
) -> tuple[type[Any], dict[str, Any]]:
    if new_kwargs.get("stream", False):
        raise ConfigurationError(
            "stream=True is not supported when using PARALLEL_TOOLS mode"
        )
    new_kwargs["tools"] = handle_parallel_model(response_model)
    new_kwargs["tool_choice"] = "auto"
    return cast(type[Any], ParallelModel(typehint=response_model)), new_kwargs
```
This function demonstrates how `instructor` adapts the `kwargs` for OpenAI's `PARALLEL_TOOLS` mode. It sets the `tools` parameter with multiple function schemas derived from the `response_model` and sets `tool_choice` to "auto", allowing the model to make multiple function calls concurrently.

## 5. Integration Points
- **Dependencies**:
  - `instructor/providers/anthropic/client.py` depends on `anthropic`, `instructor` (core library), and `typing`.
  - `instructor/providers/openai/utils.py` depends on `json`, `textwrap`, `typing`, `openai` (specifically `pydantic_function_tool`), `instructor.dsl.parallel` (for `ParallelModel`, `handle_parallel_model`), `instructor.core.exceptions` (`ConfigurationError`), `instructor.mode` (`Mode`), `instructor.utils.core` (`dump_message`, `merge_consecutive_messages`), and `instructor.processing.schema` (`generate_openai_schema`).
  - `instructor/providers/gemini/client.py` depends on `google.generativeai` (`genai`), `instructor` (core library), and `typing`.

- **Dependents**: These provider integration modules are primarily depended upon by the main `instructor` library's `from_provider` or similar functions, which serve as entry points for users to obtain an `Instructor` instance tailored to a specific AI client. They are also implicitly used when `instructor` patches the client's `create` method.