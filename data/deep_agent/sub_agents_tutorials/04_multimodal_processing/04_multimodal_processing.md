'''
# Handling Multimodal Content in RAG-Anything

## 1. Synopsis

In the real world, documents are rarely just plain text. They are rich, complex, and filled with images, tables, charts, and even equations. Traditional Retrieval-Augmented Generation (RAG) systems often struggle with this multimodal content, treating it as a black box or ignoring it altogether. This leads to incomplete knowledge bases and inaccurate answers.

This tutorial will guide you through how **RAG-Anything** tackles this challenge head-on. You will learn how to use its powerful multimodal processing pipeline to analyze images and tables, generate rich textual descriptions, and integrate them seamlessly into a queryable knowledge graph. By the end, you'll understand how to build a RAG system that understands the *whole* document, not just the text.

**Goal**: Learn how `modalprocessors.py` uses Vision-Language Models (VLMs) to enrich a knowledge base with descriptions of images and tables, leading to more accurate and context-aware query responses.

## 2. Prerequisites

Before we begin, ensure you have the following:

- Python 3.9+
- A working `RAGAnything` installation (`pip install raganything`)
- Access to:
    - A standard Large Language Model (LLM) for text analysis (e.g., GPT-4).
    - A Vision-Language Model (VLM) for image analysis (e.g., GPT-4o, LLaVA).
    - An embedding model (e.g., `text-embedding-ada-002`).

## 3. Architecture

The magic behind RAG-Anything's multimodal capability lies in its specialized `modalprocessors`. When a document is processed, the content is first parsed and separated into text and non-text (modal) blocks. While text is indexed directly, modal blocks are routed to the appropriate processor.

Here’s a visual overview of the process:

```mermaid
graph TD
    A["Input Document (.pdf, .docx)"] --> B{MineruParser};
    B --> C["Structured Content (Text, Image, Table)"];
    C --> D(ProcessorMixin);
    D --> |Text| E["Text Chunks"];
    D --> |Image/Table| F{Modal Processors};
    E --> G[Knowledge Graph];
    F --> H{"ContextExtractor"};
    H --> |"Surrounding Text"| E;
    F --> I{Vision-Language Model (VLM)};
    I --> |"Rich Description"| F;
    F --> |"Enriched Node"| G;
    J["User Query"] --> K{Query Engine};
    K --> G;
    G --> L["Contextually-Aware Answer"];
```

As the diagram shows, the `ImageModalProcessor` and `TableModalProcessor` don't just analyze the asset in isolation. They use a `ContextExtractor` to pull in surrounding text, providing crucial context to the VLM. The resulting rich description is then added to the knowledge graph, creating a powerful link between the visual element and its textual meaning.

## 4. Implementation Steps

Let's walk through a practical example of processing a document containing both an image and a table.

### Step 1: Initialize `RAGAnything`

First, we need to configure and initialize the `RAGAnything` orchestrator. This involves providing the necessary model functions for language, vision, and embeddings. For this example, we'll assume you have functions `llm_func`, `vision_func`, and `embed_func` that wrap your chosen models.

```python
import asyncio
from raganything import RAGAnything

# Assume these functions are defined to call your models
# from my_models import llm_func, vision_func, embed_func

async def main():
    # 1. Initialize the system with your model functions
    # RAGAnything will use the vision_model_func for images and the
    # llm_model_func for tables by default.
    rag_system = RAGAnything(
        llm_model_func=llm_func, 
        vision_model_func=vision_func, 
        embedding_func=embed_func
    )

    # This step is crucial to set up the underlying LightRAG instance
    # and all the processors.
    await rag_system._ensure_lightrag_initialized()
    
    print("RAG-Anything is initialized and ready.")

# To run in a Jupyter notebook or script:
# await main()
```

***Verification***:
After running this code, you should see the log message: `RAG-Anything is initialized and ready.` You can also inspect the `rag_system.modal_processors` dictionary to see the initialized processors:

```python
print(rag_system.modal_processors.keys())
# Expected Output: dict_keys(['image', 'table', 'equation', 'generic'])
```

### Step 2: Process a Multimodal Document

Now for the core of the process. The `process_document_complete` method orchestrates the entire pipeline: parsing, content separation, and processing. When it encounters an image or a table, it automatically invokes the corresponding modal processor.

Behind the scenes, the `ImageModalProcessor` (or `TableModalProcessor`) does the following:
1.  **Receives the asset**: e.g., a base64-encoded image or a markdown string for a table.
2.  **Extracts Context**: Calls the `ContextExtractor` to find nearby text from the document. This might include captions or relevant paragraphs.
3.  **Generates a Description**: Sends the asset and its context to the specified VLM (`vision_model_func` for images, `llm_model_func` for tables) with a carefully crafted prompt (from `raganything/prompt.py`).
4.  **Creates an Enriched Node**: The generated description is then added as a new, queryable text chunk in the knowledge graph, linked to the original document.

Let's process a sample PDF file named `financial_report.pdf`.

```python
async def process_doc(rag_system):
    # 2. Process a document containing images and tables
    # This single call handles everything: parsing, text indexing, 
    # and multimodal analysis.
    file_path = "path/to/your/financial_report.pdf"
    result = await rag_system.process_document_complete(file_path)

    if result["success"]:
        print(f"Successfully processed {file_path}")
        print(f"Text chunks created: {result['text_chunks_count']}")
        print(f"Modal chunks created: {result['modal_chunks_count']}")
    else:
        print(f"Failed to process {file_path}: {result['error']}")

# Assuming rag_system is the initialized system from Step 1
# await process_doc(rag_system)
```

***Verification***:
Look for logs from `modalprocessors.py`. You should see messages indicating that the image and table processors are running and generating descriptions. The final output will confirm the number of text and modal chunks created.

`INFO: Successfully processed path/to/your/financial_report.pdf`
`INFO: Text chunks created: 50`
`INFO: Modal chunks created: 2` (e.g., one for an image, one for a table)

### Step 3: Query the Enriched Knowledge Graph

Now that our knowledge graph contains detailed descriptions of the images and tables, we can ask questions that would have been impossible before.

```python
async def run_query(rag_system):
    # 3. Ask a question that requires understanding the table data
    query_text = "What was the total revenue in the last quarter according to the summary table?"
    
    print(f"\nQuerying: {query_text}")
    answer = await rag_system.aquery(query_text)
    
    print("\nAnswer:")
    print(answer.answer_text)

# Assuming rag_system has processed the document
# await run_query(rag_system)
```

Because the `TableModalProcessor` extracted the table, converted it to a structured format, and had an LLM summarize it, the RAG system can now directly answer questions about its contents. The same applies to images. If the report contained a bar chart of revenue, you could ask, "Which product had the highest revenue in the bar chart?" and the VLM-generated description would provide the answer.

## 5. Common Pitfalls

- **Missing Model Functions**: Forgetting to pass `vision_model_func` to the `RAGAnything` constructor is a common mistake. If it's missing, the system will fall back to `llm_model_func`, which will fail for images. Ensure all required model functions are provided.
- **Incorrect Parser Installation**: The system relies on `mineru-parser` by default. If it's not installed correctly (`pip install "mineru-parser[all]"`), the entire process will fail at the first step. Use `rag_system.check_parser_installation()` to verify.
- **API Rate Limits**: Multimodal models can be slow and expensive. Processing large documents with many images can lead to API rate limit errors or high costs. Consider enabling caching and processing documents in batches.

## 6. Challenge Yourself

**Task**: Extend the system to handle a new modality: **audio files**.

1.  **Create a New Processor**: Create an `AudioModalProcessor` class in a new file, inheriting from `BaseModalProcessor`.
2.  **Implement `generate_description_only`**: Use a speech-to-text model (like OpenAI's Whisper) as your `modal_caption_func`. This function should take the audio file path, transcribe it, and return the transcription as the "description".
3.  **Integrate the Processor**: In your main script, modify the `_initialize_processors` step to include your new `AudioModalProcessor` in the `modal_processors` dictionary, keyed by "audio".
4.  **Test It**: Process an audio file (`.mp3`, `.wav`) and ask a question about its content.

This challenge will test your understanding of the processor framework and how to integrate new AI capabilities into the RAG-Anything pipeline.
'''