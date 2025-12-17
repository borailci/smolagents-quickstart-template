# Batch Processing and Response Processing with Instructor

## Goal
This tutorial will guide you through using `instructor/batch` for efficient batch processing of requests and `instructor/processing` for robust post-processing of responses. You will learn how to submit batch jobs, retrieve results, and handle structured responses, leveraging Instructor's capabilities for type-safe and unified API interactions across different providers like OpenAI and Anthropic.

## Prerequisites
- Python 3.8+
- `pip install instructor openai anthropic pydantic` (or other relevant provider libraries)
- Basic understanding of Pydantic models.

## Step 1: Understanding Batch Processing (`instructor/batch`)

Batch processing allows you to make multiple API calls efficiently, often with cost savings. `instructor/batch` provides a unified interface to handle this for various providers.

### Core Components:
- `BatchProcessor`: The main class for submitting and retrieving batch jobs.
- `BatchRequest`: Defines the structure of each individual request within a batch.
- `BatchSuccess`, `BatchError`, `BatchResult`: Types for handling successful and erroneous results.
- Utility functions: `filter_successful`, `filter_errors`, `extract_results`, `get_results_by_custom_id` for easy result manipulation.

### Example: Submitting and Retrieving a Batch Job

First, let's define a Pydantic model for our expected output.

```python
from pydantic import BaseModel, Field
from instructor.batch import BatchProcessor, filter_successful, extract_results, BatchRequest
import openai
import json

class UserExtract(BaseModel):
    name: str = Field(description="The name of the person")
    age: int = Field(description="The age of the person")
    occupation: str = Field(description="The occupation of the person")

# Prepare your batch requests. Each request should be a BatchRequest object.
# For OpenAI, this typically means a JSONL file where each line is a JSON object
# representing a request (e.g., messages for a chat completion).

# Let's create a dummy JSONL file for demonstration
requests_data = [
    {"custom_id": "user_1", "method": "POST", "url": "/v1/chat/completions", "body": {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Extract name, age, and occupation from: John Doe is 30 years old and works as a software engineer."}
        ],
        "response_format": {"type": "json_object"}
    }},
    {"custom_id": "user_2", "method": "POST", "url": "/v1/chat/completions", "body": {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Extract name, age, and occupation from: Jane Smith, a 25-year-old doctor."}
        ],
        "response_format": {"type": "json_object"}
    }},
    {"custom_id": "user_3_error", "method": "POST", "url": "/v1/chat/completions", "body": {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "This is an invalid request to simulate an error."}
        ],
        "response_format": {"type": "json_object"}
    }}
]

with open("requests.jsonl", "w") as f:
    for req in requests_data:
        f.write(json.dumps(req) + "\n")

# Initialize the BatchProcessor
# The first argument is the model name for the batch API, the second is your Pydantic response model
processor = BatchProcessor(
    "openai/gpt-4o-mini", # The model that will be used for batching (not necessarily the one in body)
    UserExtract,
    client=openai.Client(), # Pass an initialized OpenAI client
)

# Submit the batch job
print("Submitting batch job...")
batch_id = processor.submit_batch("requests.jsonl")
print(f"Batch job submitted with ID: {batch_id}")

# Retrieve results (this might take some time, depending on the provider and batch size)
# In a real application, you would poll for results or use webhooks.
# For this example, we'll use a blocking retrieve for simplicity.
print("Retrieving batch results (this may take a while)...")
all_results = processor.retrieve_results(batch_id, timeout=300) # Increased timeout

# Process results
successful_extractions = filter_successful(all_results)
errors = filter_errors(all_results)
extracted_users = extract_results(successful_extractions) # Extract Pydantic models from successful results

print("\n--- Successful Extractions ---")
for user in extracted_users:
    print(user.model_dump_json(indent=2))

print("\n--- Errors ---")
for error_result in errors:
    print(f"Error for custom_id {error_result.custom_id}: {error_result.error.message}")

print("\nFull batch job info:")
print(processor.get_batch_job_info(batch_id).model_dump_json(indent=2))

```

## Step 2: Response Processing (`instructor/processing`)

The `instructor/processing` module offers utilities for handling responses, particularly for structured extraction and validation. The `process_response` function is a key component here, allowing you to parse and validate API responses against Pydantic models.

### Core Components:
- `process_response`: A versatile function to convert raw API responses into Pydantic models, handling potential re-asks or validation issues.
- `OpenAISchema`, `openai_schema`: Tools for defining OpenAI function call schemas.
- `Validator`: Custom validation logic.

