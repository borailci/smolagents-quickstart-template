# Tutorial: Advanced Error Handling and Optional Data Extraction

## 1. Synopsis

In real-world applications, extracting structured data from text is often messy. Large Language Models (LLMs) can make mistakes, and the data you're looking for might not always be present. This tutorial demonstrates how to build robust extraction systems using `instructor` that can gracefully handle these challenges.

We will cover two powerful features:
1.  **Automatic Retries with `max_retries`**: How to automatically ask the LLM to correct its own output if it fails to produce a valid Pydantic object.
2.  **Handling Missing Data with `Maybe`**: How to elegantly manage cases where the data you want to extract might not exist in the source text, avoiding validation errors.

## 2. Prerequisites

Before you begin, make sure you have `instructor` and `openai` installed:

```bash
pip install instructor openai
```

## 3. Architecture

Our system will follow a conditional logic path. When we request data from the LLM, it will first attempt to extract the data. If it fails, it will retry. If the data is potentially optional, it will wrap the result in a container that indicates success or failure.

```mermaid
graph TD
    A["User Prompt"] --> B{LLM Extraction with `instructor`};
    B --> C{Is `response_model` valid?};
    C -- No --> D{Retry with `max_retries` > 0?};
    D -- Yes --> B;
    D -- No --> E["Raise ValidationError"];
    C -- Yes --> F{Is data optional (using `Maybe`)?};
    F -- Yes --> G["Return `Maybe(result=..., error=False)` or `Maybe(result=None, error=True)`"];
    F -- No --> H["Return `YourModel(...)`"];
```

## 4. Implementation Steps

### Step 1: Automatic Error Correction with `max_retries`

LLMs don't always get it right on the first try. They might return data in the wrong format or miss a validation rule. Instead of writing complex parsing and correction logic yourself, you can instruct the model to fix its own mistakes.

The `max_retries` parameter in the patched `client.chat.completions.create` method tells `instructor` to automatically re-prompt the LLM if the returned data fails Pydantic validation. The validation error is included in the new prompt, giving the model the context it needs to correct itself.

Let's define a `User` model with a validator that ensures the user's role is one of the allowed options.

```python
import instructor
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

# 1. Define your data model
class User(BaseModel):
    name: str
    role: str

    @field_validator("role")
    def validate_role(cls, v):
        if v not in ["admin", "user"]:
            raise ValueError("Role must be either 'admin' or 'user'")
        return v

# 2. Patch the OpenAI client
client = instructor.patch(OpenAI())

# 3. Make a request with a prompt that might fail
# We set max_retries to 2 to give the model a chance to correct itself.
try:
    user = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user", 
            "content": "Extract the user 'Jason' who is a 'developer'"
        }],
        response_model=User,
        max_retries=2
    )
    print("Successfully extracted user:")
    print(user.model_dump_json(indent=2))
except Exception as e:
    print(f"Failed to extract user after retries: {e}")

```

#### *Verification*

When you run the code above, the first attempt from the LLM will likely fail because `"developer"` is not a valid role. `instructor` will catch the `ValueError` from our validator and automatically send a new request to the LLM, including the error message in the prompt. The model then corrects the role to a valid option.

You will likely see a successful extraction in the output:

```json
{
  "name": "Jason",
  "role": "user"
}
```

### Step 2: Handling Optional Data with `Maybe`

Sometimes, the information you're trying to extract simply isn't in the source text. In these cases, forcing a Pydantic model extraction would result in a validation error. The `instructor.dsl.Maybe` utility provides a clean way to handle this.

`Maybe(YourModel)` creates a new model that wraps `YourModel`. The result will contain either the successfully extracted data in a `result` field or an error flag and a message if the data could not be found.

Let's try to extract user information from two different texts: one that contains the necessary data and one that doesn't.

```python
import instructor
from openai import OpenAI
from pydantic import BaseModel, Field
from instructor.dsl.maybe import Maybe

# 1. Define the core data model
class User(BaseModel):
    name: str = Field(description="The name of the person")
    age: int = Field(description="The age of the person")

# 2. Create a Maybe-wrapped version of the User model
MaybeUser = Maybe(User)

# 3. Patch the OpenAI client
client = instructor.patch(OpenAI())

# 4. Process text that *lacks* the necessary information
text_without_user = "The quick brown fox jumps over the lazy dog."
print(f"Attempting extraction from: ''{text_without_user}''")

maybe_user_fail = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{
        "role": "user",
        "content": f"Extract user details from the following text: {text_without_user}",
    }],
    response_model=MaybeUser,
)

if maybe_user_fail.error:
    print("Extraction failed as expected.")
    print(f"Message: {maybe_user_fail.message}")
else:
    print("Unexpectedly found a user!")

print("\n" + "="*30 + "\n")

# 5. Process text that *contains* the necessary information
text_with_user = "John Doe is 42 years old."
print(f"Attempting extraction from: ''{text_with_user}''")

maybe_user_success = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{
        "role": "user",
        "content": f"Extract user details from the following text: {text_with_user}",
    }],
    response_model=MaybeUser,
)

if not maybe_user_success.error and maybe_user_success.result:
    print("Successfully extracted user:")
    print(maybe_user_success.result.model_dump_json(indent=2))
else:
    print("Extraction failed unexpectedly.")

```

#### *Verification*

Running this script will produce two different outcomes:

1.  **First Case (Failure)**: For the text without a user, the `MaybeUser` model will correctly indicate that no data could be extracted. The output will look like this:

    ```
    Attempting extraction from: ''The quick brown fox jumps over the lazy dog.''
    Extraction failed as expected.
    Message: No user information found in the provided text.
    ```

2.  **Second Case (Success)**: For the text with a user, the `result` field will be populated with a `User` instance:

    ```
    Attempting extraction from: ''John Doe is 42 years old.''
    Successfully extracted user:
    {
      "name": "John Doe",
      "age": 42
    }
    ```

## 5. Common Pitfalls

*   **Over-using `max_retries`**: Be cautious with `max_retries`. If a validation rule is impossible for the model to satisfy, you could end up in a loop of retries that wastes tokens and time. It's best for correcting formatting or minor logical errors, not for fundamental impossibilities.
*   **Ignoring `Maybe`'s Error Message**: The `message` field in a failed `Maybe` extraction is generated by the LLM. It can provide valuable insight into *why* the extraction failed (e.g., "The text mentions a name but no age"). Use this for logging and debugging.

## 6. Challenge Yourself

Combine the concepts from this tutorial. Create a script that tries to extract a `PrivilegedUser` with a `role` field that must be `"superuser"`. Use `Maybe(PrivilegedUser)` as the `response_model` and set `max_retries=2`.

-   Test it with a prompt for a user who is a "super user" (two words).
-   Test it with a prompt for a user who is just a "regular user".
-   Test it with a prompt that has no user information at all.

Observe how `instructor` first retries to fix the role and then, for the last two cases, returns a `Maybe` object indicating failure. This mimics a real-world scenario where you need to be strict about the data you get, but also need to handle cases where the data isn't available.