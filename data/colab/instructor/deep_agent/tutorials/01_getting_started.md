# Getting Started with Instructor

## 1. Synopsis

Large Language Models (LLMs) are powerful, but their unstructured text output can be difficult to work with in production applications. When you need reliable, structured data—like JSON—you often have to write cumbersome parsing and validation logic.

`instructor` solves this problem by seamlessly bridging the gap between LLMs and Pydantic models. It patches your LLM client (like OpenAI's) to directly return structured, validated data that conforms to your Pydantic schema.

This tutorial will guide you through the basics of installing `instructor`, patching an OpenAI client, and extracting a Pydantic model from an LLM call.

## 2. Prerequisites

Before you begin, you'll need to install the `instructor` and `openai` libraries. You will also need an OpenAI API key.

```bash
pip install instructor openai
```

## 3. Architecture

The core of `instructor` is a `patch` function that modifies your LLM client. When you make an API call with the patched client, `instructor` injects instructions into the request, guiding the LLM to produce output matching your desired Pydantic schema. It then parses the response and validates it, returning a ready-to-use Pydantic object.

Here's a diagram illustrating the flow:

```mermaid
graph TD
    A["Developer Defines Pydantic Model (e.g., User)"] --> B{instructor.patch(client)};
    B --> C["Patched OpenAI Client"];
    C --> D{"client.chat.completions.create(\n  response_model=User,\n  messages=[...])"};
    D --> E["LLM API Call (with schema)"];
    E --> F["LLM Response (JSON data)"];
    F --> G["Response Parsing & Pydantic Validation"];
    G --> H["Validated User Object"];
H --> I["Application Logic"];
```

## 4. Implementation Steps

### Step 1: Define Your Pydantic Model

First, define the data structure you want to extract. For this example, we'll create a simple `User` model with `name` and `age` fields.

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int
```

*Verification*: This code defines a standard Pydantic model. No external verification is needed at this stage.

### Step 2: Patch the OpenAI Client and Make the Call

Next, we'll import `instructor`, `openai`, and our `User` model. We then apply `instructor.patch` to an instance of the `openai.OpenAI` client. This patched client now has a `response_model` argument in its `chat.completions.create` method.

```python
import instructor
import openai
from pydantic import BaseModel

# 1. Define your Pydantic model
class User(BaseModel):
    name: str
    age: int

# 2. Patch the OpenAI client
# Make sure to configure your OPENAI_API_KEY environment variable
client = openai.OpenAI()

# The patch is applied automatically when you create an instructor client
instr_client = instructor.from_openai(client)

# 3. Make the call with the response_model parameter
user = instr_client.chat.completions.create(
    model="gpt-3.5-turbo",
    response_model=User,
    messages=[
        {"role": "user", "content": "Extract Jason, who is 25 years old."},
    ]
)

# 4. Use the validated Pydantic object
assert isinstance(user, User)
print(f"Name: {user.name}, Age: {user.age}")
# > Name: Jason, Age: 25
```

*Verification*: When you run this script, `instructor` will handle the interaction with the OpenAI API and return a `User` object. The output will be:

```
Name: Jason, Age: 25
```

## 5. Common Pitfalls

- **Forgetting to Patch**: A common mistake is to call `client.chat.completions.create` on the original, unpatched OpenAI client. Make sure you are using the client returned by `instructor.from_openai`.
- **Incorrect Model Inheritance**: The `response_model` must be a class that inherits from `pydantic.BaseModel`.
- **API Key Not Set**: Ensure your `OPENAI_API_KEY` environment variable is correctly configured, or you will get an authentication error from the OpenAI client.

## 6. Challenge Yourself

To solidify your understanding, try extending the `User` model. Add a new field, such as `role: str`, and modify the prompt in the `messages` list to include this information (e.g., "Extract Jason, who is a 25 year old software engineer."). Then, update the print statement to display the new `role` field.