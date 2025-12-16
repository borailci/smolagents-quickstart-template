# Toon Package Knowledge Base

## 1. Overview

The `toon` package provides a robust and flexible library for converting JavaScript values (objects, arrays, and primitives) to and from the TOON format. TOON (Typed Object Notation) is a human-readable, hierarchical data serialization format designed for configuration files, data exchange, and more. It supports various data structures, including objects, arrays (with special handling for tabular and inline formats), and primitive types, offering features like key folding and path expansion for compact representation and easy reconstruction. The library supports both direct string encoding/decoding and streaming operations, making it suitable for handling large datasets efficiently.

## 2. Key Components

### `index.ts`
This file serves as the main entry point for the `toon` library, exposing the primary `encode` and `decode` functions, along with their streaming counterparts (`encodeLines`, `decodeFromLines`, `decodeStreamSync`, `decodeStream`). It orchestrates the overall encoding and decoding process by importing and utilizing functionalities from other modules like `decode/decoders`, `decode/event-builder`, `decode/expand`, `encode/encoders`, `encode/normalize`, and `encode/replacer`.

### `types.ts`
Defines the core type definitions used throughout the `toon` package. This includes:
- `JsonPrimitive`, `JsonObject`, `JsonArray`, `JsonValue`: Standard JSON-like type definitions.
- `EncodeOptions`, `DecodeOptions`, `DecodeStreamOptions`: Interfaces for configuring the encoding and decoding processes, specifying options like `indent`, `delimiter`, `keyFolding`, `flattenDepth`, `replacer`, `strict`, and `expandPaths`.
- `EncodeReplacer`: A function type for transforming values during encoding, similar to JSON.stringify's replacer.
- `JsonStreamEvent`: Union type representing the various events emitted during streaming decoding (e.g., `startObject`, `key`, `primitive`).
- `ArrayHeaderInfo`, `ParsedLine`, `BlankLineInfo`: Internal types used during the parsing phase.

### `decode/parser.ts`
This module is responsible for the low-level parsing of individual lines in the TOON format. It contains functions to:
- `parseArrayHeaderLine`: Extracts information from array header lines (e.g., `users[3]:`, `data[{id,name}]:`).
- `parseBracketSegment`: Parses the content within square brackets in array headers to determine array length and delimiter.
- `parseDelimitedValues`: Splits a string by a given delimiter, correctly handling quoted strings and escape sequences.
- `parsePrimitiveToken`: Converts a string token into its corresponding JavaScript primitive type (string, number, boolean, null).
- `parseStringLiteral`: Parses quoted string tokens, including unescaping characters.
- `parseUnquotedKey`, `parseQuotedKey`, `parseKeyToken`: Functions for extracting and parsing keys from TOON lines.
It also includes helper functions like `isArrayHeaderContent` and `isKeyValueContent` to identify the type of content in a line.

### `encode/encoders.ts`
This module handles the logic for converting JavaScript values into TOON formatted lines. It defines generator functions that yield TOON lines, allowing for streaming:
- `encodeJsonValue`: The top-level function that dispatches encoding to appropriate handlers based on the `JsonValue` type.
- `encodeObjectLines`: Encodes JavaScript objects, iterating through their properties. It includes logic for `keyFolding`.
- `encodeKeyValuePairLines`: Handles encoding of individual key-value pairs, incorporating `keyFolding` and `flattenDepth`.
- `encodeArrayLines`: Manages the encoding of JavaScript arrays, determining the most suitable TOON representation (inline primitives, tabular objects, or expanded list items).
- `encodeArrayOfArraysAsListItemsLines`, `encodeArrayOfObjectsAsTabularLines`, `encodeMixedArrayAsListItemsLines`: Specific functions for encoding different array structures.
- `extractTabularHeader`, `isTabularArray`: Helpers for detecting and extracting headers for tabular array representations.
- `indentedLine`, `indentedListItem`: Utility functions for applying correct indentation and list item markers.

## 3. Data Flow & Dependencies

### Encoding Data Flow
1.  **Entry Point**: A JavaScript value is passed to `encode(input, options?)` or `encodeLines(input, options?)`.
2.  **Normalization**: `normalizeValue` (from `encode/normalize`) ensures the input is a valid `JsonValue`.
3.  **Replacer Application**: If an `EncodeReplacer` is provided in `options`, `applyReplacer` (from `encode/replacer`) is invoked to transform or filter values.
4.  **Option Resolution**: `resolveOptions` normalizes and sets default values for `EncodeOptions`.
5.  **Value Encoding**: `encodeJsonValue` (from `encode/encoders`) acts as a dispatcher:
    *   For primitives, `encodePrimitive` handles direct conversion.
    *   For objects, `encodeObjectLines` iterates through key-value pairs, potentially applying `keyFolding` (via `tryFoldKeyChain` from `encode/folding`).
    *   For arrays, `encodeArrayLines` determines the optimal array representation (inline, tabular, or expanded list) and calls specialized encoding functions (`encodeInlineArrayLine`, `encodeArrayOfObjectsAsTabularLines`, etc.).
6.  **Line Generation**: All encoding functions (`encodeObjectLines`, `encodeArrayLines`, etc.) are generators that yield individual TOON formatted strings, which are then correctly indented by `indentedLine` or `indentedListItem`.
7.  **Output**: For `encode()`, the yielded lines are joined by newlines to form the final TOON string. For `encodeLines()`, an iterable of lines is returned.

**Key Dependencies for Encoding**: `types.ts`, `constants.ts`, `encode/normalize.ts`, `encode/replacer.ts`, `encode/encoders.ts`, `encode/primitives.ts`, `encode/folding.ts`.

### Decoding Data Flow
1.  **Entry Point**: A TOON formatted string is passed to `decode(input, options?)` or an iterable of lines to `decodeFromLines(lines, options?)`, `decodeStreamSync(lines, options?)`, or `decodeStream(source, options?)`.
2.  **Line Splitting**: For `decode()`, the input string is split into an array of lines.
3.  **Option Resolution**: `resolveDecodeOptions` (from `index.ts`) normalizes and sets default values for `DecodeOptions`.
4.  **Stream Decoding**: `decodeStreamSyncCore` or `decodeStreamCore` (from `decode/decoders`) processes the input lines (or async source) and yields `JsonStreamEvent`s.
    *   This core decoder uses `decode/parser.ts` for low-level tasks like parsing array headers (`parseArrayHeaderLine`), delimited values (`parseDelimitedValues`), and primitive tokens (`parsePrimitiveToken`, `parseStringLiteral`). It builds an event stream representing the hierarchical structure.
5.  **Value Reconstruction**: `buildValueFromEvents` (from `decode/event-builder`) consumes the `JsonStreamEvent` stream and reconstructs the full JavaScript value in memory.
6.  **Path Expansion**: If `expandPaths: 