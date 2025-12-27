'''
# `@toon-format/toon` Core Analysis

## 1. Overview

The `@toon-format/toon` package provides the core implementation for Token-Oriented Object Notation (TOON). Its primary purpose is to encode JavaScript objects, arrays, and primitives into a compact, human-readable, and schema-aware string format, and to decode them back. The library is designed with token efficiency in mind, making it suitable for use in LLM prompts. It offers both synchronous and asynchronous APIs for handling data in memory and via streams.

## 2. File-by-File Analysis

### `packages/toon/src/index.ts`
- **Purpose**: This is the main entry point of the package. It composes functionality from internal modules (`decode`, `encode`) and exports the complete public API for consumers.
- **Key Components**:
  - It exports the primary `encode()` and `decode()` functions for simple in-memory data transformation.
  - It provides `encodeLines()` for iterable-based encoding, suitable for streaming output.
  - It offers a suite of decoding functions: `decodeFromLines()` for pre-split line inputs, and `decodeStreamSync()` / `decodeStream()` for synchronous and asynchronous event-based stream processing.
  - It re-exports key types and constants from `types.ts` and `constants.ts` to form a complete public interface.

### `packages/toon/src/types.ts`
- **Purpose**: This file defines all the data structures, type aliases, and interfaces used throughout the library, particularly for the public API.
- **Key Components**:
  - **JSON Types**: `JsonValue`, `JsonObject`, `JsonArray`, `JsonPrimitive` establish the core data model compatible with standard JSON.
  - **Options Interfaces**: `EncodeOptions` and `DecodeOptions` define the configuration parameters for encoding and decoding operations, such as `indent`, `delimiter`, and `keyFolding`.
  - **Streaming Types**: `JsonStreamEvent` defines the object shapes yielded during streaming decoding (e.g., `{ type: 'startObject' }`, `{ type: 'key', key: 'name' }`).
  - **Internal Types**: Includes helper types like `ArrayHeaderInfo` and `ParsedLine` used by the parsing logic.

### `packages/toon/src/constants.ts`
- **Purpose**: This file centralizes primitive constants and literals used by the encoder and decoder.
- **Key Components**:
  - **Markers**: Defines structural characters like `LIST_ITEM_MARKER` (`-`) and `COLON` (`:`).
  - **Literals**: Specifies the string representations for `null`, `true`, and `false`.
  - **Delimiters**: Exports a `DELIMITERS` object containing supported delimiters (`comma`, `tab`, `pipe`) and defines the `DEFAULT_DELIMITER`.

## 3. Public Interface & Integration

The public API is designed for versatility, supporting different use cases from simple one-off conversions to advanced streaming pipelines.

- **High-Level Functions**: `encode()` and `decode()` are the primary entry points for most users. They operate on full strings in memory.
- **Streaming Encoding**: `encodeLines()` provides an iterable of TOON strings, allowing developers to write to files or network sockets line-by-line without buffering the entire output string.
- **Streaming Decoding**: `decodeStream()` (async) and `decodeStreamSync()` (sync) are powerful tools for parsing large TOON documents. Instead of building a full JavaScript object, they yield a stream of events. This is ideal for memory-constrained environments or for applications that need to process data as it arrives.
- **Configuration**: All primary functions accept an `options` object to control indentation, delimiters, key folding/expansion, and strictness.

## 4. Use Cases

- **Configuration Files**: Use `encode` and `decode` to manage human-readable configuration files that are more compact than JSON.
- **LLM Prompts**: Use `encode` to serialize structured data into a token-efficient format to be included in prompts for Large Language Models.
- **Data Serialization**: As a general-purpose replacement for JSON or YAML where human readability and compactness are important.
- **Large Dataset Processing**: Use `decodeStream` to parse a large TOON file from a file stream, processing each object or array as it is read without loading the entire file into memory.

## 5. API Reference

### Exported Functions

| Function | Signature | Description |
|---|---|---|
| `encode` | `(input: unknown, options?: EncodeOptions): string` | Encodes a JavaScript value into a single TOON format string. |
| `decode` | `(input: string, options?: DecodeOptions): JsonValue` | Decodes a TOON format string into a JavaScript value. |
| `encodeLines` | `(input: unknown, options?: EncodeOptions): Iterable<string>` | Encodes a JavaScript value into an iterable of TOON lines, suitable for streaming. |
| `decodeFromLines` | `(lines: Iterable<string>, options?: DecodeOptions): JsonValue` | Decodes TOON from an iterable of lines, building the full value in memory. |
| `decodeStreamSync` | `(lines: Iterable<string>, options?: DecodeStreamOptions): Iterable<JsonStreamEvent>` | Synchronously decodes TOON lines into an iterable of low-level JSON events. |
| `decodeStream` | `(source: AsyncIterable<string> \| Iterable<string>, options?: DecodeStreamOptions): AsyncIterable<JsonStreamEvent>` | Asynchronously decodes TOON lines from a sync or async source into a stream of low-level JSON events. |

### Exported Types & Constants

| Name | Type | Description |
|---|---|---|
| `EncodeOptions` | `interface` | Configuration for `encode` and `encodeLines`. |
| `DecodeOptions` | `interface` | Configuration for `decode` and `decodeFromLines`. |
| `DecodeStreamOptions` | `interface` | Configuration for `decodeStream` and `decodeStreamSync`. |
| `JsonValue` | `type` | Union of all possible JSON value types. |
| `JsonStreamEvent` | `type` | Union of all possible event types yielded by streaming decoders. |
| `DEFAULT_DELIMITER` | `const` | The default delimiter character (`,`). |
| `DELIMITERS` | `const` | An object containing all available delimiter characters. |

### `EncodeOptions` Interface

| Property | Type | Default | Description |
|---|---|---|---|
| `indent` | `number` | `2` | Number of spaces per indentation level. |
| `delimiter` | `Delimiter` | `DELIMITERS.comma` | Delimiter for tabular arrays and inline primitives. |
| `keyFolding` | `'off' \| 'safe'` | `'off'` | Collapses nested single-key objects into dotted paths. |
| `flattenDepth` | `number` | `Infinity` | Max depth for `keyFolding`. |
| `replacer` | `EncodeReplacer` | `undefined` | Function to transform or filter values during encoding. |

### `DecodeOptions` Interface

| Property | Type | Default | Description |
|---|---|---|---|
| `indent` | `number` | `2` | Number of spaces per indentation level. |
| `strict` | `boolean` | `true` | Enforces strict validation of array and table structures. |
| `expandPaths` | `'off' \| 'safe'` | `'off'` | Expands dotted keys into nested objects. Not for streaming. |
'''