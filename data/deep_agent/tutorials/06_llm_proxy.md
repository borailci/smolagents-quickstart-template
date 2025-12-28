# Tutorial: LLM Proxy for Advanced Interactions

## 1. Synopsis

In complex AI agent systems, you often need to interact with various Large Language Models (LLMs) from different providers (OpenAI, Azure, Anthropic, etc.). Managing these connections, observing performance, and ensuring consistent data logging can be challenging. A centralized proxy simplifies this by providing a single, unified endpoint for all LLM calls.

The `agentlightning.llm_proxy.LLMProxy` is a powerful component built on `LiteLLM` that acts as a smart router for your LLM requests. It allows you to:

- **Standardize API Calls**: Use the OpenAI SDK format to call any supported model.
- **Centralize Configuration**: Manage all your models and API keys in one place.
- **Enhance Observability**: Automatically capture detailed traces (inputs, outputs, timings, token counts) for every LLM call and persist them to a `LightningStore` for analysis and debugging.
- **Inject Context**: Seamlessly inject distributed tracing identifiers (`rollout_id`, `attempt_id`) into requests for end-to-end observability.

This tutorial will guide you through configuring and running the `LLMProxy` to route requests to an external LLM.

## 2. Prerequisites

- **Python >= 3.10**
- The `agentlightning` package installed. You can install it with the necessary proxy dependencies:
  ```bash
  pip install "agentlightning[litellm]"
  ```
- An API key for an LLM provider, such as OpenAI. For this tutorial, you will need to set it as an environment variable:
  ```bash
  export OPENAI_API_KEY="your-api-key-here"
  ```

## 3. Architecture

The `LLMProxy` sits between your agent logic and the actual LLM providers. It intercepts OpenAI-compatible requests, enriches them with tracing information, and then routes them to the appropriate destination model configured in its settings.

```mermaid
graph TD
    A["Your Application (Agent)"] -- "OpenAI-compatible API Request<br>(e.g., /v1/chat/completions)" --> B{LLMProxy on localhost};

    subgraph LLMProxy Internals
        B -- "Intercepts Request" --> C(RolloutAttemptMiddleware);
        C -- "Injects Tracing Headers<br>(x-rollout-id, x-attempt-id)" --> D(LiteLLM Router);
        D -- "Routes to Correct Model" --> E[External LLM <br> (e.g., OpenAI API)];
        E -- "LLM Response" --> D;
        D -- "Captures Trace Data" --> F(LightningSpanExporter);
        F -- "Writes Spans" --> G[(LightningStore)];
    end

    D -- "Streams Response Back" --> A;

```

## 4. Implementation Steps

### Step 1: Configure and Launch the Proxy

First, we'll write a Python script to configure the `LLMProxy` and start it. The configuration is a list of dictionaries, where each dictionary defines a model that the proxy will expose.

Create a file named `run_proxy.py`:

```python
import asyncio
import os
from agentlightning.llm_proxy import LLMProxy, ModelConfig
from agentlightning.store.memory import InMemoryStore

# 1. Define the models the proxy will serve.
#    We are creating a model named 'gpt-4o-mini-proxy' that routes to OpenAI's 'gpt-4o-mini'.
#    LiteLLM automatically picks up the OPENAI_API_KEY from the environment.
model_list: list[ModelConfig] = [
    {
        "model_name": "gpt-4o-mini-proxy",
        "litellm_params": {
            "model": "gpt-4o-mini",
        },
    }
]

# 2. Instantiate an in-memory store to hold the observability data.
#    In a real application, you might use a persistent store like MongoStore.
store = InMemoryStore()

# 3. Configure and create the LLMProxy instance.
llm_proxy = LLMProxy(
    port=8080,                # The port the proxy will listen on.
    model_list=model_list,    # The list of models we defined.
    store=store,              # The store for saving trace data.
)

async def main():
    print("Starting LLMProxy...")
    await llm_proxy.start()
    print("LLMProxy is running on http://localhost:8080")
    print("Press Ctrl+C to stop.")
    
    # Keep the proxy running until interrupted.
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        print("\nStopping LLMProxy...")
        await llm_proxy.stop()
        print("LLMProxy stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

### Step 2: Interact with the Proxy

Now, let's write a separate client script to send a request to our running proxy. This script will use the standard `openai` library, but will point it to our local proxy endpoint.

Create a file named `run_client.py`:

```python
import openai

# 1. Create a client pointing to the local LLMProxy.
#    The base_url must match the host and port of the running proxy.
client = openai.OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-a-real-key",  # The API key is managed by the proxy, not the client.
)

# 2. Make a request to the model we defined in the proxy's config.
#    Note: We use the proxy's model name 'gpt-4o-mini-proxy'.
print("Sending request to the proxy...")
response = client.chat.completions.create(
    model="gpt-4o-mini-proxy",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain the importance of a centralized LLM proxy in 100 words."},
    ],
    max_tokens=150,
)

# 3. Print the response from the LLM.
print("\nResponse received from LLM:")
print(response.choices[0].message.content)

print(f"\nUsage: {response.usage.prompt_tokens} prompt tokens, {response.usage.completion_tokens} completion tokens.")
```

### Step 3: Run and Verify

1.  **Start the proxy**: Open a terminal, make sure your `OPENAI_API_KEY` is set, and run:
    ```bash
    python run_proxy.py
    ```
    You should see the message: `LLMProxy is running on http://localhost:8080`.

2.  **Run the client**: Open a *second* terminal and run:
    ```bash
    python run_client.py
    ```

*Verification*: The client script will print the response generated by OpenAI's `gpt-4o-mini`, demonstrating that the proxy successfully received the request, forwarded it to OpenAI, and returned the result.

In the background, the `LightningSpanExporter` has captured a full trace of this interaction and saved it to the `InMemoryStore`. You could inspect `proxy.get_store()` to see the collected data.

## 5. Common Pitfalls

- **Incorrect `base_url`**: The most common error is forgetting to set the `base_url` in the `openai` client to point to the proxy's address (`http://localhost:8080/v1`). If you don't, the client will try to contact OpenAI's servers directly.
- **Firewall or Port Conflicts**: Ensure that port `8080` (or whichever port you configure) is not already in use or blocked by a firewall.
- **Missing Environment Variables**: The proxy itself needs the `OPENAI_API_KEY` (or other provider keys) in its environment to be able to authenticate with the downstream LLM service.
- **Model Name Mismatch**: The `model` parameter in the client's `create` call must exactly match a `model_name` you defined in the proxy's `model_list` (e.g., `"gpt-4o-mini-proxy"`), not the actual model name (e.g., `"gpt-4o-mini"`).

## 6. Challenge Yourself

Modify the `run_proxy.py` script to add a second model from a different provider, such as Anthropic's Claude.

1.  Add another `ModelConfig` to the `model_list` for a Claude model (e.g., `"claude-3-haiku-20240307"`).
2.  You will need to get an Anthropic API key and set it as an environment variable (`ANTHROPIC_API_KEY`).
3.  Modify `run_client.py` to make a second API call, this time targeting the new Claude model name you defined in the proxy.

This will prove your ability to use the proxy as a single gateway for multiple, distinct LLM backends.