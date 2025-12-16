# Project Executive Summary

## 1. Architecture Overview
The project encompasses a core library (`toon`) for Typed Object Notation (TOON) serialization/deserialization, a Command Line Interface (CLI) tool for convenient data conversion, and a comprehensive benchmarking suite for evaluating language models and data formats.

*   **TOON Library**: Provides robust functionalities for encoding JavaScript values into TOON format and decoding TOON strings back into JavaScript values. It supports human-readable structured data, including array headers, tabular data, and key folding, with synchronous and asynchronous streaming capabilities.
*   **TOON CLI**: A command-line tool built on the `toon` library for converting data between JSON and TOON formats. It offers flexible input/output options (files, stdin/stdout) and control over formatting, strictness, and key handling.
*   **Benchmarking Suite**: Designed to assess the performance of various language models (e.g., Anthropic, Google, OpenAI) and data serialization formats (TOON, JSON, YAML, XML, CSV) in terms of retrieval accuracy and token efficiency using synthetic and real-world datasets.

## 2. Core Workflows

### 2.1 Data Conversion (TOON Library & CLI)
*   **Encoding**: JavaScript (JSON) data is transformed into the TOON format. This involves recursively processing JSON structures, applying formatting rules (indentation, delimiters), and optionally performing "key folding" for compact representation of nested single-key objects (e.g., `a.b.c: value`).
*   **Decoding**: TOON formatted strings are parsed and converted back into JavaScript (JSON) objects. The process involves granular parsing of TOON syntax elements (keys, values, array headers), managing parsing state, and reconstructing the original data structure, with options for expanding folded paths.
*   **Streaming**: Both encoding and decoding support streaming operations for handling large datasets efficiently.

### 2.2 Performance Benchmarking
*   **Accuracy Benchmark**: Evaluates how accurately language models can extract information from data presented in different formats (TOON, JSON, etc.). It involves constructing prompts with formatted data, querying models, and comparing their responses against ground truth answers, while tracking latency and token usage.
*   **Token Efficiency Benchmark**: Compares the token count of various data formats for representing the same datasets. It formats datasets into different serialization methods (TOON, JSON, YAML, XML, CSV) and calculates the token savings or overhead, aiming to demonstrate TOON's efficiency.

## 3. Implementation Map

### Logic Core
*   **TOON Library (`packages/toon`)**: Contains the primary business logic for TOON encoding (`encode/encoders.ts`, `encode/folding.ts`) and decoding (`decode/decoders.ts`, `decode/parser.ts`). `index.ts` serves as the main entry point, orchestrating these sub-modules.
*   **TOON CLI (`packages/cli/src/conversion.ts`)**: Handles the high-level conversion flow, calling the `toon` library's encode/decode functions and managing input/output streams.
*   **Benchmarking Suite (`benchmarks/src/evaluate.ts`)**: Encapsulates the core evaluation logic for assessing model accuracy, including prompt construction and result comparison.

### Data Layer
*   **TOON Library**: Processes JavaScript `JsonValue` types and produces/consumes TOON formatted strings or iterables of lines.
*   **TOON CLI**: Reads input from files or stdin (JSON or TOON) and writes output to files or stdout (TOON or JSON).
*   **Benchmarking Suite (`benchmarks/src/datasets.ts`)**: Generates and manages synthetic and real-world datasets used for evaluation. Data is typically in JSON format before being formatted for benchmarks.

### Interface
*   **TOON Library**: Exposes a programmatic API via `index.ts` with `encode`, `decode`, and streaming functions for direct integration into applications.
*   **TOON CLI**: Provides a command-line interface for users to interact with the conversion functionalities, accepting arguments for input/output files, conversion modes, and various options (e.g., `--indent`, `--keyFolding`, `--strict`).
*   **Benchmarking Suite**: Interacts with external Language Model APIs (e.g., Anthropic, Google, OpenAI via `@ai-sdk/ai`) for evaluation. It uses `citty` for script orchestration and `consola` for logging, and generates detailed markdown reports.

## 4. Developer Glossary
*   **TOON (Typed Object Notation)**: A human-readable, structured data format for configuration and data interchange, featuring array headers, tabular data, and key folding.
*   **Key Folding**: An optimization in TOON encoding that compactly represents nested single-key objects as a single dot-separated key (e.g., `{ a: { b: "value" } }` becomes `a.b: value`).
*   **Expand Paths**: A TOON decoding option that reconstructs nested objects from folded keys (e.g., `a.b: value` becomes `{ a: { b: "value" } }`).
*   **Token Efficiency**: A metric used in benchmarking to compare how many tokens different data serialization formats require to represent the same data, particularly relevant for language model contexts.
*   **Retrieval Accuracy**: A benchmark metric assessing how correctly a language model can extract specific information from a given dataset formatted in various ways.
*   **`citty`**: A library used for building robust command-line interfaces.
*   **`consola`**: A versatile logger used for displaying messages, warnings, and errors in console applications.