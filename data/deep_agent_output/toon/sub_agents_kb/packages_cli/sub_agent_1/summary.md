# `packages/cli` Knowledge Base

## 1. Overview

The `packages/cli` module provides a command-line interface (CLI) for seamless conversion between JSON and TOON data formats. It serves as the primary user-facing tool for interacting with the core TOON conversion logic. Built on `citty` for robust argument parsing and leveraging the `toon` library for the actual data transformation, this CLI tool allows users to encode JSON to TOON, decode TOON to JSON, and configure various aspects of the conversion process through command-line arguments. It supports reading from files or standard input and writing to files or standard output, making it highly flexible for scripting and integration into build pipelines.

## 2. Key Components

The `cli` package is structured around several key TypeScript files and external libraries:

*   **`src/index.ts`**: This is the heart of the CLI, defining the main command (`mainCommand`) and its extensive set of command-line arguments using the `citty` framework. It handles argument validation (e.g., `indent`, `delimiter`, `keyFolding`, `flattenDepth`, `expandPaths`) and orchestrates the conversion flow by calling `encodeToToon` or `decodeToJson` from `conversion.ts` based on detected or specified modes. This file acts as the bridge between user input and the underlying conversion logic.

*   **`src/cli-entry.ts`**: A minimal entry point file that imports `mainCommand` from `index.ts` and initiates the CLI application by calling `runMain` from `citty`. It's the initial script executed when the CLI is invoked.

*   **`src/conversion.ts`**: Contains the core business logic for performing the actual JSON-TOON and TOON-JSON conversions. It exposes `encodeToToon` and `decodeToJson` functions. This file interacts heavily with the `../../toon/src` library for encoding/decoding and manages file input/output, including streaming capabilities for large files. It also integrates `tokenx` for estimating token counts when the `--stats` flag is used.

*   **`src/types.ts`**: Defines fundamental TypeScript types used across the CLI package, most notably `InputSource`, which abstracts whether input originates from standard input (`stdin`) or a file (`file`).

*   **External Libraries**: The CLI relies on:
    *   `citty`: For defining and running command-line applications.
    *   `consola`: For consistent and informative logging to the console.
    *   `tokenx`: For estimating token counts in both JSON and TOON formats.
    *   `../../toon/src`: The core library providing the actual `encode`, `decode`, `encodeLines`, and `decodeStream` functions.

## 3. Data Flow & Dependencies

The data flow within the `cli` package follows a clear path from argument parsing to data conversion and output:

1.  **Invocation**: The CLI is initiated via `src/cli-entry.ts`, which calls `citty.runMain(mainCommand)`.
2.  **Argument Parsing & Validation**: `mainCommand` (defined in `src/index.ts`) parses command-line arguments. It validates inputs like `indent`, `delimiter`, `keyFolding`, `flattenDepth`, and `expandPaths`. Errors during validation lead to immediate termination.
3.  **Input Source Determination**: Based on the `input` argument, an `InputSource` object (defined in `src/types.ts`) is created, indicating whether to read from `stdin` or a specific file path.
4.  **Conversion Mode Detection**: The `detectMode` utility (imported in `index.ts`, likely from `utils.ts`) determines if the operation is `encode` (JSON to TOON) or `decode` (TOON to JSON). This can be overridden by explicit `--encode` or `--decode` flags.
5.  **Conversion Execution**: 
    *   **Encoding (JSON to TOON)**: If `mode` is `encode`, `conversion.encodeToToon` is called. It reads the JSON input (via `readInput`), parses it, and then uses `toon.encode` or `toon.encodeLines` to convert the data to TOON. If the `stats` flag is active, it performs token estimation using `tokenx`.
    *   **Decoding (TOON to JSON)**: If `mode` is `decode`, `conversion.decodeToJson` is called. This function reads the TOON input (via `readInput` for full content or `readLinesFromSource` for streaming), and then utilizes `toon.decode` or `toon.decodeStream` to transform the data into JSON.
6.  **Output Handling**: Both `encodeToToon` and `decodeToJson` utilize `writeStreamingToon` and `writeStreamingJson` (defined in `conversion.ts`) respectively. These functions handle writing the converted output to either a specified `outputPath` file or `process.stdout` (standard output) using a streaming approach to minimize memory usage for large datasets.
7.  **Error Handling**: A `try...catch` block in `index.ts` gracefully handles conversion errors, logging them using `consola.error` and exiting with a non-zero status code.

The `cli` package heavily depends on the `toon` library for its core functionality and `node:fs/promises`, `node:path`, and `node:process` for file system interactions and process management.

## 4. Code Deep Dive

### CLI Command Definition and Argument Handling (`src/index.ts`)

