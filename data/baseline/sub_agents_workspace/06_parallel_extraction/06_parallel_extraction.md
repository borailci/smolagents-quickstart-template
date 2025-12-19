# Parallel Extraction with Instructor

## 1. Goal
In this tutorial, you will learn how to use Instructor's `Parallel` feature to extract multiple different Pydantic models from a single LLM API call. This allows for efficient extraction of diverse data points simultaneously, streamlining your interaction with large language models.

## 2. Prerequisites
- Python 3.9+
- Basic understanding of Pydantic models
- `instructor` library installed (`pip install instructor pydantic openai`)

## 3. Architecture
At a high level, the process involves defining multiple Pydantic models, wrapping them in `Iterable` for `ParallelModel`, sending a prompt to the LLM, and then iterating through the extracted models.

```mermaid
graph LR
    A["User Input (Text)"] -->|Prompt| B(LLM with Instructor) 
    B -->|Tool Calls (Multiple Models)| C["ParallelModel(Iterable[Model1 | Model2])"]
    C -->|Extracted Pydantic Models| D["Application Logic"]
```

## 4. Step 1: Define Your Pydantic Models
First, we need to define the Pydantic models that represent the different types of structured data we want to extract. For this example, let's imagine we want to extract information about a `User` and a `Product` from a single piece of text.

```python
from pydantic import BaseModel
from typing import Iterable, Union

class User(BaseModel):
    name: str
    age: int
    email: str

class Product(BaseModel):
    name: str
    price: float
    currency: str

# We'll use these models with ParallelModel
# For example: Iterable[User | Product]
```

## 5. Step 2: Use `ParallelModel` for Extraction
Now, we'll use `instructor` to patch our OpenAI client and then use `ParallelModel` to tell the LLM to extract instances of either `User` or `Product` from the input text. `ParallelModel` takes an `Iterable` of `Union` types, allowing you to specify all possible models you want to extract.

```python
import instructor
from openai import OpenAI

# Patch the OpenAI client
client = instructor.from_openai(OpenAI())

# Define the prompt that contains information for both models
user_and_product_description = (
    "A user named John Doe, aged 30, with email john.doe@example.com."
    "He recently purchased an item called 'Wireless Headphones' for 99.99 USD."
)

# Perform the parallel extraction
# The LLM will return a list of tool calls, each corresponding to a model
extracted_data = client.chat.completions.create(
    model="gpt-4o-mini", # Or any other suitable model
    response_model=Iterable[Union[User, Product]],
    messages=[
        {
            "role": "user",
            "content": user_and_product_description,
        }
    ],
)

print("Extracted Data:")
for item in extracted_data:
    print(item)

# Expected Output (order might vary):
# User(name='John Doe', age=30, email='john.doe@example.com')
# Product(name='Wireless Headphones', price=99.99, currency='USD')
```

## 6. Conclusion
You've successfully used `instructor`'s `Parallel` feature to extract multiple different Pydantic models from a single LLM call. This technique is incredibly powerful for scenarios where you need to parse diverse entities from unstructured text efficiently. You can extend this by adding more complex Pydantic models and handling various extraction scenarios based on your application's needs.