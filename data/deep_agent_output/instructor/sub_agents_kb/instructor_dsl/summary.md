# instructor/dsl Analysis

## 1. Overview
The `instructor/dsl` module provides a set of Domain Specific Language (DSL) components designed to extend Pydantic models for more sophisticated interactions with Large Language Models (LLMs). These utilities enable functionalities such as handling citations, processing streaming data into iterable model instances, gracefully managing optional or missing data, executing parallel function calls, and performing partial streaming of model responses.

## 2. Key Components
-   `CitationMixin`: A Pydantic mixin that allows models to extract and validate `substring_quotes` from a given `context`. It ensures that the extracted quotes are present in the provided context, making responses more attributable.
-   `IterableBase`: A base class for processing streaming responses from LLMs, segmenting them into multiple Pydantic model instances. It handles various LLM modes (e.g., Anthropic, Gemini, VertexAI, Mistral) and extracts JSON chunks to construct a stream of model objects.
-   `IterableModel(subtask_class)`: A factory function that dynamically creates an `OpenAISchema` compatible Pydantic model. This generated model can segment multiple instances of `subtask_class` from a streaming response, effectively allowing the LLM to return a list of objects iteratively.
-   `MaybeBase`: A generic Pydantic base model (`result: Optional[T], error: bool, message: Optional[str]`) designed to encapsulate the outcome of a model extraction, indicating whether a result was successfully obtained or if an error occurred.
-   `Maybe(model)`: A factory function that creates a `Maybe` wrapper around a given Pydantic `model`. This is useful for scenarios where the presence of data for a model is uncertain, allowing the LLM to either return the model or an error message.
-   `ParallelBase`: A base class for processing responses containing parallel function calls from LLMs. It dispatches arguments from tool calls to their corresponding Pydantic models for validation.
-   `VertexAIParallelBase`, `AnthropicParallelBase`: Specializations of `ParallelBase` tailored for handling parallel tool calls from VertexAI and Anthropic LLMs, respectively, accounting for their specific response formats.
-   `ParallelModel(typehint: type[Iterable[T]])`: A factory function that creates an instance of `ParallelBase` to handle parallel tool calls, where `typehint` specifies an `Iterable` of Pydantic models that the LLM might call.
-   `VertexAIParallelModel(typehint: type[Iterable[T]])`, `AnthropicParallelModel(typehint: type[Iterable[T]])`: Factory functions for creating specialized parallel model handlers for VertexAI and Anthropic.
-   `PartialBase`: A generic base class for handling partial streaming responses. It dynamically creates a "partial" version of a Pydantic model where all fields are optional, allowing for validation of incomplete JSON objects as they stream in.
-   `Partial(T_Model)`: A generic type hint that transforms a `T_Model` Pydantic model into its partial streaming counterpart. This enables the model to be validated even when only a portion of the JSON data has been received from the LLM.

## 3. Data Flow
Many DSL components, especially `IterableBase` and `PartialBase`, operate by processing streaming JSON responses from LLMs. The general data flow involves:
1.  **Extraction**: `extract_json` (or `extract_json_async`) methods are used to parse raw LLM completion chunks into raw JSON string segments, specific to the LLM provider's streaming format (e.g., OpenAI, Anthropic, Gemini, VertexAI, Mistral).
2.  **Accumulation & Parsing**: These JSON segments are then accumulated and continuously parsed. For `PartialBase`, `from_json` (from `jiter` library) is used for efficient partial JSON parsing.
3.  **Dynamic Model Creation/Validation**: Based on the DSL component, either a new Pydantic model is dynamically created (e.g., by `IterableModel` or `Maybe`) or an existing model is adapted (e.g., `Partial` creates a version of the model with all optional fields).
4.  **Yielding Objects**: As valid (or partially valid) JSON objects are identified, they are validated against the appropriate Pydantic model and yielded as instances, allowing for real-time processing of streaming LLM outputs.

`CitationMixin` operates post-model creation, using Pydantic's `model_validator(mode="after")` to verify that extracted `substring_quotes` are indeed present in the `context` provided during validation, ensuring data integrity and traceability.

`ParallelModel` components function by inspecting the `tool_calls` in an LLM's response. Each tool call's name is mapped to a registered Pydantic model, and its arguments are validated against that model, allowing for multiple structured outputs from a single LLM interaction.

## 4. Code Deep Dive

### `CitationMixin` Usage Example
```python
from pydantic import BaseModel, Field
from instructor import CitationMixin

class User(CitationMixin, BaseModel):
    name: str = Field(description="The name of the person")
    age: int = Field(description="The age of the person")
    role: str = Field(description="The role of the person")

context = "Betty was a student. Jason was a student. Jason is 20 years old"

# Assuming openai.ChatCompletion.create is used with response_model=User
# and validation_context={"context": context}
# user = openai.ChatCompletion.create(...)

# After validation, user.substring_quotes would contain:
# [
#     "Jason was a student",
#     "Jason is 20 years old",
# ]
# These quotes are verified to be present in the `context`.
```

### `Partial` Model Creation
```python
from pydantic import BaseModel, Field
from instructor import Partial

class User(BaseModel):
    name: str
    age: int
    email: str = Field(pattern=r"^[\w.-]+@[\w.-]+\.\w+$")

# Creating a partial version of the User model
PartialUser = Partial[User]

# The PartialUser model would effectively look like:
# class PartialUser(BaseModel):
#     name: Optional[str]
#     age: Optional[int]
#     email: Optional[str]

# This allows for validating incomplete JSON during streaming:
# data_stream = '{"name": "John", "age": 30' # Incomplete JSON
# partial_user_instance = PartialUser.model_validate_json(data_stream, strict=False)
# assert partial_user_instance.name == "John"
# assert partial_user_instance.age == 30
# assert partial_user_instance.email is None
```

## 5. Tutorial Hints
-   **Building Attributable LLM Applications**: A tutorial on using `CitationMixin` to ensure LLM responses are grounded in provided context, enhancing trustworthiness and reducing hallucinations.
-   **Processing Streaming Data with Pydantic**: Demonstrate how `IterableModel` can be used to process continuous streams of data from LLMs, extracting multiple structured objects in real-time.
-   **Graceful Error Handling in LLM Extractions**: A guide on using `Maybe` to design robust data extraction pipelines that can handle cases where expected information might be missing or incomplete.
-   **Advanced LLM Tooling with Parallel Models**: How to leverage `ParallelModel` for orchestrating complex LLM interactions involving multiple concurrent function calls or structured outputs.
-   **Real-time UI Updates with Partial Streaming**: A tutorial showcasing how `Partial` models can be used to validate and display LLM-generated data incrementally as it streams, improving user experience in interactive applications.
