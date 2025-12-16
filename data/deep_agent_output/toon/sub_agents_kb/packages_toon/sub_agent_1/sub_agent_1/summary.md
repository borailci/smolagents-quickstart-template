## 4. Code Deep Dive

### 4.1. Encoding an Object (`encode/encoders.ts`)

The `encodeObjectLines` generator function is central to converting JavaScript objects into TOON lines. It iterates through an object's properties and uses `encodeKeyValuePairLines` to handle each key-value pair, potentially applying key folding.

```typescript
export function* encodeObjectLines(
  value: JsonObject,
  depth: Depth,
  options: ResolvedEncodeOptions,
  rootLiteralKeys?: Set<string>,
  pathPrefix?: string,
  remainingDepth?: number,
): Generator<string> {
  const keys = Object.keys(value)

  // At root level (depth 0), collect all literal dotted keys for collision checking
  if (depth === 0 && !rootLiteralKeys) {
    rootLiteralKeys = new Set(keys.filter(k => k.includes('.')))
  }

  const effectiveFlattenDepth = remainingDepth ?? options.flattenDepth

  for (const [key, val] of Object.entries(value)) {
    yield* encodeKeyValuePairLines(key, val, depth, options, keys, rootLiteralKeys, pathPrefix, effectiveFlattenDepth)
  }
}

export function* encodeKeyValuePairLines(
  key: string,
  value: JsonValue,
  depth: Depth,
  options: ResolvedEncodeOptions,
  siblings?: readonly string[],
  rootLiteralKeys?: Set<string>,
  pathPrefix?: string,
  flattenDepth?: number,
): Generator<string> {
  const currentPath = pathPrefix ? `${pathPrefix}${DOT}${key}` : key
  const effectiveFlattenDepth = flattenDepth ?? options.flattenDepth

  // Attempt key folding when enabled
  if (options.keyFolding === 'safe' && siblings) {
    const foldResult = tryFoldKeyChain(key, value, siblings, options, rootLiteralKeys, pathPrefix, effectiveFlattenDepth)

    if (foldResult) {
      const { foldedKey, remainder, leafValue, segmentCount } = foldResult
      const encodedFoldedKey = encodeKey(foldedKey)

      // Case 1: Fully folded to a leaf value
      if (remainder === undefined) {
        // The folded chain ended at a leaf (primitive, array, or empty object)
        if (isJsonPrimitive(leafValue)) {
          yield indentedLine(depth, `${encodedFoldedKey}: ${encodePrimitive(leafValue, options.delimiter)}`, options.indent)
          return
        }
        else if (isJsonArray(leafValue)) {
          yield* encodeArrayLines(foldedKey, leafValue, depth, options)
          return
        }
        else if (isJsonObject(leafValue) && isEmptyObject(leafValue)) {
          yield indentedLine(depth, `${encodedFoldedKey}:`, options.indent)
          return
        }
      }

      // Case 2: Partially folded with a tail object
      if (isJsonObject(remainder)) {
        yield indentedLine(depth, `${encodedFoldedKey}:`, options.indent)
        // Calculate remaining depth budget (subtract segments already folded)
        const remainingDepth = effectiveFlattenDepth - segmentCount
        const foldedPath = pathPrefix ? `${pathPrefix}${DOT}${foldedKey}` : foldedKey
        yield* encodeObjectLines(remainder, depth + 1, options, rootLiteralKeys, foldedPath, remainingDepth)
        return
      }
    }
  }

  const encodedKey = encodeKey(key)

  if (isJsonPrimitive(value)) {
    yield indentedLine(depth, `${encodedKey}: ${encodePrimitive(value, options.delimiter)}`, options.indent)
  }
  else if (isJsonArray(value)) {
    yield* encodeArrayLines(key, value, depth, options)
  }
  else if (isJsonObject(value)) {
    yield indentedLine(depth, `${encodedKey}:`, options.indent)
    if (!isEmptyObject(value)) {
      yield* encodeObjectLines(value, depth + 1, options, rootLiteralKeys, currentPath, effectiveFlattenDepth)
    }
  }
}
```

*   **`encodeObjectLines`**: This function takes a `JsonObject`, its current `depth` in the TOON structure, and `ResolvedEncodeOptions`. It iterates over the object's keys and calls `encodeKeyValuePairLines` for each entry. It also handles the `rootLiteralKeys` for collision checking during key folding.
*   **`encodeKeyValuePairLines`**: This function is responsible for encoding a single key-value pair. It first attempts `keyFolding` if enabled. If folding occurs, it generates the appropriate folded line. Otherwise, it encodes the key and then delegates to other encoding functions (`encodePrimitive`, `encodeArrayLines`, `encodeObjectLines`) based on the value's type. The `indentedLine` helper ensures proper indentation.

### 4.2. Synchronous Streaming Decode (`decode/decoders.ts`)

The `decodeStreamSync` generator function processes TOON lines synchronously, yielding `JsonStreamEvent`s. This is crucial for efficient parsing without loading the entire structure into memory.

