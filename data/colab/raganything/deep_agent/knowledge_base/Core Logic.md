'''
# Core Logic Analysis: `raganything` Package

## 1. Overview

The `raganything` package is a comprehensive, all-in-one Retrieval-Augmented Generation (RAG) system designed for multimodal content. Built on top of the `lightrag` library, it provides a complete pipeline for parsing documents, processing both text and modal content (images, tables, equations), inserting them into a knowledge graph, and querying the indexed information. The system is highly configurable and extensible, allowing developers to integrate their own language models (LLMs), vision models, and embedding functions.

The core logic is structured around a central `RAGAnything` class that combines functionality from several mixins, principally `ProcessorMixin` for content processing and `QueryMixin` for handling user queries.

## 2. File-by-File Analysis

### `raganything/raganything.py`

- **Purpose**: This file defines the main `RAGAnything` class, which serves as the primary entry point and orchestrator for the entire system. It integrates all the different components, including parsing, processing, batch operations, and querying.
- **Key Components**:
  - `RAGAnything(QueryMixin, ProcessorMixin, BatchMixin)`: A dataclass that initializes the system. It manages the configuration (`RAGAnythingConfig`), the lifecycle of the `lightrag` instance, and the various modal processors.
  - **Initialization (`__post_init__`, `_ensure_lightrag_initialized`)**: Handles the setup of the configuration, logger, document parser (`MineruParser` or `DoclingParser`), and the lazy initialization of the `LightRAG` instance and modal processors. It requires the user to provide an `llm_model_func` and `embedding_func` if a `lightrag` instance is not provided pre-initialized.
  - **Processor Management (`_initialize_processors`)**: Dynamically creates instances of `ImageModalProcessor`, `TableModalProcessor`, and `EquationModalProcessor` based on the user's configuration. A `GenericModalProcessor` is always included as a fallback.

### `raganything/base.py`

- **Purpose**: This file provides a basic enumeration for tracking the status of documents during the ingestion process.
- **Key Components**:
  - `DocStatus(str, Enum)`: An enumeration that defines the possible states of a document, such as `READY`, `PROCESSING`, `PROCESSED`, and `FAILED`. This is used to manage the processing pipeline and avoid redundant work.

### `raganything/processor.py`

- **Purpose**: This file contains the `ProcessorMixin` class, which encapsulates the logic for parsing files and processing their content for insertion into the `lightrag` knowledge graph.
- **Key Components**:
  - `ProcessorMixin`: A class that provides the core content processing functionalities.
  - **Document Parsing (`parse_document`)**: Detects the file type (PDF, image, Office document) and uses the configured parser (`MineruParser` or `DoclingParser`) to extract a list of content blocks. It includes a caching mechanism (`_get_cached_result`, `_store_cached_result`) to avoid re-parsing unchanged files.
  - **Content Processing (`_process_multimodal_content`, `process_file_or_folder`)**: This is the main processing pipeline. It first separates the parsed content into pure text and multimodal items (images, tables, etc.). The text is inserted directly into `lightrag`. The multimodal content is then processed by specialized modal processors to generate descriptive captions, which are then inserted as separate but linked nodes in the knowledge graph.

### `raganything/query.py`

- **Purpose**: This file defines the `QueryMixin` class, which adds sophisticated query capabilities to the `RAGAnything` object.
- **Key Components**:
  - `QueryMixin`: A class that provides methods for querying the indexed data.
  - **Text Query (`aquery`)**: A method for performing standard text-based queries. It directly utilizes the underlying `lightrag.aquery()` method.
  - **Multimodal Query (`aquery_with_multimodal`)**: This method enhances a user's text query with descriptions of provided multimodal content (e.g., an image or table). It generates a more detailed prompt that is then fed to the standard query method.
  - **VLM-Enhanced Query (`aquery_vlm_enhanced`)**: An advanced query mode that first retrieves context from the RAG system. It then finds image paths within that context, replaces them with their base64-encoded data, and sends the entire context (text and images) to a Vision Language Model (VLM) for a more informed answer.

## 3. Public Interface & Integration

The primary public interface is the `RAGAnything` class. A developer would typically instantiate this class, providing it with the necessary model functions, and then call its methods to process documents and ask questions.

**Integration Points**:
- **Model Functions**: The system is decoupled from specific model implementations. The user must provide:
  - `llm_model_func`: A callable function for text generation and analysis.
  - `embedding_func`: A callable function to generate text embeddings.
  - `vision_model_func`: (Optional) A callable function for image analysis, required for VLM-enhanced queries and describing images.
- **LightRAG**: The `raganything` package is a high-level wrapper around `lightrag`. An initialized `LightRAG` instance can be passed in directly, or `RAGAnything` can initialize one on behalf of the user.
- **Parsers**: The system uses `MineruParser` or `DoclingParser` for document analysis. These must be installed in the environment.

## 4. Use Cases

### Use Case 1: Processing a Document and Asking a Question

```python
# Assumes llm_func, embedding_func are defined
from raganything import RAGAnything
import asyncio

async def main():
    rag = RAGAnything(
        llm_model_func=llm_func, 
        embedding_func=embedding_func
    )

    # Process a local PDF file
    await rag.process_file("path/to/my_document.pdf")

    # Ask a question related to the document
    answer = await rag.aquery("What is the main conclusion of the document?")
    print(answer)

asyncio.run(main())
```

### Use Case 2: Multimodal Query with an Image

```python
# Assumes rag object is initialized as in Use Case 1
import asyncio

async def query_with_image():
    answer = await rag.aquery_with_multimodal(
        query="Describe the key elements in this image.",
        multimodal_content=[{
            "type": "image",
            "img_path": "path/to/my_image.jpg"
        }]
    )
    print(answer)

asyncio.run(query_with_image())
```

## 5. API Reference

Below is a summary of the key public methods available on the `RAGAnything` class, primarily from the `ProcessorMixin` and `QueryMixin`.

| Method Signature | Description |
| --- | --- |
| `async def process_file(file_path: str, output_dir: str = None, **kwargs) -> Dict` | **(From `BatchMixin` - Assumed)** Processes a single file. Parses the document, inserts text content, and processes multimodal content. |
| `async def process_folder(folder_path: str, **kwargs) -> List[Dict]` | **(From `BatchMixin` - Assumed)** Processes all supported files within a folder, potentially recursively. |
| `async def parse_document(file_path: str, output_dir: str = None, parse_method: str = None, **kwargs) -> Tuple[List[Dict], str]` | Parses a single document and returns the extracted content list and a document ID. Caching is supported. |
| `async def aquery(query: str, mode: str = "mix", system_prompt: str = None, **kwargs) -> str` | Executes a pure text-based query against the indexed data using the configured `LightRAG` instance. |
| `async def aquery_with_multimodal(query: str, multimodal_content: List[Dict[str, Any]] = None, mode: str = "mix", **kwargs) -> str` | Executes a query enhanced with user-provided multimodal content (images, tables). It generates descriptions of the content to enrich the query prompt. |
| `async def aquery_vlm_enhanced(query: str, mode: str = "mix", system_prompt: str = None, **kwargs) -> str` | Performs a VLM-enhanced query. Retrieves context, finds image paths, and sends the text and image data to a vision model for a comprehensive answer. |
| `def update_config(**kwargs)` | Updates the `RAGAnythingConfig` with new values at runtime. |
| `def get_config_info() -> Dict[str, Any]` | Returns a dictionary containing the current configuration of the `RAGAnything` instance. |

'''