### Example: Post-processing a Single Response

While `instructor.batch` handles the full cycle, you might need to process individual responses that don't come from a batch job or apply specific validation logic. `process_response` is useful in such scenarios.

```python
from pydantic import BaseModel, Field
from instructor.processing import process_response
import instructor
import openai

# Assume a similar UserExtract model from before
class UserExtractSingle(BaseModel):
    name: str = Field(description="The name of the person")
    age: int = Field(description="The age of the person")
    occupation: str = Field(description="The occupation of the person")

# Patch the OpenAI client to enable Instructor's features
client = instructor.patch(openai.OpenAI())

# Simulate an API response (this would typically come from client.chat.completions.create)
# For demonstration, we'll create a mock response object
class MockChoice:
    def __init__(self, content):
        self.message = MockMessage(content)

class MockMessage:
    def __init__(self, content):
        self.content = content

class MockCompletion:
    def __init__(self, choices):
        self.choices = choices

    def model_dump(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": self.choices[0].message.content
                    }
                }
            ]
        }

# A response that successfully extracts information
successful_raw_response = MockCompletion(choices=[
    MockChoice(content='''{
        "name": "Alice Wonderland",
        "age": 28,
        "occupation": "Storyteller"
    }''')
])

# A response that has malformed JSON (to show error handling)
malformed_raw_response = MockCompletion(choices=[
    MockChoice(content='''{
        "name": "Bob The Builder",
        "age": "forty",
        "occupation": "Builder"
    }''') # age should be int, not string
])

# Process the successful response
try:
    print("\n--- Processing Successful Response ---")
    processed_user = process_response(
        response=successful_raw_response,
        response_model=UserExtractSingle,
        stream=False,
        validation_context=None, # No specific context needed here
    )
    print(processed_user.model_dump_json(indent=2))
except Exception as e:
    print(f"Error processing successful response: {e}")

# Process the malformed response
try:
    print("\n--- Processing Malformed Response ---")
    # Note: process_response with Instructor's patch usually handles re-asking.
    # Here we simulate a direct processing where it might raise a ValidationError.
    processed_user_malformed = process_response(
        response=malformed_raw_response,
        response_model=UserExtractSingle,
        stream=False,
        validation_context=None,
    )
    print(processed_user_malformed.model_dump_json(indent=2))
except Exception as e:
    print(f"Error processing malformed response: {e}")

```

## Step 3: Workflow Visualization

Here's a diagram illustrating the general flow of batch processing and subsequent response handling.

```mermaid
graph TD
    A[Start] --> B(Define Pydantic Models)
    B --> C{Prepare Batch Requests}
    C -- Create requests.jsonl --> D[Initialize BatchProcessor]
    D --> E(Submit Batch Job)
    E --> F[Batch Job ID]
    F --> G{Wait for Batch Completion / Poll}
    G --> H[Retrieve Batch Results]
    H --> I{Filter Successful/Errors}
    I -- Successful --> J[Extract Structured Data]
    I -- Errors --> K[Handle Errors]
    J --> L[Process Extracted Data (e.g., `process_response`)]
    L --> M[Final Structured Output]
    K --> M
    M --> N[End]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#ccf,stroke:#333,stroke-width:2px
    style D fill:#ccf,stroke:#333,stroke-width:2px
    style E fill:#ccf,stroke:#333,stroke-width:2px
    style F fill:#ccf,stroke:#333,stroke-width:2px
    style G fill:#ccf,stroke:#333,stroke-width:2px
    style H fill:#bbf,stroke:#333,stroke-width:2px
    style I fill:#ccf,stroke:#333,stroke-width:2px
    style J fill:#ccf,stroke:#333,stroke-width:2px
    style K fill:#fbb,stroke:#333,stroke-width:2px
    style L fill:#bbf,stroke:#333,stroke-width:2px
    style M fill:#ccf,stroke:#333,stroke-width:2px
    style N fill:#f9f,stroke:#333,stroke-width:2px
```

## Conclusion

You've learned how to leverage `instructor/batch` for efficient and cost-effective processing of multiple requests and `instructor/processing` for robust post-processing of responses, ensuring type safety and structured data extraction. These tools streamline your interactions with LLM APIs, making it easier to build reliable and scalable applications. Enjoy building intelligent applications with Instructor!