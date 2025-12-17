# Getting Started with Instructor

## Goal
This tutorial aims to introduce you to `instructor`, a powerful library for controlling the output of Large Language Models (LLMs) with Python types. You'll learn what `instructor` is, its key features, and how to get started with its installation and basic usage.

## What is Instructor?
`instructor` is a library that extends the capabilities of LLMs by enabling them to return structured data directly as Python types. This means instead of parsing raw text output from an LLM, you can define your expected output as a Pydantic model (or similar), and `instructor` will ensure the LLM's response conforms to that structure. This significantly simplifies integration of LLMs into applications by eliminating the need for complex parsing logic.

### Why use Instructor?
- **Structured Output**: Guarantees that LLMs return data in a predefined, usable format.
- **Type Safety**: Leverage Python's type hinting for robust and error-free LLM integrations.
- **Reduced Parsing Logic**: Eliminate boilerplate code for parsing LLM responses.
- **Enhanced Reliability**: Improve the consistency and predictability of LLM outputs.
- **Streamlined Development**: Focus on application logic rather than output formatting.

## Key Features

### 1. Pydantic Integration
`instructor` works seamlessly with Pydantic, allowing you to define complex data structures for your LLM outputs using familiar Python classes.

### 2. OpenAI, Anthropic, and other LLM API Compatibility
It provides a consistent interface for popular LLM providers, abstracting away their specific API differences when it comes to structured output.

### 3. Automatic Retries and Validation
If an LLM initially fails to produce valid structured output, `instructor` can automatically retry and guide the model until a valid response is generated.

### 4. Function Calling Abstraction
It simplifies the use of function calling features in LLMs, allowing you to directly map LLM outputs to Python functions.

### 5. Streaming Support
`instructor` supports streaming responses, allowing for interactive and real-time data processing.

## Installation

Installing `instructor` is straightforward using `pip`:

```bash
pip install instructor
```

If you want to include support for specific LLM providers, you can install them as extras. For example, for OpenAI:

```bash
pip install instructor[openai]
```

Or for Anthropic:

```bash
pip install instructor[anthropic]
```

## Basic Usage Example

Let's see how `instructor` can be used to extract structured data from a simple text input.

First, define a Pydantic model for the expected output:

```python
from pydantic import BaseModel, Field
import instructor
from openai import OpenAI

class User(BaseModel):
    name: str = Field(description="The name of the user")
    age: int = Field(description="The age of the user")
    occupation: str = Field(description="The occupation of the user")

# Patch the OpenAI client to enable instructor's features
client = instructor.patch(OpenAI())

# Now, when you call chat.completions.create, you can pass response_model
def extract_user_info(text: str) -> User:
    response = client.chat.completions.create(
        model="gpt-4", # or your preferred model
        response_model=User,
        messages=[
            {"role": "user", "content": f"Extract user information from the following text: {text}"}
        ]
    )
    return response

# Example usage
text_data = "John Doe is 30 years old and works as a software engineer."
user_info = extract_user_info(text_data)

print(user_info.name) # Output: John Doe
print(user_info.age)  # Output: 30
print(user_info.occupation) # Output: software engineer
```

## How Instructor Works (Conceptual Diagram)

Here's a simplified flow of how `instructor` intercepts and processes LLM calls to ensure structured output:

```mermaid
graph TD
    A[Your Application] --> B{Call LLM API with `response_model`}
    B --> C(Instructor's Patched Client)
    C --> D{Instruct LLM with Schema & Constraints}
    D --> E[LLM API (e.g., OpenAI)]
    E --> F[Raw LLM Response (JSON/Text)]
    F --> G{Instructor's Validator/Parser}
    G -- Invalid --> D
    G -- Valid --> H[Pydantic Model Instance]
    H --> A
```

## Conclusion

`instructor` significantly simplifies working with LLMs by guaranteeing structured outputs and integrating seamlessly with Python's type system. By patching your LLM client, you can define the exact data shape you expect, making your LLM integrations more robust and easier to manage. Start experimenting with `instructor` today to unlock the full potential of structured LLM interactions!
