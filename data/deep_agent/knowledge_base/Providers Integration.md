
# Providers Integration Analysis

## 1. Overview

The `instructor` library integrates with various LLM providers by patching their native clients. This integration layer adapts the provider-specific API calls to enable structured data extraction using Pydantic models. The core mechanism involves factory functions (`from_anthropic`, `from_gemini`) that wrap the original client and a set of mode-specific handlers (especially for OpenAI) that manipulate the request and response payloads.

This analysis covers the integration modules for OpenAI, Anthropic, and Google Gemini, detailing how each provider is adapted for use with `instructor`.

## 2. File-by-File Analysis

### `instructor/providers/openai/utils.py`

- **Purpose**: This module is the heart of the OpenAI provider integration. It provides a comprehensive set of functions to handle different extraction modes (`TOOLS`, `JSON`, `FUNCTIONS`, etc.), manage retries with corrective feedback (`reask`), and prepare the arguments for the OpenAI API.
- **Key Components**:
  - **Response Handlers (`handle_*`)**: These functions (`handle_tools`, `handle_json_modes`, `handle_parallel_tools`, etc.) are responsible for modifying the `kwargs` of the `client.chat.completions.create` call. They inject the necessary parameters like `tools`, `tool_choice`, or `response_format` based on the specified `instructor.Mode` and the Pydantic `response_model`.
  - **Reask Handlers (`reask_*`)**: When a validation error occurs on the LLM's output, these functions (`reask_tools`, `reask_md_json`, etc.) construct new messages to be sent back to the model. These messages include the original response and the validation exception, guiding the model to correct its output.
  - **Handler Registry (`OPENAI_HANDLERS`)**: This dictionary maps each `instructor.Mode` to its corresponding `response` and `reask` handler functions, creating a pluggable system for managing OpenAI's diverse capabilities.

### `instructor/providers/anthropic/client.py`

- **Purpose**: This module provides a simple factory function, `from_anthropic`, to create a patched `instructor` client from a native `anthropic` client instance.
- **Key Components**:
  - **`from_anthropic()`**: This function is the public entry point for integrating with Anthropic. It accepts a sync or async `anthropic` client and an `instructor.Mode` (`ANTHROPIC_JSON` or `ANTHROPIC_TOOLS`). It then returns a corresponding `instructor.Instructor` or `instructor.AsyncInstructor` instance with the `create` method patched to handle structured responses.

### `instructor/providers/gemini/client.py`

- **Purpose**: This module provides the `from_gemini` factory function to adapt Google's `GenerativeModel` for use with `instructor`. **Note: This module is deprecated** in favor of `from_genai` or the provider-agnostic `from_provider`.
- **Key Components**:
  - **`from_gemini()`**: This function takes a `google.generativeai.GenerativeModel` instance and wraps it, creating an `instructor.Instructor` or `instructor.AsyncInstructor`. It patches the `generate_content` (or `generate_content_async`) method to inject the logic required for structured JSON output, as defined by `instructor.Mode.GEMINI_JSON` or `instructor.Mode.GEMINI_TOOLS`.

## 3. Integration Patterns

The primary integration pattern is the **Factory Function Pattern**. Users do not interact with these provider modules directly. Instead, they import a factory function (`from_anthropic`, `from_gemini`) which handles the setup:

1.  **Client Instantiation**: The user first creates an instance of the provider's native client (e.g., `anthropic.Anthropic()`).
2.  **Instructor Wrapping**: The user passes this client to the appropriate `instructor` factory function (e.g., `instructor.from_anthropic(client)`).
3.  **Patching**: The factory function identifies the correct method to patch (e.g., `client.messages.create`) and wraps it using `instructor.patch`. This wrapper intercepts calls, injects necessary parameters for structured output, and validates the response against the user's Pydantic model.
4.  **Return Patched Client**: The factory returns an `instructor.Instructor` (or `AsyncInstructor`) instance, which exposes the patched method for the user to call.

For OpenAI, the integration is more complex due to its multiple modes. The `instructor.patch` function uses the `OPENAI_HANDLERS` registry in `openai/utils.py` to dynamically select the correct request/response handling logic based on the chosen `instructor.Mode`.

## 4. Public Interface & API Reference

The public interface consists of the factory functions designed to be the entry point for users.

| Function | Signature | Description |
|---|---|---|
| `from_anthropic` | `(client: anthropic.Anthropic | anthropic.AsyncAnthropic, mode: instructor.Mode = ANTHROPIC_TOOLS, **kwargs) -> instructor.Instructor | instructor.AsyncInstructor` | Creates a patched `instructor` client from a native Anthropic client. |
| `from_gemini` | `(client: genai.GenerativeModel, mode: instructor.Mode = GEMINI_JSON, use_async: bool = False, **kwargs) -> instructor.Instructor | instructor.AsyncInstructor` | **(Deprecated)** Creates a patched `instructor` client from a Google Gemini `GenerativeModel`. |

The internal functions within `instructor/providers/openai/utils.py` are not part of the public API but are crucial to the internal workings of `instructor.patch` for the OpenAI provider.

## 5. Use Cases

- **Use `from_anthropic` when**: You have an existing application using the `anthropic` Python SDK and want to add structured output capabilities with Pydantic models without rewriting your client setup code.
- **Use `from_gemini` when**: You are working with the `google.generativeai` library and need to extract structured data. (Note: The library recommends migrating to `from_genai`).
- **The `openai/utils.py` module is used implicitly when**: You use `instructor.patch` with an `openai` client. You select the extraction strategy by setting the `mode` parameter (e.g., `mode=instructor.Mode.TOOLS` for function calling, `mode=instructor.Mode.JSON` for JSON mode).
