A deep technical analysis of the CLI Utils for the @toon-format/cli package, detailing file responsibilities, key components, and public APIs for developers. The analysis covers utilities for streaming JSON generation, input/output handling, and operational mode detection within the command-line interface.

## 1. Overview

The `packages/cli/src` directory contains a collection of TypeScript modules that provide the core utilities for the `@toon-format/cli` command-line tool. These utilities handle the logic for converting between TOON and JSON formats, managing input and output streams, and determining the desired operation (encode or decode) based on user input and file types. The modules are designed to be efficient, supporting streaming for large files to minimize memory consumption.

## 2. File-by-File Analysis

### `json-from-events.ts`

- **Purpose**: This module is responsible for converting a stream of `JsonStreamEvent` objects into a formatted JSON string. This is a crucial component for the TOON-to-JSON decoding process, as it allows for the direct conversion of decoded TOON events into JSON output without constructing the entire JSON object tree in memory. This approach is highly memory-efficient, making it suitable for very large files.
- **Key Components**:
  - `jsonStreamFromEvents(events: AsyncIterable<JsonStreamEvent>, indent: number = 2): AsyncIterable<string>`: An asynchronous generator function that takes a stream of `JsonStreamEvent` objects and yields formatted JSON string chunks. It maintains a stack-based context to correctly handle the structure of JSON objects and arrays, including indentation and comma placement for pretty-printing.

### `json-stringify-stream.ts`

- **Purpose**: This module provides a streaming JSON stringifier. It takes a JavaScript value (object, array, primitive) and yields JSON string chunks, one at a time. This is useful for serializing large JavaScript objects to a stream without having to create the entire JSON string in memory first.
- **Key Components**:
  - `jsonStringifyLines(value: unknown, indent: number = 2): Iterable<string>`: A generator function that recursively traverses the input value and yields formatted JSON string chunks. It supports both compact and pretty-printed output based on the `indent` parameter.

### `utils.ts`

- **Purpose**: This module contains a set of general-purpose utility functions for the CLI, primarily focused on input/output operations and command-line argument processing.
- **Key Components**:
  - `detectMode(input: InputSource, encodeFlag?: boolean, decodeFlag?: boolean): 'encode' | 'decode'`: Determines whether the CLI should perform an "encode" (JSON to TOON) or "decode" (TOON to JSON) operation. It prioritizes explicit command-line flags (`--encode`, `--decode`) and then falls back to file extension detection (`.json` -> encode, `.toon` -> decode). Defaults to "encode".
  - `readInput(source: InputSource): Promise<string>`: Reads the entire input from either a file or standard input (`stdin`) and returns it as a single string.
  - `formatInputLabel(source: InputSource): string`: Formats the input source into a user-friendly label for display in messages (e.g., "stdin" or a relative file path).
  - `readLinesFromSource(source: InputSource): AsyncIterable<string>`: Reads input from a file or `stdin` and yields it line by line. This is the primary function for handling streaming input.

## 3. Integration Patterns

The utilities in these modules are designed to be composed together to build the CLI's functionality.

- **Decoding (TOON to JSON)**: The typical flow for decoding a TOON file involves `readLinesFromSource` to stream the input file line by line. These lines are then fed into a TOON decoder (presumably from the `@toon-format/toon` package), which in turn emits `JsonStreamEvent`s. These events are then piped to `jsonStreamFromEvents` to generate the final JSON output, which can be written to a file or `stdout`.

- **Encoding (JSON to TOON)**: For encoding, `readInput` would be used to read an entire JSON file into memory. This JSON string would be parsed into a JavaScript object using `JSON.parse`. This object would then be passed to a TOON encoder (from `@toon-format/toon`) to produce the TOON output.

- **Streaming Output**: `jsonStringifyLines` can be used to stream the serialization of a large JavaScript object. This is useful when the object is too large to stringify in one go, or when the output needs to be streamed to another process.

## 4. Use Cases

- **CLI Tool Implementation**: These utilities are the building blocks of the `@toon-format/cli` tool. They provide the core logic for the `toon` command, handling file I/O, format detection, and the streaming conversion process.

- **Custom Scripting**: Developers could use these utilities in custom Node.js scripts to perform batch conversions or to integrate TOON/JSON conversion into a larger data processing pipeline. For example, a script could watch a directory for new `.toon` files and use `readLinesFromSource` and `jsonStreamFromEvents` to convert them to JSON automatically.

## 5. API Reference

| Function | Signature | Description |
|---|---|---|
| `jsonStreamFromEvents` | `(events: AsyncIterable<JsonStreamEvent>, indent?: number): AsyncIterable<string>` | Converts a stream of `JsonStreamEvent` objects into formatted JSON string chunks. |
| `jsonStringifyLines` | `(value: unknown, indent?: number): Iterable<string>` | Yields JSON tokens one at a time for a given value. |
| `detectMode` | `(input: InputSource, encodeFlag?: boolean, decodeFlag?: boolean): 'encode' \| 'decode'` | Determines the operation mode (encode or decode) based on flags and file extensions. |
| `readInput` | `(source: InputSource): Promise<string>` | Reads the entire input from a file or stdin. |
| `formatInputLabel` | `(source: InputSource): string` | Formats the input source for display. |
| `readLinesFromSource` | `(source: InputSource): AsyncIterable<string>` | Reads input from a file or stdin line by line. |
