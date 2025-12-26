# Getting Started with Instructor

## 1. Goal

This tutorial will guide you through the installation and basic usage of the `instructor` library. You will learn how to get structured, validated data from a large language model (LLM) using just a few lines of Python code.

## 2. Prerequisites

- Python 3.9+ installed.
- An API key from an LLM provider (e.g., OpenAI, Anthropic, Google). This tutorial will use OpenAI.

## 3. Installation

You can install `instructor` using pip:

```bash
pip install instructor
```

## 4. Architecture

The core idea behind `instructor` is to use Pydantic models to define the structure of the data you want to extract. `instructor` handles the communication with the LLM, validation of the response, and retries, giving you back a clean Pydantic object.

```mermaid
graph TD
    A[You: Define Pydantic Model & Prompt] --> B{instructor};
    B --> C[LLM Provider (e.g., OpenAI)];
    C --> D[LLM Response (JSON)];
    D --> B;
    B --> E[You: Receive Validated Pydantic Object];
```

## 5. Implementation

Let's extract user information from a simple sentence. 

First, you need to define the data structure you want to receive using a Pydantic `BaseModel`.

Then, you create an `instructor` client, patched to your preferred LLM provider. In this case, we use `instructor.from_provider` to easily configure a client for OpenAI's GPT-4o-mini.

Finally, you call the `chat.completions.create` method, passing your Pydantic model to the `response_model` argument. `instructor` takes care of the rest.

Here is a complete, runnable example:

```python
import instructor
from pydantic import BaseModel

# 1. Define the data structure you want to extract
class User(BaseModel):
    name: str
    age: int

# 2. Create a client
# Make sure you have your OPENAI_API_KEY environment variable set
client = instructor.from_provider("openai/gpt-4o-mini")

# 3. Extract the data
user = client.chat.completions.create(
    response_model=User,
    messages=[{"role": "user", "content": "John is 25 years old"}],
)

# The 'user' variable is now a validated Pydantic object
assert isinstance(user, User)
print(f"Name: {user.name}, Age: {user.age}")
# Output: Name: John, Age: 25
```

That's it! You don't need to worry about parsing JSON, validating data types, or handling API errors. `instructor` provides a simple and reliable way to get structured outputs from LLMs.

## 6. Conclusion

In this tutorial, you learned how to install `instructor`, define a Pydantic model for data extraction, and use the `instructor` client to get structured data from an LLM. This is just the beginning; `instructor` offers many more powerful features like streaming, retries with validation, and support for complex nested objects.