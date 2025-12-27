## 1. High-Level Purpose

The project provides a suite of tools for working with TOON (Token-Oriented Object Notation), a data format designed to be more compact and human-readable than JSON. It consists of a core library (`@toon-format/toon`) for encoding and decoding data, and a command-line interface (`@toon-format/cli`) for performing these conversions directly from the terminal. The primary goal is to offer an efficient data serialization format suitable for configuration files, data transfer, and Large Language Model (LLM) prompts where token count is a concern.

## 2. Navigation Guide (Source Map)

| Topic / Component | Description | Source File |
| :--- | :--- | :--- |
| CLI Main Command | Defines the `toon` command, its arguments, and orchestrates the conversion process. | `CLI Core.md` |
| CLI Utilities | Helper functions for the CLI, including I/O streaming and format detection. | `CLI Utils.md` |
| Core Library API | The main public interface for `encode()` and `decode()` functions. | `Toon Core.md` |
| Encoding Internals | The internal logic for converting JavaScript objects into TOON format strings. | `Toon Encoding.md` |
| Decoding Internals | The internal pipeline for parsing TOON strings into a stream of JSON events. | `Toon Decoding.md` |
| Shared Utilities | Low-level functions for string manipulation, validation, and literal detection. | `Toon Shared.md` |

## 3. Key Architecture Modules

*   **`@toon-format/cli` (Command-Line Interface)** (Source: `CLI Core.md`): The user-facing tool built with `citty`. It parses command-line arguments to manage input/output (files or stdin/stdout) and orchestrates the conversion by calling the core library. It determines whether to encode or decode based on flags or file extensions.

*   **`@toon-format/toon` (Core Library)** (Source: `Toon Core.md`): The central package containing the logic for TOON conversion. It exposes high-level functions like `encode()` and `decode()` for simple in-memory operations, as well as streaming APIs (`decodeStream`, `encodeLines`) for handling large datasets efficiently without high memory usage.

*   **Streaming Decoder Pipeline** (Source: `Toon Decoding.md`): The decoder is architected as a multi-stage pipeline. A **scanner** reads the input line-by-line, a **parser** interprets the syntactic meaning of each line, and a **decoder** generates a stream of `JsonStreamEvent` objects. This event-based approach is highly memory-efficient.

*   **Recursive Encoder with Optimizations** (Source: `Toon Encoding.md`): The encoder recursively traverses a JavaScript object. It employs several optimization strategies for compactness, including **key folding** (collapsing `a: { b: 1 }` to `a.b: 1`) and **tabular array encoding** (representing arrays of similar objects as a compact table).

## 4. Common Use Cases

*   **Convert JSON to TOON for Readability** (Source: `CLI Core.md`): Use the CLI to make a large JSON file more compact and easier to read.
    ```sh
    cat data.json | toon > data.toon
    ```

*   **Convert TOON back to JSON** (Source: `CLI Core.md`): Convert a TOON file back into standard JSON for compatibility with other tools.
    ```sh
    toon data.toon --output data.json
    ```

*   **Process Large Datasets via Streams** (Source: `Toon Decoding.md`): Programmatically use the `decodeStream` function from the core library to parse a very large TOON file line-by-line without loading it all into memory.

*   **Generate Compact LLM Prompts** (Source: `Toon Core.md`): Use the `encode` function to serialize structured data into the token-efficient TOON format before including it in a prompt for a Large Language Model.
