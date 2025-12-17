# Getting Started with `instructor`

## Goal
This tutorial aims to introduce you to the `instructor` library, its purpose, and guide you through setting up a basic client to interact with Large Language Models (LLMs) with structured outputs. By the end of this tutorial, you will understand the core concepts and be able to implement a simple example.

## Prerequisites
To follow this tutorial, you will need:
- Python 3.8 or higher
- `pip` for package installation
- An OpenAI API key (or another supported LLM provider's API key)

To install `instructor` and the OpenAI client, run the following command:
```bash
pip install instructor openai
```

## Introduction to `instructor`
`instructor` is a Python library that enhances the capabilities of LLMs by enabling them to return structured data. Traditionally, LLMs generate free-form text, which can be challenging to parse and integrate into applications. `instructor` addresses this by forcing the LLM to output Pydantic models or other structured formats, making LLM outputs reliable and easy to use.

## Core Concepts

### 1. Structured Output
The primary concept behind `instructor` is ensuring that LLMs produce outputs that conform to a predefined schema (e.g., a Pydantic model). This is achieved by modifying the way requests are sent to the LLM API, guiding the model to generate valid JSON that can be parsed directly into Python objects.

### 2. Patching the Client
`instructor` works by "patching" the LLM client (e.g., OpenAI client). This patching mechanism intercepts the API calls and injects the necessary logic to enforce structured output. This allows you to use your existing LLM client with minimal changes.

### 3. Pydantic Models
Pydantic models are central to `instructor`. You define the desired output structure using Pydantic, and `instructor` uses this definition to constrain the LLM's output. This provides robust data validation and serialization.

## Setting up a Basic Client
Let's set up a basic OpenAI client patched with `instructor`.

First, make sure you have your OpenAI API key set as an environment variable or pass it directly.

```python
import openai
import instructor
from pydantic import BaseModel

# Patch the OpenAI client
# This enables the `response_model` argument in chat.completions.create
client = instructor.patch(openai.OpenAI())

# Define a Pydantic model for the desired output structure
class User(BaseModel):
    name: str
    age: int
    occupation: str

# Now, you can use the patched client to get structured output
def extract_user_info(text: str) -> User:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        response_model=User,
        messages=[
            {"role": "user", "content": f"Extract user information from the following text: {text}"}
        ]
    )
    return response

# Example usage
user_text = "My name is John Doe, I am 30 years old, and I work as a software engineer."
user_info = extract_user_info(user_text)

print(f"Name: {user_info.name}")
print(f"Age: {user_info.age}")
print(f"Occupation: {user_info.occupation}")
```

## Workflow Visualization
Here's a Mermaid diagram illustrating the basic workflow with `instructor`:

```mermaid
graph TD
    A[User Input] --> B{Define Pydantic Model}
    B --> C[Patch LLM Client (instructor.patch)]
    C --> D[Call client.chat.completions.create with response_model]
    D --> E{LLM Generates Structured Output}
    E --> F[instructor Parses and Validates Output]
    F --> G[Returns Pydantic Object]
    G --> H[Application Logic]
```

## Conclusion
`instructor` simplifies the process of integrating LLMs into applications by enforcing structured output. By patching your LLM client and defining Pydantic models, you can ensure that your LLM responses are reliable, validated, and easy to consume. This foundation opens up possibilities for building more robust and predictable AI-powered features.))
