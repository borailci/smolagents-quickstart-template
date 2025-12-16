# Toon Library Knowledge Base

## 1. Overview

The `toon` library provides robust functionalities for encoding JavaScript values into the TOON (Typed Object Notation) format and decoding TOON formatted strings back into JavaScript values. TOON is a human-readable, structured data format designed for configuration files and data interchange, offering features like array headers, tabular data representation, and key folding for compactness. The library supports both synchronous and asynchronous streaming operations for large datasets, making it versatile for various use cases from small configurations to significant data streams.

## 2. Key Components

*   **`index.ts`**: This is the main entry point for the `toon` library, exposing the core `encode` and `decode` functions, along with their streaming counterparts (`encodeLines`, `decodeFromLines`, `decodeStreamSync`, `decodeStream`). It orchestrates calls to the encoding and decoding sub-modules and handles overall options resolution.

*   **`decode/parser.ts`**: This module is responsible for the granular parsing of TOON syntax elements. It contains functions to parse array headers (`parseArrayHeaderLine`), delimited values (`parseDelimitedValues`), primitive tokens (`parsePrimitiveToken` for strings, numbers, booleans, null), and key tokens (`parseKeyToken`). It distinguishes between quoted and unquoted keys and values, handling escape sequences and bracket/colon positions within lines.

*   **`decode/decoders.ts`**: This component orchestrates the decoding process by consuming parsed lines and emitting `JsonStreamEvent`s. It manages the state during stream processing (e.g., tracking indentation depth) and reconstructs the JavaScript object or array structure. It handles various array formats (inline primitive arrays, tabular arrays with headers, and list-style arrays) and validates structure based on strictness options. The `StreamingLineCursor` class facilitates efficient line processing.

*   **`encode/encoders.ts`**: This module drives the encoding process, converting JavaScript values into TOON formatted lines. It recursively traverses the input value, determining the appropriate TOON representation for objects, arrays, and primitives. It differentiates between inline arrays, tabular arrays, and list arrays, and applies formatting rules like indentation and delimiters. It also integrates with the key folding mechanism.

*   **`encode/folding.ts`**: This module implements the "key folding" feature, which allows compact representation of nested single-key objects into a single dot-separated key (e.g., `{ a: { b: { c: "value" } } }` becomes `a.b.c: value`). The `tryFoldKeyChain` function attempts this optimization under "safe" conditions, ensuring no key collisions or invalid identifiers are created.

## 3. Data Flow & Dependencies

### Encoding Data Flow

1.  **Input**: A JavaScript `JsonValue` (object, array, primitive).
2.  **`index.ts` (`encode` or `encodeLines`)**: Resolves encoding options and normalizes the input value. An optional `replacer` function can transform the value.
3.  **`encode/encoders.ts` (`encodeJsonValue`, `encodeObjectLines`, `encodeArrayLines`, etc.)**: Recursively processes the JSON structure. For each key-value pair or array item, it decides on the appropriate TOON syntax. It leverages `encode/primitives.ts` for formatting individual primitives and keys.
4.  **`encode/folding.ts` (`tryFoldKeyChain`)**: If key folding is enabled and "safe" mode is active, `encoders.ts` will attempt to fold nested single-key objects into a single dotted key for a more compact output.
5.  **Output**: An `Iterable<string>` of TOON lines (from `encodeLines`) or a single TOON formatted string (from `encode`).

### Decoding Data Flow

1.  **Input**: A TOON formatted string or an `Iterable<string>` of TOON lines.
2.  **`index.ts` (`decode` or `decodeFromLines`, `decodeStreamSync`, `decodeStream`)**: Resolves decoding options and splits the input string into lines if necessary. For streaming, it initializes a `StreamingLineCursor` and a `StreamingScanState`.
3.  **`decode/scanner.ts`**: Processes raw input lines, extracts content and indentation depth, and identifies blank lines.
4.  **`decode/parser.ts`**: For each line, `decoders.ts` calls `parser.ts` functions (e.g., `parseArrayHeaderLine`, `parseKeyToken`, `parsePrimitiveToken`, `parseDelimitedValues`) to break down the line into its constituent TOON syntax elements (keys, values, array metadata).
5.  **`decode/decoders.ts` (`decodeStreamSync`, `decodeKeyValueSync`, `decodeArrayFromHeaderSync`, etc.)**: Consumes the parsed elements, managing the parsing state (e.g., current object/array context, depth). It emits `JsonStreamEvent`s (e.g., `startObject`, `key`, `primitive`, `endObject`) that represent the underlying JSON structure.
6.  **`decode/event-builder.ts`**: If not in streaming mode, `index.ts` uses `buildValueFromEvents` to aggregate these `JsonStreamEvent`s into a complete JavaScript value. An optional `expandPathsSafe` function can then process paths that might have been collapsed during encoding.
7.  **Output**: A JavaScript `JsonValue` (object, array, or primitive) or an `AsyncIterable<JsonStreamEvent>` / `Iterable<JsonStreamEvent>` in streaming mode.

### Key Dependencies

The modules within `toon` are highly interconnected, primarily depending on each other for parsing, encoding, and utility functions. External dependencies are minimal, focusing on core JavaScript types and built-in functionalities.

## 4. Code Deep Dive

### Encoding an object with key folding

The `encode` function is the primary way to convert a JavaScript object into a TOON string. Here's an example using key folding:

```typescript
import { encode } from './index';

const data = {
  user: {
    profile: {
      name: 'Alice',
      age: 30
    }
  },
  settings: {
    notifications: true
  }
};

const toonString = encode(data, { keyFolding: 'safe' });
console.log(toonString);
// Expected output:
// user.profile.name: Alice
// user.profile.age: 30
// settings.notifications: true
```

This example demonstrates how `keyFolding: 'safe'` automatically collapses `user.profile.name` into a single dotted key, making the output more concise. The `encode/folding.ts` module, specifically `tryFoldKeyChain`, is responsible for identifying and performing this transformation when safe conditions are met (e.g., no key collisions, valid identifiers).

### Decoding a TOON string with array expansion

The `decode` function converts a TOON string back into a JavaScript object. This example shows decoding a tabular array and using `expandPaths`:

```typescript
import { decode } from './index';

const toonInput = `
users[2]{id,name}:
  1,Alice
  2,Bob
config:
  logging.level: info
  logging.format: json
`;

const decodedValue = decode(toonInput, { expandPaths: 'safe' });
console.log(JSON.stringify(decodedValue, null, 2));
// Expected output:
// {
//   "users": [
//     {
//       "id": 1,
//       "name": "Alice"
//     },
//     {
//       "id": 2,
//       "name": "Bob"
//     }
//   ],
//   "config": {
//     "logging": {
//       "level": "info",
//       "format": "json"
//     }
//   }
// }
```

Here, the `users` array, defined with a header `users[2]{id,name}:`, is correctly parsed into an array of objects. The `config` object, which might have been encoded with key folding, is automatically expanded back into nested objects thanks to `expandPaths: 