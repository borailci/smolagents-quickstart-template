
# Direct Multimodal Content Processing in RAGAnything

## 1. Goal

This tutorial demonstrates how to use RAGAnything to process multimodal content directly, without needing to parse a full document. This is particularly useful when you have pre-existing content, such as images, tables, or text chunks from a database or API, and you want to ingest them into the RAG system for querying.

We will show how to use the specialized modal processors (`ImageModalProcessor`, `TableModalProcessor`, etc.) to process individual pieces of content and add them to the knowledge graph.

## 2. Prerequisites

- The `raganything` package installed. You can install it with `pip install raganything`.
- Access to an LLM provider (like OpenAI) for generating captions and embeddings.

## 3. Architecture

While RAGAnything provides a complete end-to-end document processing pipeline, it is built on a modular architecture that allows for direct content injection. The core of the system is `LightRAG`, which manages the knowledge graph, vector stores, and retrieval processes. Specialized modal processors handle the transformation of raw multimodal content into a format that `LightRAG` can index.

Here's a diagram illustrating the direct content processing workflow:

```mermaid
graph TD
    subgraph "Direct Content Injection"
        A[Raw Content
(Image, Table, Text)] --> B{Modal Processors
(ImageModalProcessor, etc.)};
        B --> C{Content Understanding
(Captioning, Summarization)};
        C --> D[Structured Data
(Chunks, Entities, Relations)];
    end

    subgraph "LightRAG Core"
        D --> E(Text Chunks DB);
        D --> F(Vector DB);
        D --> G(Knowledge Graph);
    end

    H[User Query] --> I{Retriever};

    subgraph "Retrieval"
        E --> I;
        F --> I;
        G --> I;
    end

    I --> J[Synthesizer
(LLM)];
    J --> K[Answer];

```

In this workflow, we bypass the initial document parsing stage and directly use the modal processors to prepare our content for indexing.

## 4. Implementation

Let's walk through a Python example of how to process an image and a table directly.

### Step 1: Initialize `LightRAG`

First, we need to set up a `LightRAG` instance. This object orchestrates the different components of the RAG system.

```python
import asyncio
from lightrag import LightRAG
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

# Set up your API keys and base URLs as needed
api_key = "YOUR_OPENAI_API_KEY"
base_url = "YOUR_OPENAI_BASE_URL"  # Optional

# Initialize LightRAG
rag = LightRAG(
    working_dir="./rag_storage",
    llm_model_func=lambda prompt, system_prompt=None, history_messages=[], **kwargs: openai_complete_if_cache(
        "gpt-4o-mini",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    ),
    embedding_func=EmbeddingFunc(
        embedding_dim=3072,
        max_token_size=8192,
        func=lambda texts: openai_embed(
            texts,
            model="text-embedding-3-large",
            api_key=api_key,
            base_url=base_url,
        ),
    )
)

# Initialize the storage components
asyncio.run(rag.initialize_storages())
```

### Step 2: Define Modal Captioning Function

The modal processors require a function to generate textual descriptions of non-textual content. For images, this would be a vision model; for tables, a language model that can summarize structured data.

```python
# Define a vision model function for image and table processing
def vision_model_func(
    prompt, system_prompt=None, history_messages=[], image_data=None, messages=None, **kwargs
):
    if messages:
        return openai_complete_if_cache(
            "gpt-4o",
            "",
            system_prompt=None,
            history_messages=[],
            messages=messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
    elif image_data:
        return openai_complete_if_cache(
            "gpt-4o",
            "",
            system_prompt=None,
            history_messages=[],
            messages=[
                {"role": "system", "content": system_prompt}
                if system_prompt
                else None,
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            },
                        },
                    ],
                }
                if image_data
                else {"role": "user", "content": prompt},
            ],
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
    else:
        return rag.llm_model_func(prompt, system_prompt, history_messages, **kwargs)
```

### Step 3: Process Multimodal Content

Now we can instantiate the modal processors and use them to process our content.

```python
import base64
from raganything.modalprocessors import ImageModalProcessor, TableModalProcessor

async def process_multimodal_content():
    # Process an image
    image_processor = ImageModalProcessor(
        lightrag=rag,
        modal_caption_func=vision_model_func
    )

    # Example: Load an image and encode it in base64
    with open("path/to/your/image.jpg", "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')

    print("Processing image...")
    image_chunk_id, image_entity_id = await image_processor.process(
        image_data,
        file_path="path/to/your/image.jpg",
        extract_entities=True
    )
    print(f"Image processed. Chunk ID: {image_chunk_id}, Entity ID: {image_entity_id}")

    # Process a table
    table_processor = TableModalProcessor(
        lightrag=rag,
        modal_caption_func=vision_model_func
    )

    # Example: A table represented as a list of lists
    table_data = [
        ["Product", "Region", "Sales"],
        ["A", "North", "1000"],
        ["B", "South", "1500"]
    ]

    print("\nProcessing table...")
    table_chunk_id, table_entity_id = await table_processor.process(
        table_data,
        file_path="manual_data.py", # A virtual path for the data source
        extract_entities=True
    )
    print(f"Table processed. Chunk ID: {table_chunk_id}, Entity ID: {table_entity_id}")

# Run the processing function
asyncio.run(process_multimodal_content())
```

### Step 4: Query the Content

After processing, the content is indexed and available for querying. You can use the `aquery` method of your `LightRAG` instance to ask questions about the ingested content.

```python
async def run_query():
    # Query about the content of the image and table
    query = "What are the sales figures for the products? Also, describe the image."
    print(f"\nQuerying: {query}")
    result = await rag.aquery(query, mode="hybrid")
    print("\nQuery Result:")
    print(result)

# Run the query function
asyncio.run(run_query())

```

## 5. Conclusion

By using the modal processors directly, you gain fine-grained control over the content that enters your RAG system. This approach is ideal for integrating RAGAnything into existing data pipelines or for applications where you work with discrete pieces of multimodal information rather than complete documents.

This modularity allows you to leverage the powerful indexing and retrieval capabilities of RAGAnything on any content, regardless of its source.
