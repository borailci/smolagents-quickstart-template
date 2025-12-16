# instructor/core Knowledge Base

## 1. Overview
The `instructor/core` module is the foundational layer for the `instructor` library, primarily enabling reliable structured output from Large Language Models (LLMs). Its main purpose is to bridge the gap between LLM inference and predefined data schemas (typically Pydantic models), ensuring that the generated responses adhere to a specified structure. This module provides client implementations (`Instructor`, `AsyncInstructor`) that wrap standard LLM clients (like OpenAI's) and extend their `create` methods to support automatic parsing, validation, and retrying of structured outputs. It also introduces various modes for interacting with LLMs (e.g., `TOOLS`, `JSON`) and a robust hook system for customizability.

While the task description mentioned `base.py` and `helpers.py`, these files were not found in the provided context. Therefore, this documentation focuses solely on `client.py`, which appears to contain the core client logic.

## 2. Key Components

### `Instructor` (and `AsyncInstructor`)
These are the central classes. They act as wrappers around standard LLM clients (e.g., `openai.OpenAI` or `openai.AsyncOpenAI`). They enhance the client's `chat.completions.create` method to handle `response_model` parameters, which are Pydantic `BaseModel` classes defining the desired output structure. They manage retry logic, apply different interaction modes, and integrate a comprehensive hook system. `AsyncInstructor` provides asynchronous counterparts to all methods.

### `Response` (and `AsyncResponse`)
These are convenience classes instantiated within `Instructor` and `AsyncInstructor` when certain `instructor.Mode` values (like `RESPONSES_TOOLS`) are used. They offer a slightly simplified interface for calling the underlying client's `create` method, primarily by standardizing the input message format (converting a string input to a list of `ChatCompletionMessageParam`).

### `from_openai` and `from_litellm` functions
These are factory functions responsible for creating and patching `Instructor` or `AsyncInstructor` instances. They take an existing LLM client (from OpenAI or a LiteLLM completion function) and an `instructor.Mode`, then return an `Instructor` instance configured to work with that client and mode. They handle the internal patching of the `create` method and ensure provider-specific mode compatibility.

### `instructor.Mode`
An enumeration (imported from `instructor`) that defines how the structured output is achieved. Examples include `TOOLS` (using OpenAI's function calling/tool use API), `JSON` (asking the LLM to output pure JSON), `MD_JSON` (asking for JSON within a markdown block), `FUNCTIONS` (deprecated OpenAI function calling), and others specific to certain providers like `OPENROUTER_STRUCTURED_OUTPUTS`.

### Hooks (`instructor.core.hooks.Hooks`)
A mechanism to register and trigger callback functions at different stages of the completion process, such as before sending kwargs (`completion:kwargs`), after receiving a response (`completion:response`), or on parsing errors (`parse:error`). This allows for extensive customizability and observability.

## 3. Data Flow & Dependencies

**Input**: The primary input to the `instructor` client is a list of `ChatCompletionMessageParam` (standard OpenAI chat messages) and a `response_model` (a Pydantic `BaseModel` class). Other inputs include `max_retries`, `validation_context`, and arbitrary `**kwargs` passed to the underlying LLM client.

**Processing**: 
1.  The `from_openai` (or `from_litellm`) function patches the original LLM client's `create` method with `instructor.patch`, which injects the structured output logic based on the chosen `instructor.Mode`.
2.  When `instructor_client.create()` is called, it first processes its own `kwargs` and combines its internal hooks with any call-specific hooks.
3.  It then invokes the patched `create_fn` (which is typically `client.chat.completions.create` wrapped with instructor's logic).
4.  Inside `instructor.patch` (not shown in `client.py` but implicitly used), the `response_model` is converted into a tool definition (for `TOOLS` mode) or instruction within the prompt (for `JSON` mode). The LLM call is made.
5.  The LLM's raw response is then intercepted. If a `response_model` was provided, `instructor` attempts to parse and validate the LLM's output against this Pydantic model. If validation fails or parsing errors occur, the retry mechanism (configured by `max_retries`) is engaged, potentially prompting the LLM to correct its output.
6.  Hooks registered for events like `completion:response` or `parse:error` are triggered during this process.

**Output**: The output is an instance of the specified `response_model` (a Pydantic `BaseModel`) or an iterable/generator of such instances for streaming methods (`create_iterable`, `create_partial`). If no `response_model` is specified, it returns the raw LLM completion object.

**Dependencies**: The module heavily depends on:
*   `openai`: For integrating with OpenAI's API clients.
*   `pydantic`: For defining structured response models and validation.
*   `tenacity`: For robust retry mechanisms on API failures or validation errors.
*   `instructor` (parent library): For `Mode` enum, `patch` function, and `Partial` type.

## 4. Code Deep Dive

### Initialization of the Instructor Client
The `from_openai` function is the primary way to initialize an `instructor` client, wrapping an existing OpenAI client.

```python
def from_openai(
    client: openai.OpenAI | openai.AsyncOpenAI,
    mode: instructor.Mode = instructor.Mode.TOOLS,
    **kwargs: Any,
) -> Instructor | AsyncInstructor:
    # ... provider detection and mode assertions ...

    if isinstance(client, openai.OpenAI):
        return Instructor(
            client=client,
            create=instructor.patch(
                create=(
                    client.chat.completions.create
                    if mode
                    not in {
                        instructor.Mode.RESPONSES_TOOLS_WITH_INBUILT_TOOLS,
                        instructor.Mode.RESPONSES_TOOLS,
                    }
                    else partial(map_chat_completion_to_response, client=client)
                ),
                mode=mode,
            ),
            mode=mode,
            provider=provider,
            **kwargs,
        )
    # ... similar logic for AsyncOpenAI ...
```
This snippet shows how `from_openai` inspects the input client type and patches the `client.chat.completions.create` method using `instructor.patch`. The `partial` function is used to adapt the response mapping for specific modes. The `mode` parameter is crucial here, determining how `instructor.patch` will modify the underlying `create` call.

### Core `create` Method
The `create` method on the `Instructor` (or `AsyncInstructor`) class is the primary entry point for making LLM calls with structured output.

```python
class Instructor:
    # ... __init__ and other methods ...

    def create(
        self,
        response_model: type[T] | None,
        messages: list[ChatCompletionMessageParam],
        max_retries: int | Retrying | AsyncRetrying = 3,
        validation_context: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        strict: bool = True,
        hooks: Hooks | None = None,
        **kwargs: Any,
    ) -> T | Any | Awaitable[T] | Awaitable[Any]:
        kwargs = self.handle_kwargs(kwargs)

        # Combine client hooks with per-call hooks
        combined_hooks = self.hooks
        if hooks is not None:
            combined_hooks = self.hooks + hooks

        return self.create_fn(
            response_model=response_model,
            messages=messages,
            max_retries=max_retries,
            validation_context=validation_context,
            context=context,
            strict=strict,
            hooks=combined_hooks,
            **kwargs,
        )
```
This method demonstrates the forwarding of calls to the internally `patched` `create_fn`. It also illustrates how client-level `kwargs` are merged with call-specific `kwargs`, and how `hooks` are combined, providing a flexible way to manage LLM call parameters and observability.

### Handling Streaming and Partial Responses
The `create_partial` method is designed for streaming responses, yielding partial Pydantic objects as tokens arrive.

```python
class Instructor:
    # ... other methods ...
    def create_partial(
        self,
        response_model: type[T],
        messages: list[ChatCompletionMessageParam],
        max_retries: int | Retrying | AsyncRetrying = 3,
        # ... other params ...
        **kwargs: Any,
    ) -> Generator[T, None, None] | AsyncGenerator[T, None]:
        kwargs["stream"] = True
        kwargs = self.handle_kwargs(kwargs)
        # ... hooks combination ...

        response_model = instructor.Partial[response_model]  # type: ignore
        return self.create_fn(
            messages=messages,
            response_model=response_model,
            # ... other params ...
            **kwargs,
        )
```
Here, `stream` is explicitly set to `True` in `kwargs`, and the `response_model` is wrapped with `instructor.Partial`. This indicates that the underlying patched `create_fn` will be configured to handle streaming input and progressively parse the incoming tokens into instances of `instructor.Partial[response_model]`, allowing for real-time processing of structured data.

## 5. Potential Pitfalls
*   **Mode Mismatch**: Using an `instructor.Mode` that is not supported by the underlying LLM provider or client can lead to runtime errors (asserts within `from_openai`). Developers must ensure the chosen mode is compatible.
*   **Pydantic Model Complexity**: While powerful, overly complex or recursive Pydantic models can sometimes confuse LLMs, leading to lower parsing success rates and increased retries. Simplification or careful prompting might be necessary.
*   **Retry Exhaustion**: If `max_retries` is too low or the LLM consistently fails to produce valid structured output, the `create` call will ultimately raise an exception.
*   **Asynchronous vs. Synchronous Usage**: Mixing `Instructor` with `AsyncOpenAI` or `AsyncInstructor` with `OpenAI` directly will lead to type errors or unexpected behavior. Always ensure consistency in synchronous/asynchronous client usage with the corresponding `Instructor` type.
*   **Deprecation Warnings**: The code indicates `validation_context` is deprecated in 2.0. Users should be aware of such warnings and plan for migration.