
# Streaming Partial Objects

## 1. Goal

This tutorial will guide you through streaming partial objects from a large language model. This is particularly useful when you want to display results to a user as they are being generated, improving the user experience by making the application feel more responsive.

## 2. Prerequisites

- The `instructor` package installed.
- An OpenAI client or any other supported client.

## 3. Architecture

When you request a streaming response, the large language model sends back tokens as they are generated. `instructor` intercepts these tokens, combines them into a coherent JSON string, and then validates them against a partial version of your Pydantic model. This allows you to work with a partially complete, yet valid, data structure at each step of the stream.

```mermaid
graph TD
    A[LLM Stream] -->|Token Chunks| B(Instructor);
    B -->|Partial JSON| C(Partial[YourModel]);
    C -->|Yields| D(Stream of Partially Validated Objects);
```

## 4. Implementation

To stream partial objects, you can use the `Partial` wrapper from `instructor.dsl`. This wrapper makes all fields in your Pydantic model optional, allowing `instructor` to validate the model even when only a subset of the fields have been returned by the model.

Let's define a simple Pydantic model and then stream partial instances of it.

```python
import instructor
import openai
from pydantic import BaseModel

# 1. Define your Pydantic model
class User(BaseModel):
    name: str
    age: int

# 2. Patch the OpenAI client
client = instructor.from_openai(openai.OpenAI())

# 3. Use `Partial[User]` and stream=True
response_stream = client.chat.completions.create(
    model="gpt-4-turbo",
    response_model=instructor.Partial[User],
    messages=[
        {"role": "user", "content": "Extract John Doe, who is 30 years old."},
    ],
    stream=True,
)

print("Streaming partial User objects:")
for partial_user in response_stream:
    print(partial_user)
```

### Expected Output

As the model generates tokens, `instructor` will yield `Partial[User]` objects. The output will look something like this, with each line representing a more complete object than the last:

```
Streaming partial User objects:
name='John' age=None
name='John Doe' age=None
name='John Doe' age=30
```

This demonstrates that you can access the data as it becomes available, field by field, allowing for a real-time updates in your application's UI.
