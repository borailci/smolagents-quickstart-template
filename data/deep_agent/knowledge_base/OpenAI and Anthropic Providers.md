
# OpenAI and Anthropic Provider Analysis

## 1. Overview

These modules provide the foundational support for integrating the `instructor` library with the OpenAI and Anthropic Large Language Models (LLMs). They act as provider-specific adapters, translating `instructor`'s high-level, mode-based API into the precise request formats and protocols expected by each LLM provider. The core responsibility is to manage various interaction modes (e.g., tool calling, JSON output), handle response validation, and implement retry logic (`reask`) when the LLM fails to produce a valid, parsable output.

## 2. File-by-File Analysis

### `instructor/providers/anthropic/client.py`

- **Purpose**: This file serves as the primary entry point for using `instructor` with an Anthropic client. It provides the `from_anthropic` factory function.
- **Key Components**:
  - `from_anthropic(...)`: A factory function that takes an existing sync or async Anthropic client and "patches" it to create an `instructor.Instructor` or `instructor.AsyncInstructor` instance. It validates that the client and the specified `mode` are compatible and injects the necessary request/response handling logic.

### `instructor/providers/openai/utils.py`

- **Purpose**: This module contains the specific implementation details for all OpenAI-related modes. It is responsible for constructing the correct API arguments for `chat.completions.create` calls based on the selected `instructor.Mode`.
- **Key Components**:
  - **Response Handlers (`handle_*`)**: A collection of functions (e.g., `handle_tools`, `handle_json_modes`, `handle_parallel_tools`) that modify the keyword arguments of the API call. They add `tools`, `tool_choice`, `response_format`, and other parameters as required by the chosen mode.
  - **Reask Handlers (`reask_*`)**: Functions like `reask_tools` and `reask_md_json` that are invoked when Pydantic validation of the LLM's output fails. They construct new messages to append to the conversation history, informing the model of the validation error and asking it to correct its output.
  - `OPENAI_HANDLERS`: A dictionary that acts as a registry, mapping each `Mode` to its corresponding response handler and reask handler.

### `instructor/providers/anthropic/utils.py`

- **Purpose**: This module mirrors the OpenAI utils but is tailored for the Anthropic API, particularly the Claude family of models.
- **Key Components**:
  - **System Message Management**: Anthropic's API uses a dedicated `system` parameter for system prompts. Functions like `extract_system_messages` and `combine_system_messages` manage the separation of system messages from the main conversation history.
  - **Response Handlers (`handle_anthropic_*`)**: Functions such as `handle_anthropic_tools` and `handle_anthropic_json` that prepare the `tools`, `tool_choice`, and `system` parameters for the Anthropic API call.
  - **Reask Handlers (`reask_anthropic_*`)**: Functions (`reask_anthropic_tools`, `reask_anthropic_json`) that formulate follow-up messages when validation fails, using Anthropic's `tool_result` format for tool-related errors.
  - `ANTHROPIC_HANDLERS`: A registry mapping `Mode` enums to their specific Anthropic implementation handlers.

## 3. Architecture and Data Flow

The architectural pattern is consistent for both providers and is centered around a "mode-based handler" registry.

1.  **Initialization**: The user wraps an LLM client using `instructor.from_openai` or `instructor.from_anthropic`, selecting a specific `Mode`.
2.  **Patching**: The `patch` function intercepts the `chat.completions.create` method.
3.  **Request Handling**: When a patched `create` call is made with a `response_model`, the `instructor` wrapper looks up the `Mode` in the provider-specific `HANDLERS` dictionary (e.g., `OPENAI_HANDLERS`).
4.  **Argument Modification**: The corresponding "response" handler (e.g., `handle_tools` for OpenAI, `handle_anthropic_tools` for Anthropic) is executed. This function modifies the API call's keyword arguments, adding the necessary parameters to instruct the LLM to return structured data.
5.  **API Call**: The modified arguments are passed to the original `create` method, and the request is sent to the provider's API.
6.  **Validation & Reask**: If the response is received but fails Pydantic validation against the `response_model`, the "reask" handler from the registry is invoked. It constructs a new request with error information and retries the API call (up to a specified `max_retries` limit).

This flow effectively decouples the user's code from the provider-specific implementation details of achieving structured output.

## 4. Code Deep Dive

### OpenAI: `handle_tools`

This function is fundamental for enabling tool-use with OpenAI models. It takes the user's Pydantic model and converts it into a schema that the OpenAI API understands, then forces the model to use it via `tool_choice`.

```python
def handle_tools(
    response_model: type[Any] | None, new_kwargs: dict[str, Any]
) -> tuple[type[Any] | None, dict[str, Any]]:
    """
    Handle OpenAI tools mode.
    """
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

### Anthropic: `handle_anthropic_tools` and System Message Handling

This Anthropic handler demonstrates the key difference in API design. It not only sets up the tools but also has to extract system messages from the standard `messages` list and place them in the dedicated `system` parameter.

```python
def handle_anthropic_tools(
    response_model: type[Any] | None, new_kwargs: dict[str, Any]
) -> tuple[type[Any] | None, dict[str, Any]]:
    """
    Handle Anthropic tools mode.
    """
    if response_model is None:
        new_kwargs = handle_anthropic_message_conversion(new_kwargs)
        return None, new_kwargs

    tool_descriptions = generate_anthropic_schema(response_model)
    new_kwargs["tools"] = [tool_descriptions]
    new_kwargs["tool_choice"] = {
        "type": "tool",
        "name": response_model.__name__,
    }

    system_messages = extract_system_messages(new_kwargs.get("messages", []))

    if system_messages:
        new_kwargs["system"] = combine_system_messages(
            new_kwargs.get("system"), system_messages
        )

    new_kwargs["messages"] = [
        m for m in new_kwargs.get("messages", []) if m["role"] != "system"
    ]

    return response_model, new_kwargs
```

## 5. API Reference & Integration

### Public Interface

The primary public-facing interface for the Anthropic provider is the `from_anthropic` factory function.

| Function | Signature |
|---|---|
| `from_anthropic` | `(client: Anthropic | AsyncAnthropic | ..., mode: instructor.Mode = instructor.Mode.ANTHROPIC_TOOLS, **kwargs) -> instructor.Instructor | instructor.AsyncInstructor` |

### Internal Handler Registries

The core of the provider logic is managed through two internal dictionaries that map `instructor.Mode` to specific handler functions.

- **`OPENAI_HANDLERS`**: Contains mappings for modes like `TOOLS`, `JSON`, `PARALLEL_TOOLS`, `JSON_SCHEMA` and more.
- **`ANTHROPIC_HANDLERS`**: Contains mappings for modes like `ANTHROPIC_TOOLS`, `ANTHROPIC_JSON`, `ANTHROPIC_REASONING_TOOLS`, and `ANTHROPIC_PARALLEL_TOOLS`.

These registries are internal to the library but are crucial to its operation, providing a pluggable system for defining and extending provider capabilities.
