# Tutorial Plan: `raganything`

This document outlines the tutorial series for the `raganything` library. The goal is to provide a comprehensive learning path for developers to build powerful multimodal RAG applications.

## Tutorial Series Checklist

- [ ] **Tutorial 1: Your First Multimodal RAG Pipeline**
    - **Goal**: Guide the user through the simplest end-to-end workflow: ingest a single document and ask a question.
    - **Key Concepts**: `RAGAnything` instantiation, `process_file`, `aquery`.
    - **Files to Create**: `1_first_pipeline.md`

- [ ] **Tutorial 2: Configuring Your RAG System**
    - **Goal**: Explain how to configure `RAGAnything` using `RAGAnythingConfig`.
    - **Key Concepts**: `RAGAnythingConfig`, environment variables, custom model functions (`llm_model_func`, `embedding_func`).
    - **Files to Create**: `2_configuration.md`

- [ ] **Tutorial 3: The `raganything` Processing Pipeline**
    - **Goal**: Detail the internal workings of the content processing pipeline.
    - **Key Concepts**: `ProcessorMixin`, `parse_document`, modal processors (`ImageModalProcessor`, `TableModalProcessor`).
    - **Files to Create**: `3_processing_pipeline.md`

- [ ] **Tutorial 4: Advanced Queries**
    - **Goal**: Showcase the advanced query capabilities of `raganything`.
    - **Key Concepts**: `QueryMixin`, `aquery_with_multimodal`, `aquery_vlm_enhanced`.
    - **Files to Create**: `4_advanced_queries.md`

- [ ] **Tutorial 5: Batch Processing for Large Datasets**
    - **Goal**: Demonstrate how to efficiently ingest large numbers of documents.
    - **Key Concepts**: `BatchMixin`, `process_folder`, `process_documents_with_rag_batch`.
    - **Files to Create**: `5_batch_processing.md`

- [ ] **Tutorial 6: Customizing `raganything`**
    - **Goal**: Show how to extend `raganything` with custom components.
    - **Key Concepts**: Creating custom modal processors, integrating different parsers.
    - **Files to Create**: `6_customization.md`
