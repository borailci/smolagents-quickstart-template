
# Working with Other LLM Providers

## 1. Goal

This tutorial demonstrates how to use `instructor` with Large Language Models (LLMs) other than OpenAI. While `instructor` provides deep integration with OpenAI's APIs, its architecture is provider-agnostic. We will learn how to wrap other clients, such as those from Anthropic and Google, to enable the same powerful, structured data extraction capabilities.

## 2. Prerequisites

Before you begin, ensure you have the necessary libraries and API keys:

1.  **`instructor` Library**: If you haven't already, install it:
    ```bash
    pip install instructor
    ```

2.  **Provider-Specific Libraries**: You need to install the SDK for the provider you want to use. `instructor` includes optional dependency groups for this.

    *   **For Anthropic**:
        ```bash
        pip install instructor[anthropic]
        ```

    *   **For Google Gemini**:
        ```bash
        pip install instructor[google-genai]
        ```

3.  **API Keys**: You must have an API key for the service you are using. Set it as an environment variable:
    ```bash
    export ANTHROPIC_API_KEY="your-anthropic-api-key"
    # or
    export GOOGLE_API_KEY="your-google-api-key"
    ```

## 3. Architecture: The Factory Pattern

`instructor` uses a factory function pattern (`from_anthropic`, `from_gemini`, etc.) to adapt third-party clients. This pattern wraps a provider's native client, patching its request-making method (e.g., `create`) to inject `instructor`'s structured data logic.

Here’s a conceptual overview of the process:

```mermaid
graph TD
    A["User instantiates native client (e.g., `anthropic.Anthropic()`)"] --> B["Pass client to `instructor` factory<br/>(e.g., `instructor.from_anthropic(client)`)"];
    B --> C["Factory patches the client's core method<br/>(e.g., `.messages.create`)"];
    C --> D["An `instructor.Instructor` instance is returned"];
    D --> E["User calls the patched method<br/>with a `response_model`"];
    E --> F["`instructor` intercepts the call, adds tool definitions<br/>to the API request, and sends it"];
    F --> G["Provider API returns a structured response"];
    G --> H["`instructor` parses and validates the response<br/>into the Pydantic model"];
    H --> I["A validated Pydantic object is returned to the user"];
```

## 4. Implementation Steps

Let's walk through a practical example using Anthropic's Claude.

### Step 1: Using `instructor` with Anthropic

The `from_anthropic` function is the entry point for integrating with Anthropic models. It takes a native `anthropic.Anthropic` or `anthropic.AsyncAnthropic` client and returns a patched `instructor` client.

Here is a complete, runnable example:

```python
import instructor
import anthropic
from pydantic import BaseModel

# 1. Define your desired data structure
class User(BaseModel):
    name: str
    age: int

# 2. Instantiate the native Anthropic client
# Make sure your ANTHROPIC_API_KEY is set
client = anthropic.Anthropic()

# 3. Wrap the client with `instructor.from_anthropic`
# This returns a patched client that can handle the `response_model` parameter
instructor_client = instructor.from_anthropic(
    client,
    mode=instructor.Mode.ANTHROPIC_TOOLS, # Use ANTHROPIC_JSON for older models
)

# 4. Call the patched method with the `response_model`
extracted_user = instructor_client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": "Extract the user from the following text: 'Jason is 25 years old.'",
        }
    ],
    response_model=User, # The magic happens here!
)

# 5. The result is a validated Pydantic object
assert isinstance(extracted_user, User)
print(extracted_user.model_dump_json(indent=2))
```

#### *Verification*

When you run the script, the output will be a clean JSON object, not a raw string from the LLM. This confirms that `instructor` successfully directed the model to provide structured data and parsed it into your Pydantic class.

```json
{
  "name": "Jason",
  "age": 25
}
```

### Step 2: Using `instructor` with Google Gemini

Similarly, `instructor` provides a factory function for Google's Gemini models. 

**Important Note**: The `from_gemini` function is deprecated. The source code recommends using the newer `from_genai` function, which works with a `genai.Client` instance rather than a `genai.GenerativeModel`. The following example uses the modern approach.

```python
import instructor
from google import generativeai as genai
from pydantic import BaseModel

# 1. Define your data structure
class SearchQuery(BaseModel):
    query: str
    limit: int

# Configure the Gemini client
# Make sure your GOOGLE_API_KEY is set
genai.configure()

# 2. Use `from_provider` for a simple setup
client = instructor.from_provider(
    provider="google", 
    model="gemini-1.5-flash",
    mode=instructor.Mode.GEMINI_TOOLS
)

# 3. Call the `create` method with your response model
resp = client.create(
    messages=[
        {
            "role": "user",
            "content": "Search for 'pydantic v2' with a limit of 5 results.",
        }
    ],
    response_model=SearchQuery,
)

assert isinstance(resp, SearchQuery)
print(resp.model_dump_json(indent=2))
```

#### *Verification*

Running the code will produce the structured `SearchQuery` object, demonstrating successful extraction with Gemini.

```json
{
  "query": "pydantic v2",
  "limit": 5
}
```

## 5. Common Pitfalls

1.  **Mismatched Mode**: Each provider requires a specific `instructor.Mode`. Using the wrong mode will result in an error. 
    *   For Anthropic, use `instructor.Mode.ANTHROPIC_TOOLS` (recommended) or `instructor.Mode.ANTHROPIC_JSON`.
    *   For Gemini, use `instructor.Mode.GEMINI_TOOLS` or `instructor.Mode.GEMINI_JSON`.
    The `from_anthropic` function will raise a `ModeError` if you supply an incompatible mode.

2.  **Missing Dependencies**: Forgetting to `pip install instructor[anthropic]` or `instructor[google-genai]` will lead to `ImportError` when you try to instantiate the native clients.

3.  **API Key Not Set**: Ensure your provider's API key is correctly exported as an environment variable. Otherwise, the native client will fail to initialize.

## 6. Challenge Yourself

Now that you know how to wrap different providers, try this:

1.  Modify the Anthropic example to extract a `list[User]` instead of a single `User`. You will need to change the `response_model` and update the prompt to include multiple users (e.g., "Jason is 25 and Maria is 30.").
2.  Explore the `instructor.Mode.ANTHROPIC_JSON` mode. What happens if you switch from `ANTHROPIC_TOOLS`? Does the model's reliability change? (Note: `ANTHROPIC_TOOLS` is generally more robust).
3.  Take a look at the `instructor/providers/` directory in the `instructor` source code. Can you identify another provider, like Cohere or Mistral, and write a similar script to extract a Pydantic object using their respective client?