The `mainCommand` in `src/index.ts` is where the CLI's behavior is defined, including its metadata and all supported arguments. This snippet demonstrates how `citty.defineCommand` is used to declare arguments and their types, descriptions, aliases, and default values.

```typescript
export const mainCommand: CommandDef<{
  input: { /* ... */ }
  output: { /* ... */ }
  encode: { /* ... */ }
  decode: { /* ... */ }
  delimiter: { /* ... */ }
  indent: { /* ... */ }
  strict: { /* ... */ }
  keyFolding: { /* ... */ }
  flattenDepth: { /* ... */ }
  expandPaths: { /* ... */ }
  stats: { /* ... */ }
}> = defineCommand({
  meta: {
    name,
    description: 'TOON CLI — Convert between JSON and TOON formats',
    version,
  },
  args: {
    input: {
      type: 'positional',
      description: 'Input file path (omit or use "-" to read from stdin)',
      required: false,
    },
    output: {
      type: 'string',
      description: 'Output file path',
      alias: 'o',
    },
    encode: {
      type: 'boolean',
      description: 'Encode JSON to TOON (auto-detected by default)',
      alias: 'e',
    },
    // ... other arguments ...
  },
  async run({ args }) {
    // ... argument validation and conversion logic ...
  },
})
```

This structure ensures that the CLI has well-defined options and that `citty` automatically handles parsing these arguments from the command line. The `run` function then contains the logic to process these arguments.

### Streaming TOON Encoding (`src/conversion.ts`)

The `encodeToToon` function demonstrates how JSON content is read, parsed, and then converted to TOON. It also showcases the conditional logic for token statistics and the streaming write mechanism.

```typescript
export async function encodeToon(config: {
  input: InputSource
  output?: string
  indent: NonNullable<EncodeOptions['indent']>
  delimiter: NonNullable<EncodeOptions['delimiter']>
  keyFolding?: NonNullable<EncodeOptions['keyFolding']>
  flattenDepth?: number
  printStats: boolean
}): Promise<void> {
  const jsonContent = await readInput(config.input)

  let data: unknown
  try {
    data = JSON.parse(jsonContent)
  }
  catch (error) {
    throw new Error(`Failed to parse JSON: ${error instanceof Error ? error.message : String(error)}`)
  }

  const encodeOptions: EncodeOptions = {
    delimiter: config.delimiter,
    indent: config.indent,
    keyFolding: config.keyFolding,
    flattenDepth: config.flattenDepth,
  }

  if (config.printStats) {
    const toonOutput = encode(data, encodeOptions)
    // ... write full output and print stats ...
  }
  else {
    // Streamed output for non-stats mode
    await writeStreamingToon(encodeLines(data, encodeOptions), config.output)

    if (config.output) {
      const relativeInputPath = formatInputLabel(config.input)
      const relativeOutputPath = path.relative(process.cwd(), config.output)
      consola.success(`Encoded \
${relativeInputPath}\
 → \
${relativeOutputPath}\
`)
    }
  }
}
```

This snippet highlights the use of `readInput` for flexible input handling, `JSON.parse` for initial data parsing, and then the core `encode` or `encodeLines` functions from the `toon` library. The `writeStreamingToon` function is crucial for efficient memory management when dealing with potentially large TOON outputs.

### Streaming Output to File or Stdout (`src/conversion.ts`)

The `writeStreamingJson` function demonstrates the abstract pattern for writing streamed data, either to a file or directly to standard output. This pattern is essential for handling large conversion results without buffering the entire content in memory.

```typescript
async function writeStreamingJson(
  chunks: AsyncIterable<string> | Iterable<string>,
  outputPath?: string,
): Promise<void> {
  if (outputPath) {
    let fileHandle: FileHandle | undefined
    try {
      fileHandle = await fsp.open(outputPath, 'w')
      for await (const chunk of chunks) {
        await fileHandle.write(chunk)
      }
    } finally {
      await fileHandle?.close()
    }
  }
  else {
    for await (const chunk of chunks) {
      process.stdout.write(chunk)
    }
    process.stdout.write('\n') // Add final newline for stdout
  }
}
```

This function abstracts the file writing logic, using `node:fs/promises` for file operations and `process.stdout.write` for console output. The `for await...of` loop efficiently handles asynchronous chunking of data, making it suitable for streaming operations.

## 5. Potential Pitfalls

*   **Invalid Argument Values**: The CLI performs validation for several arguments (e.g., `indent`, `delimiter`, `keyFolding`, `flattenDepth`, `expandPaths`). Providing invalid values will result in runtime errors and process exit. Users should carefully review the expected formats and allowed values for each option.
*   **Input/Output Paths**: Incorrect or inaccessible file paths for input or output will cause I/O errors. Ensure the CLI has appropriate read/write permissions for specified files.
*   **Large Files and `expandPaths='safe'`**: When `expandPaths` is set to `