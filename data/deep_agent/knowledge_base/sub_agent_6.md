# Distillation and Templating Analysis

## 1. Overview
This document provides a technical analysis of the `distil.py` and `templating.py` modules within the `instructor` library. The `distil.py` module focuses on function distillation, allowing the tracking and replaying of function calls for fine-tuning language models, particularly with OpenAI's API. The `templating.py` module provides robust message templating capabilities using Jinja2, supporting various large language model (LLM) providers like OpenAI, Anthropic, Cohere, VertexAI, and Gemini.

## 2. File-by-File Analysis

### `instructor/distil.py`
- **Purpose**: This module enables the "distillation" of Python function calls and their responses into a format suitable for fine-tuning large language models. It also supports a "dispatch" mode to directly call an LLM instead of the original function. It tracks function input, output, and metadata, logging this information for later use in training.
- **Key Components**:
  - `FinetuneFormat` (enum): Defines the output format for fine-tuning data: `MESSAGES` (OpenAI chat completion format) or `RAW` (raw function details).
  - `Instructions` (class): The core class for managing distillation and dispatch. It configures the logging, fine-tuning format, and interaction with the OpenAI API.
    - `__init__()`: Initializes the `Instructions` instance with a name, ID, logging handlers, fine-tune format, indentation settings, and an OpenAI client.
    - `distil()` (decorator): A decorator that, when applied to a function, either tracks its execution (`distil` mode) or dispatches the function call to an LLM (`dispatch` mode). It ensures the function has a Pydantic `BaseModel` as its return type hint.
    - `track()`: Logs the function call, its arguments, and the Pydantic `BaseModel` response in the specified `finetune_format`.
    - `openai_kwargs()`: Constructs the `OpenAIChatKwargs` dictionary, preparing messages and function definitions for an OpenAI chat completion API call.
  - `get_signature_from_fn()`: Extracts the function signature as a string.
  - `format_function()`: Formats a function into a string including its definition, docstring, and body.
  - `is_return_type_base_model_or_instance()`: Checks if a function's return type hint is a Pydantic `BaseModel`.

### `instructor/templating.py`
- **Purpose**: This module provides utilities for applying Jinja2 templates to messages exchanged with various LLM APIs. It standardizes message content across different providers by dynamically applying context variables.
- **Key Components**:
  - `apply_template()`: Applies a Jinja2 template to a given string using a provided context dictionary. It also uses `textwrap.dedent` for consistent formatting.
  - `process_message()`: Processes a single message dictionary, applying `apply_template` to its content based on the detected message format (OpenAI, Anthropic, Cohere, VertexAI, Gemini).
  - `handle_templating()`: The main entry point for applying templating. It takes `kwargs` (typically intended for an LLM API call), a `Mode` enum, and a `context` dictionary. It identifies the message structure within `kwargs` and delegates to `process_message` for templating, returning the modified `kwargs`.

## 3. Architecture & Data Flow

### `distil.py` Flow
```mermaid
graph TD
    A[User Function with @Instructions.distil] -->|Call| B{Instructions.distil Decorator}
    B -- IF "distil" mode --> C[Original Function Execution]
    C --> D[Instructions.track(fn, args, kwargs, resp)]
    D --> E[Log Data (JSON) to Logger]
    B -- IF "dispatch" mode --> F[Instructions.openai_kwargs]
    F --> G[OpenAI Client Chat Completion API Call]
    G --> H[LLM Response]
```

### `templating.py` Flow
```mermaid
graph TD
    A[Initial LLM API kwargs] --> B[handle_templating(kwargs, mode, context)]
    B --> C{Identify Message Structure (OpenAI, Anthropic, etc.)}
    C --> D[Loop through messages/parts]
    D --> E[process_message(message_part, context, mode)]
    E --> F[apply_template(text, context)]
    F --> G[Jinja2 SandboxedEnvironment Render]
    G --> H[Templated Message Part]
    H --> I[Reconstruct Modified kwargs]
    I --> J[Templated LLM API kwargs]
```

## 4. Code Deep Dive

