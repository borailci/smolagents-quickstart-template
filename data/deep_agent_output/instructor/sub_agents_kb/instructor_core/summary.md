# instructor/core Analysis

## 1. Overview
The `instructor/core` module is the heart of the Instructor library, providing the foundational mechanisms to extend the capabilities of LLM client libraries (like OpenAI's) with structured output, robust error handling, and extensibility via hooks. It primarily focuses on patching the `chat.completions.create` methods of these clients to inject features such as response model validation (using Pydantic), automatic retries for validation failures, and a flexible event system.

## 2. Key Components
-   `client.py`:
    -   `Instructor`: A synchronous client wrapper that integrates structured extraction, retries, and hooks.
    -   `AsyncInstructor`: An asynchronous counterpart to `Instructor`.
    -   `Response`: A helper class for `Instructor` that simplifies calling `create`, `create_iterable`, `create_partial`, and `create_with_completion`.
    -   `AsyncResponse`: The asynchronous version of `Response`.
    -   `from_openai(client, mode)`: A factory function to create `Instructor` or `AsyncInstructor` instances from `openai.OpenAI` or `openai.AsyncOpenAI` clients, applying the necessary patching based on the specified mode.
    -   `from_litellm(completion, mode)`: A factory function to create `Instructor` or `AsyncInstructor` instances from a LiteLLM completion function.

-   `exceptions.py`:
    -   `InstructorError`: Base exception for all Instructor-specific errors.
    -   `FailedAttempt`: A `NamedTuple` to store details of a single failed retry attempt.
    -   `IncompleteOutputException`: Raised when LLM output is truncated.
    -   `InstructorRetryException`: Raised when all retry attempts for a prompt are exhausted.
    -   `ValidationError`: Raised when an LLM response fails Pydantic validation.
    -   `ProviderError`: Encapsulates errors from specific LLM providers.
    -   `ConfigurationError`: For issues with Instructor configuration or initialization.
    -   `ModeError`: Raised when an invalid mode is used for a given provider.
    -   `ClientError`: For client initialization or usage errors.
    -   `AsyncValidationError`: Specific to async validation errors.
    -   `ResponseParsingError`: Raised when the LLM's raw response cannot be parsed.

-   `hooks.py`:
    -   `Hooks`: A class managing event handlers for various stages of the completion process (e.g., `completion:kwargs`, `completion:response`, `parse:error`). It allows registering, emitting, and clearing handlers.
    -   `HookName`: An Enum defining the available hook points.

-   `patch.py`:
    -   `patch(client/create, mode)`: The core function that intercepts the LLM client's `create` method. It injects logic for `response_model` processing, retry mechanisms, context handling, caching, and hook invocation.

-   `retry.py`:
    -   `retry_sync(func, response_model, ..., hooks)`: Handles synchronous retries for the patched `create` function, including error handling, usage tracking, and re-asking logic.
    -   `retry_async(func, response_model, ..., hooks)`: The asynchronous counterpart to `retry_sync`.
    -   `initialize_retrying`: Configures `tenacity.Retrying` or `tenacity.AsyncRetrying` objects based on `max_retries`.
    -   `initialize_usage`: Initializes usage tracking for different providers.
    -   `extract_messages`: Helper to normalize message extraction from various client kwargs.

## 3. Data Flow
1.  **Client Initialization**: A user initializes an OpenAI or other LLM client.
2.  **Instructor Patching**: `instructor.from_openai()` or `instructor.patch()` is called, which intercepts the `client.chat.completions.create` method. This creates an `Instructor` or `AsyncInstructor` instance.
3.  **Request Initiation**: When `client.chat.completions.create()` is invoked with a `response_model` and messages:
    a.  `patch.py`'s `new_create_sync` or `new_create_async` is executed.
    b.  `handle_context` processes validation and context data.
    c.  `handle_response_model` (from `processing.response`) modifies kwargs to inject tool/function calling details based on the `response_model` and `mode`.
    d.  `handle_templating` applies any prompt templating.
    e.  Cache lookup occurs if enabled.
    f.  The request proceeds to `retry_sync` or `retry_async`.
4.  **Retry Logic**: The `retry.py` functions (`retry_sync`/`retry_async`):
    a.  Initialize usage tracking and `tenacity` retry logic.
    b.  Enter a retry loop, calling the *original* (or wrapped) `client.chat.completions.create` function.
    c.  `hooks.emit_completion_arguments` is called before the LLM request.
    d.  Upon receiving an LLM response, `hooks.emit_completion_response` is called.
    e.  `update_total_usage` tracks token consumption.
    f.  `process_response` (from `processing.response`) attempts to parse and validate the LLM's response against the `response_model`.
    g.  If `ValidationError`, `JSONDecodeError`, or other relevant `InstructorError` occurs:
        i.  `hooks.emit_parse_error` is called.
        ii. The failed attempt is logged.
        iii. `handle_reask_kwargs` (from `processing.response`) modifies the messages to include the error feedback, preparing for a re-ask if retries are available.
        iv. The error is re-raised, triggering the next retry attempt via `tenacity`.
    h.  If validation succeeds, the structured Pydantic object is returned.
    i.  If all retries fail, an `InstructorRetryException` is raised.
5.  **Response Handling**: The validated Pydantic object is returned to the user.
    a.  If caching is enabled, the successful response is stored.

## 4. Code Deep Dive

**Patching the `create` method (from `instructor/core/patch.py`):**
```python
# Simplified snippet from patch.py
def patch(
    client: OpenAI | AsyncOpenAI | None = None,
    create: Callable[T_ParamSpec, T_Retval] | None = None,
    mode: Mode = Mode.TOOLS,
) -> OpenAI | AsyncOpenAI:
    # ... (initialization and async check)

    @wraps(func) # type: ignore
    async def new_create_async(
        response_model: type[T_Model] | None = None,
        # ... (other parameters)
        **kwargs: T_ParamSpec.kwargs,
    ) -> T_Model:
        # ... (context, response_model, templating, caching)

        response = await retry_async(
            func=func, # type:ignore (This `func` is the original client.chat.completions.create)
            response_model=response_model,
            context=context,
            max_retries=max_retries,
            args=args,
            kwargs=new_kwargs,
            strict=strict,
            mode=mode,
            hooks=hooks,
        )
        # ... (caching, return response)

    # ... (new_create_sync equivalent)

    new_create = new_create_async if func_is_async else new_create_sync

    if client is not None:
        client.chat.completions.create = new_create # type: ignore
        return client
    else:
        return new_create # type: ignore

```

**Retry Mechanism (from `instructor/core/retry.py`):**
```python
# Simplified snippet from retry.py
def retry_sync(
    func: Callable[T_ParamSpec, T_Retval],
    response_model: type[T_Model] | None,
    args: Any,
    kwargs: Any,
    max_retries: int | Retrying = 1,
    mode: Mode = Mode.TOOLS,
    hooks: Hooks | None = None,
    # ... (other parameters)
) -> T_Model | None:
    hooks = hooks or Hooks()
    total_usage = initialize_usage(mode)
    max_retries = initialize_retrying(max_retries, is_async=False, timeout=kwargs.get("timeout"))
    failed_attempts: list[FailedAttempt] = []

    try:
        response = None
        for attempt in max_retries:
            with attempt:
                try:
                    hooks.emit_completion_arguments(*args, **kwargs)
                    response = func(*args, **kwargs) # Original LLM call
                    hooks.emit_completion_response(response)
                    response = update_total_usage(
                        response=response, total_usage=total_usage
                    )

                    return process_response( # Validate and parse
                        response=response,
                        response_model=response_model,
                        validation_context=context,
                        strict=strict,
                        mode=mode,
                        stream=stream,
                    )
                except (ValidationError, JSONDecodeError, InstructorValidationError) as e:
                    hooks.emit_parse_error(e)
                    failed_attempts.append(
                        FailedAttempt(
                            attempt_number=attempt.retry_state.attempt_number,
                            exception=e,
                            completion=response,
                        )
                    )
                    # ... (check if last attempt, emit hooks.emit_completion_last_attempt)
                    kwargs = handle_reask_kwargs( # Update messages for re-ask
                        kwargs=kwargs,
                        mode=mode,
                        response=response,
                        exception=e,
                        failed_attempts=failed_attempts,
                    )
                    raise e # Re-raise to trigger next retry
    except RetryError as e:
        raise InstructorRetryException( # All retries failed
            f"Failed to get a valid response after {len(failed_attempts)} attempts.",
            last_completion=response,
            n_attempts=len(failed_attempts),
            total_usage=total_usage.total_tokens,
            create_kwargs=kwargs,
            failed_attempts=failed_attempts,
        ) from e

```

## 5. Tutorial Hints
-   **Getting Started with Structured Output**: A tutorial demonstrating how to use `instructor.from_openai` and define a Pydantic `response_model`.
-   **Robust LLM Calls with Retries**: How to leverage `max_retries` for self-correcting LLM calls and understanding `InstructorRetryException`.
-   **Debugging LLM Interactions with Hooks**: A guide on using the `Hooks` system to monitor `completion:kwargs`, `completion:response`, and `parse:error` events for debugging and logging.
-   **Handling Partial and Streaming Responses**: Demonstrating `create_iterable` and `create_partial` for real-time processing and incomplete outputs.
-   **Custom Error Handling**: How to catch and interpret the various `InstructorError` types for more specific error management.`