```typescript
export function* decodeStreamSync(
  source: Iterable<string>,
  options?: DecodeStreamOptions,
): Generator<JsonStreamEvent> {
  // Validate options
  if (options?.expandPaths !== undefined) {
    throw new Error('expandPaths is not supported in streaming decode')
  }

  const resolvedOptions: DecoderContext = {
    indent: options?.indent ?? 2,
    strict: options?.strict ?? true,
  }

  const scanState = createScanState()
  const lineGenerator = parseLinesSync(source, resolvedOptions.indent, resolvedOptions.strict, scanState)
  const cursor = new StreamingLineCursor(lineGenerator, scanState)

  // Get first line to determine root form
  const first = cursor.peekSync()
  if (!first) {
    // Empty input decodes to empty object
    yield { type: 'startObject' }
    yield { type: 'endObject' }
    return
  }

  // Check for root array
  if (isArrayHeaderContent(first.content)) {
    const headerInfo = parseArrayHeaderLine(first.content, DEFAULT_DELIMITER)
    if (headerInfo) {
      cursor.advanceSync()
      yield* decodeArrayFromHeaderSync(headerInfo.header, headerInfo.inlineValues, cursor, 0, resolvedOptions)
      return
    }
  }

  // Check for single primitive
  cursor.advanceSync()
  const hasMore = !cursor.atEndSync()
  if (!hasMore && !isKeyValueLineSync(first)) {
    // Single non-key-value line is root primitive
    yield { type: 'primitive', value: parsePrimitiveToken(first.content.trim()) }
    return
  }

  // Root object
  yield { type: 'startObject' }
  yield* decodeKeyValueSync(first.content, cursor, 0, resolvedOptions)

  // Process remaining object fields
  while (!cursor.atEndSync()) {
    const line = cursor.peekSync()
    if (!line || line.depth !== 0) {
      break
    }

    cursor.advanceSync()
    yield* decodeKeyValueSync(line.content, cursor, 0, resolvedOptions)
  }

  yield { type: 'endObject' }
}

function* decodeKeyValueSync(
  content: string,
  cursor: StreamingLineCursor,
  baseDepth: Depth,
  options: DecoderContext,
): Generator<JsonStreamEvent> {
  // Check for array header first
  const arrayHeader = parseArrayHeaderLine(content, DEFAULT_DELIMITER)
  if (arrayHeader && arrayHeader.header.key) {
    yield { type: 'key', key: arrayHeader.header.key }
    yield* decodeArrayFromHeaderSync(arrayHeader.header, arrayHeader.inlineValues, cursor, baseDepth, options)
    return
  }

  // Regular key-value pair
  const { key, isQuoted } = parseKeyToken(content, 0)
  const colonIndex = content.indexOf(COLON, key.length)
  const rest = colonIndex >= 0 ? content.slice(colonIndex + 1).trim() : ''

  yield isQuoted ? { type: 'key', key, wasQuoted: true } : { type: 'key', key }

  // No value after colon - expect nested object or empty
  if (!rest) {
    const nextLine = cursor.peekSync()
    if (nextLine && nextLine.depth > baseDepth) {
      yield { type: 'startObject' }
      yield* decodeObjectFieldsSync(cursor, baseDepth + 1, options)
      yield { type: 'endObject' }
      return
    }

    // Empty object
    yield { type: 'startObject' }
    yield { type: 'endObject' }
    return
  }

  // Inline primitive value
  yield { type: 'primitive', value: parsePrimitiveToken(rest) }
}
```

*   **`decodeStreamSync`**: This generator function takes an `Iterable<string>` (TOON lines) and `DecodeStreamOptions`. It initializes a `StreamingLineCursor` to manage line consumption and then determines the root structure (object, array, or primitive) based on the first line. It then delegates to other synchronous decoding generators like `decodeArrayFromHeaderSync` or `decodeKeyValueSync` to process the data.
*   **`decodeKeyValueSync`**: This function is responsible for decoding a single TOON key-value line. It first checks if the line represents an array header. If not, it parses the key and then determines the value type (primitive, nested object, or empty object) based on the remaining content and the next line's indentation. It yields `JsonStreamEvent`s representing the parsed key and value.

## 5. Potential Pitfalls

*   **Indentation Sensitivity**: TOON is highly sensitive to indentation, similar to YAML. Incorrect indentation will lead to parsing errors. The `indent` option in both encoding and decoding should be consistent.
*   **Strict Mode**: The `strict` option in decoding (defaulting to `true`) enforces rigorous validation of array lengths, tabular row counts, and blank lines. While good for correctness, it can be unforgiving with malformed input. Setting it to `false` might allow parsing of slightly irregular TOON, but with potential data integrity issues.
*   **Streaming Limitations**: The streaming decode functions (`decodeStreamSync`, `decodeStream`) explicitly do not support `expandPaths`. If path expansion is required, the full `decode` or `decodeFromLines` functions must be used, which build the entire JSON value in memory. This is a trade-off between memory efficiency and feature set.
*   **Key Folding Complexity**: While `keyFolding` in encoding simplifies output, complex folding scenarios or collisions with literal dotted keys require careful handling, as seen in `tryFoldKeyChain` logic. Decoding with `expandPaths` is essential for a lossless round-trip when `keyFolding` is used.
*   **Error Handling**: The decoders throw `SyntaxError` or `ReferenceError` for unexpected input formats or missing components. Robust applications using this library should implement appropriate try-catch blocks to handle these exceptions gracefully.