### `instructor/distil.py` - `Instructions.distil` decorator
This snippet shows the core logic for the `distil` decorator, which conditionally switches between tracking function calls and dispatching to an LLM.
```python
    def distil(
        self,
        *args: Any,
        name: Optional[str] = None,
        mode: Literal['distil', 'dispatch'] = "distil",
        model: str = "gpt-3.5-turbo",
        fine_tune_format: Optional[FinetuneFormat] = None,
    ) -> Union[
        Callable[P, Union[T_Retval, ChatCompletion]],
        Callable[[Callable[P, T_Retval]], Callable[P, Union[T_Retval, ChatCompletion]]],
    ]:
        # ... (mode and format validation)

        def _wrap_distil(
            fn: Callable[P, T_Retval],
        ) -> Callable[P, Union[T_Retval, ChatCompletion]]:
            # ... (return type validation)
            return_base_model = inspect.signature(fn).return_annotation

            @functools.wraps(fn)
            def _dispatch(*args: P.args, **kwargs: P.kwargs) -> ChatCompletion:
                openai_kwargs = self.openai_kwargs(
                    name=name if name else fn.__name__,  # type: ignore
                    fn=fn,
                    args=args,
                    kwargs=kwargs,
                    base_model=return_base_model,
                )
                return self.client.chat.completions.create(
                    **openai_kwargs,
                    model=model,
                    response_model=return_base_model,  # type: ignore
                )

            @functools.wraps(fn)
            def _distil(*args: P.args, **kwargs: P.kwargs) -> T_Retval:
                resp = fn(*args, **kwargs)
                self.track(
                    fn,
                    args,
                    kwargs,
                    resp,
                    name=name,
                    finetune_format=fine_tune_format,
                )
                return resp

            return _dispatch if mode == "dispatch" else _distil

        if len(args) == 1 and callable(args[0]):
            return _wrap_distil(args[0])  # type: ignore

        return _wrap_distil
```

### `instructor/templating.py` - `handle_templating` function
This excerpt demonstrates how `handle_templating` intelligently processes different message formats for templating.
```python
def handle_templating(
    kwargs: dict[str, Any], mode: Mode, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    # ... (context check and kwargs copy)

    # Handle Cohere's message field
    if "message" in new_kwargs:
        new_kwargs["message"] = apply_template(new_kwargs["message"], context)
        new_kwargs["chat_history"] = [
            process_message(message, context, mode)
            for message in new_kwargs["chat_history"]
        ]
        return new_kwargs

    # ... (message extraction logic)

    if "messages" in new_kwargs:
        new_kwargs["messages"] = [
            process_message(message, context, mode) for message in messages
        ]

    elif "contents" in new_kwargs:
        new_kwargs["contents"] = [
            process_message(content, context, mode)
            for content in new_kwargs["contents"]
        ]

    return new_kwargs
```

## 5. Integration Points
- **Dependencies (`distil.py`)**:
    - `openai`: For interacting with OpenAI's API, particularly for chat completions and function calling.
    - `pydantic`: Used for defining structured return types (`BaseModel`), which are crucial for type enforcement and schema generation for LLMs.
    - `logging`: For tracking and logging function calls and responses.
    - `typing`, `typing_extensions`: For advanced type hinting.
- **Dependencies (`templating.py`)**:
    - `jinja2.sandbox.SandboxedEnvironment`: For safe Jinja2 template rendering.
    - `textwrap.dedent`: For cleaning up multiline strings.
    - `instructor.mode.Mode`: An internal enum likely defining different operational modes for the `instructor` library.
    - `google.genai.types`, `vertexai.generative_models`: Conditional imports for handling specific message formats for Google's GenAI and VertexAI.
- **Dependents**:
    - Both modules are core to the `instructor` library, suggesting they are integrated into its primary function calling and response processing workflows. `distil.py` is likely used by developers to prepare data for fine-tuning custom LLMs or to route function calls through an LLM. `templating.py` would be used internally by the `instructor` library to prepare prompts and messages before sending them to various LLM providers, allowing for dynamic content generation based on context.
