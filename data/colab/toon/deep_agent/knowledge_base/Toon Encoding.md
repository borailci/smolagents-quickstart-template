'''
# Toon Encoding Technical Analysis

## 1. Overview

The Toon Encoding modules are a core component of the `@toon-format/toon` package. Their primary responsibility is to convert a standard JSON-like object model (`JsonValue`) into the proprietary, human-readable, and token-efficient TOON format string. The encoding process is designed to be both compact and structured, with special optimizations for common data patterns like arrays of objects (tabular data) and nested single-key objects (key folding).

The process is orchestrated by `encoders.ts`, which recursively traverses the input `JsonValue`. It relies on `primitives.ts` for the low-level encoding of individual values (strings, numbers, booleans) and `folding.ts` for the advanced key-folding optimization.

## 2. File-by-File Analysis

### `packages/toon/src/encode/primitives.ts`

- **Purpose**: This file provides foundational functions for serializing the smallest units of data in the TOON format. It handles the conversion of JavaScript primitives to their TOON string representation.
- **Key Components**:
  - `encodePrimitive()`: The main function that dispatches a `JsonPrimitive` (string, number, boolean, null) to the appropriate handler.
  - `encodeStringLiteral()`: Encodes a string. It intelligently decides whether the string can be represented as an unquoted literal or if it requires double quotes and escaping (e.g., if it contains spaces, special characters, or the user-defined delimiter).
  - `encodeKey()`: Similar to `encodeStringLiteral` but for object keys. It determines if a key can be an unquoted identifier or needs to be quoted.
  - `formatHeader()`: A crucial helper for creating the TOON headers that precede collections (arrays and objects). It formats headers like `key[3]:`, `[5,]:`, or `data[10]{id,name}:` which encode the key, item count, delimiter, and tabular fields.

### `packages/toon/src/encode/folding.ts`

- **Purpose**: This module implements an optimization technique called "key folding". It transforms deeply nested objects that have only a single key at each level into a compact, dot-separated key.
- **Key Components**:
  - `tryFoldKeyChain()`: The primary export. This function inspects a key-value pair to see if the value is a chain of single-key objects (e.g., `{ "a": { "b": { "c": 123 } } }`). If the `keyFolding: 'safe'` option is enabled and certain safety conditions are met (no key collisions, valid identifiers), it returns a `FoldResult` containing the new folded key (`"a.b.c"`) and the final leaf value (`123`). This allows the encoder to output `a.b.c: 123` directly, saving indentation and lines.
  - `collectSingleKeyChain()`: A helper function that traverses the nested object structure to extract the chain of keys and the final value, respecting the `flattenDepth` limit.

### `packages/toon/src/encode/encoders.ts`

- **Purpose**: This is the central orchestrator for the encoding process. It contains the main recursive logic for traversing a `JsonValue` and generating the final TOON string line by line using a generator (`Generator<string>`).
- **Key Components**:
  - `encodeJsonValue()`: The main entry point for encoding any `JsonValue`. It checks if the value is a primitive, array, or object and delegates to the appropriate specialized encoder.
  - `encodeObjectLines()`: Recursively iterates over the keys of an object. For each key-value pair, it calls `encodeKeyValuePairLines`.
  - `encodeKeyValuePairLines()`: This is a key function that first attempts to apply key folding via `tryFoldKeyChain()`. If folding is not successful, it proceeds to encode the key and value based on the value's type (primitive, array, or object), applying the correct indentation.
  - `encodeArrayLines()`: A dispatcher for array encoding. It detects the type of array and delegates to the most efficient encoding strategy:
    - `isArrayOfPrimitives`: Encodes to a single, inline line (e.g., `key[3]: 1,2,3`).
    - `isArrayOfObjects` (Tabular): If all objects share the same keys and have primitive values, it encodes them as a compact table with a header row.
    - `isArrayOfArrays` / `Mixed Array`: Falls back to a list-based format where each item is prefixed with a `-`.
  - `encodeObjectAsListItemLines()`: Handles the complex case of encoding an object that is an item in a list. It ensures the first key-value pair is on the same line as the list marker (`-`) for compactness.

## 3. Integration & Data Flow

The encoding process begins with a call to `encodeJsonValue`. 

1.  The function determines the value's top-level type.
2.  For objects, it iterates through keys. For each key, it calls `tryFoldKeyChain` to see if a nested structure can be flattened into a single `a.b.c` key.
3.  If folding succeeds, the folded key and its final value are encoded.
4.  If not, the key is encoded using `encodeKey`, and the value is processed recursively.
5.  For arrays, `encodeArrayLines` inspects the array's contents to choose an encoding strategy:
    *   **Inline**: For `[1, 2, 3]`, it produces `[3]: 1,2,3`.
    *   **Tabular**: For `[{id:1, name:"A"}, {id:2, name:"B"}]`, it produces a header (`[2]{id,name}:`) followed by rows (`1,"A"` and `2,"B"`).
    *   **List**: For mixed or complex types, it produces a header (`[2]:`) followed by indented list items (`- ...`).
6.  All primitive values are ultimately serialized by `encodePrimitive`.
7.  The entire output is a stream of strings yielded by generators, which are finally joined to create the complete TOON document.

## 4. API Reference

Below is a reference for the key exported functions across the encoding modules. The primary entry point for consumers is `encodeJsonValue`.

| Function Signature | Description |
| --- | --- |
| `encodeJsonValue(value: JsonValue, options: ResolvedEncodeOptions, depth: Depth): Generator<string>` | **Primary Entry Point.** Encodes a `JsonValue` into a sequence of TOON-formatted lines. | 
| `encodeObjectLines(value: JsonObject, depth: Depth, options: ResolvedEncodeOptions, ...): Generator<string>` | Encodes the properties of an object. This is a core part of the recursive encoding process. | 
| `encodeArrayLines(key: string \| undefined, value: JsonArray, depth: Depth, options: ResolvedEncodeOptions): Generator<string>` | Dispatches an array to the appropriate specialized encoder (inline, tabular, or list) based on its contents. | 
| `encodeKeyValuePairLines(key: string, value: JsonValue, depth: Depth, ...): Generator<string>` | Encodes a single key-value pair. It incorporates the key-folding logic before falling back to standard encoding. | 
| `encodePrimitive(value: JsonPrimitive, delimiter?: string): string` | Encodes a single primitive value (string, number, boolean, null) into its TOON string representation. | 
| `encodeKey(key: string): string` | Encodes an object key, quoting it if it contains unsafe characters. | 
| `formatHeader(length: number, options?: { key?: string; fields?: readonly string[]; delimiter?: string }): string` | Constructs the `key[length]{fields}:` header string used for arrays and objects. | 
| `tryFoldKeyChain(key: string, value: JsonValue, ...): FoldResult \| undefined` | Attempts to perform key folding on a nested object structure. Returns a `FoldResult` on success. | 
| `isTabularArray(rows: readonly JsonObject[], header: readonly string[]): boolean` | Utility function to check if an array of objects can be represented in the compact tabular format. |

'''