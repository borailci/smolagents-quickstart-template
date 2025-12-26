
# Advanced Features Analysis

## 1. Overview

This document provides a technical analysis of the advanced features within the `instructor` package, focusing on distillation, multimodal handling, and LLM-powered validation. These modules provide sophisticated capabilities for model training, data validation, and maintaining backwards compatibility.

## 2. File-by-File Analysis

### `instructor/distil.py`

- **Purpose**: This module provides the `Instructions` class and a `distil` decorator to facilitate knowledge distillation and function dispatching to language models. It can capture function calls and their outputs to create datasets for fine-tuning, or it can route function execution to an LLM.

- **Key Components**:
  - `Instructions` **(Class)**: Manages the configuration for distillation, including logging, formatting, and the OpenAI client.
  - `distil` **(Decorator)**: The primary entry point. It wraps a function and, depending on the `mode`, either logs the execution for distillation (`distil` mode) or dispatches the call to an OpenAI model (`dispatch` mode).
  - `track` **(Method)**: A method within the `Instructions` class that logs the function signature, arguments, and response to a specified log handler, formatted for fine-tuning.

### `instructor/multimodal.py`

- **Purpose**: This module serves as a backwards-compatibility layer for multimodal features. It is deprecated and now redirects imports to the `instructor.processing.multimodal` module.

- **Key Components**:
  - `__getattr__(name: str)`: This function intercepts attribute access on the module, issues a `DeprecationWarning`, and attempts to load the requested attribute from `instructor.processing.multimodal`.

### `instructor/validation/llm_validators.py`

- **Purpose**: This module offers powerful, dynamic validation capabilities by using language models to validate Pydantic model fields.

- **Key Components**:
  - `llm_validator` **(Function)**: A higher-order function that creates a custom Pydantic validator. This validator sends the value and a validation rule (the `statement`) to an LLM, which then determines if the value is valid. If not, the LLM provides a reason.
  - `openai_moderation` **(Function)**: Creates a validator that uses the OpenAI Moderation API to check a string for inappropriate content, raising a `ValueError` if the content is flagged.

## 3. Integration Points

- **Verified Dependencies**:
  - `openai`: Used for all interactions with OpenAI APIs, including chat completions and moderations.
  - `pydantic`: The validation features are built as Pydantic validators, and the distillation feature requires Pydantic `BaseModel` for return types.

- **Internal Integration**:
  - The `distil` module relies on `instructor.core.client.Instructor` for making `response_model` predictions when in `dispatch` mode.
  - `llm_validator` integrates with any Pydantic model by being used with `Annotated` types.

## 4. Use Cases

- **`distil.py`**: 
  - **Knowledge Distillation**: Use `@distil` in `distil` mode to automatically generate training data from existing Python functions. By running the functions, you create a log of inputs and outputs that can be used to fine-tune a smaller, cheaper model.
  - **LLM-Powered Functions**: Use `@distil` in `dispatch` mode to create functions that are executed by an LLM, using the function's signature and docstring as a prompt.

- **`validation/llm_validators.py`**:
  - **Complex Validation**: Use `llm_validator` for validation logic that is difficult to express with regular expressions or simple checks, such as "the name must be a full name" or "the summary must be professionally written."
  - **Content Moderation**: Use `openai_moderation` to automatically flag and reject user-provided text that violates OpenAI's usage policies.

## 5. API Reference

| Class / Function | Signature | Description |
|---|---|---|
| `Instructions` | `__init__(self, name, id, log_handlers, finetune_format, indent, include_code_body, openai_client)` | Configures and manages distillation tasks. |
| `Instructions.distil` | `distil(self, *args, name, mode, model, fine_tune_format)` | Decorator for distilling knowledge or dispatching function calls to an LLM. |
| `llm_validator` | `llm_validator(statement, client, allow_override, model, temperature)` | Creates a Pydantic validator that uses an LLM to validate a field. |
| `openai_moderation` | `openai_moderation(client)` | Creates a Pydantic validator that uses the OpenAI Moderation API. |

