# TOON CLI Knowledge Base

## 1. Overview
The TOON CLI is a command-line interface tool designed for converting data between JSON and TOON (TOML-like Object Notation) formats. It provides functionalities to encode JSON into TOON and decode TOON back into JSON, supporting various options for formatting, strictness, and key handling. The CLI can read input from files or stdin and write output to files or stdout, making it flexible for scripting and piping.

## 2. Key Components
*   **`packages/cli/src/cli-entry.ts`**: This is the primary entry point for the CLI application. It uses the `citty` library to execute the `mainCommand` defined in `index.ts`.
*   **`packages/cli/src/index.ts`**: This file defines the `mainCommand` using `citty.defineCommand`. It specifies all available command-line arguments (e.g., input/output files, encode/decode flags, delimiter, indent, strict mode, key folding, expand paths, stats). The `run` method within `mainCommand` orchestrates the conversion process by parsing arguments, validating them, detecting the conversion mode (encode/decode), and then calling the appropriate conversion function from `conversion.ts`.
*   **`packages/cli/src/conversion.ts`**: This file contains the core logic for the actual data conversion. It exports `encodeToToon` and `decodeToJson` functions. These functions handle reading input, parsing/stringifying data (JSON.parse/JSON.stringify), interacting with the underlying `toon` library for encoding/decoding, and writing output to files or stdout, often using a streaming approach for efficiency.

## 3. Data Flow & Dependencies
**Input:**
- The CLI accepts input data either from a specified file path (positional argument) or from standard input (`-` or omitted). The `readInput` utility (from `utils.ts`, used in `conversion.ts`) handles reading from these sources.

**Output:**
- Converted data can be written to an output file specified by the `-o` or `--output` flag. If no output file is specified, the result is printed to standard output. The `writeStreamingJson` and `writeStreamingToon` functions in `conversion.ts` manage this output.

**Dependencies:**
- **`citty`**: Used for building the command-line interface, defining commands, arguments, and handling execution.
- **`consola`**: Utilized for logging informative messages, warnings, and errors to the console.
- **`@toon` (internal library)**: The core library responsible for the actual TOON encoding and decoding logic (`decode`, `encode`, `decodeStream`, `encodeLines`).
- **`tokenx`**: Used in `encodeToToon` when `--stats` flag is enabled, to estimate token counts for JSON and TOON outputs, providing compression statistics.
- **`node:path` and `node:fs/promises`**: For file system operations and path manipulation.

## 4. Code Deep Dive

### 4.1 CLI Command Definition
The `mainCommand` in `index.ts` sets up the CLI interface and arguments:
```typescript
export const mainCommand: CommandDef<{
  input: { type: 'positional'; description: string; required: false }
  output: { type: 'string'; description: string; alias: string }
  encode: { type: 'boolean'; description: string; alias: string }
  decode: { type: 'boolean'; description: string; alias: string }
  delimiter: { type: 'string'; description: string; default: string }
  indent: { type: 'string'; description: string; default: string }
  strict: { type: 'boolean'; description: string; default: true }
  keyFolding: { type: 'string'; description: string; default: string }
  flattenDepth: { type: 'string'; description: string }
  expandPaths: { type: 'string'; description: string; default: string }
  stats: { type: 'boolean'; description: string; default: false }
}> = defineCommand({
  meta: {
    name,
    description: 'TOON CLI — Convert between JSON and TOON formats',
    version,
  },
  args: {
    // ... argument definitions ...
  },
  async run({ args }) {
    // ... logic for parsing args, mode detection, and calling conversion functions ...
  },
})
```
This snippet illustrates how `citty.defineCommand` is used to declare the command's metadata and available arguments, including their types, descriptions, aliases, and default values. The `run` function contains the main execution logic.

### 4.2 Conversion Execution Logic
The `run` function within `mainCommand` determines the conversion mode and calls the appropriate function:
```typescript
    const mode = detectMode(inputSource, args.encode, args.decode)

    try {
      if (mode === 'encode') {
        await encodeToToon({
          input: inputSource,
          output: outputPath,
          delimiter: delimiter as Delimiter,
          indent,
          keyFolding: keyFolding as NonNullable<EncodeOptions['keyFolding']>,
          flattenDepth,
          printStats: args.stats === true,
        })
      }
      else {
        await decodeToJson({
          input: inputSource,
          output: outputPath,
          indent,
          strict: args.strict !== false,
          expandPaths: expandPaths as NonNullable<DecodeOptions['expandPaths']>,
        })
      }
    }
    catch (error) {
      consola.error(error)
      process.exit(1)
    }
```
This section shows the conditional execution of `encodeToToon` or `decodeToJson` based on the detected `mode`. It also highlights the argument passing and error handling using `consola`.

### 4.3 TOON Encoding with Statistics
The `encodeToToon` function in `conversion.ts` handles JSON to TOON conversion, including an optional statistics feature:
```typescript
export async function encodeToToon(config: {
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
    // ... write output and calculate/log token stats ...
  }
  else {
    await writeStreamingToon(encodeLines(data, encodeOptions), config.output)
    // ... log success ...
  }
}
```
This snippet demonstrates reading the input JSON, parsing it, defining `encodeOptions`, and then either performing a full encode for token statistics or streaming the output directly using `encodeLines` for efficiency. Error handling for JSON parsing is also included.

## 5. Potential Pitfalls
-   **Invalid Argument Values**: The CLI performs validation for several arguments like `delimiter`, `indent`, `keyFolding`, `flattenDepth`, and `expandPaths`. Providing invalid values will result in an error and program exit. Users should refer to the help message for valid options.
-   **JSON Parsing Errors**: When encoding from JSON, if the input JSON is malformed or invalid, the CLI will fail to parse it, leading to an error. Ensure input JSON is well-formed.
-   **TOON Decoding Errors (Strict Mode)**: If `strict` mode is enabled (default) during decoding, any non-compliant TOON syntax will cause decoding to fail. Users can disable strict mode (`--strict=false`) for more lenient parsing, but this might lead to unexpected results.
-   **Large File Performance with Path Expansion**: When decoding with `expandPaths='safe'`, the entire TOON content is read into memory before decoding. For very large TOON files, this could lead to higher memory consumption compared to the streaming approach used when `expandPaths` is `'off'`.

## Usage Examples

**1. Encode JSON from a file to TOON and write to another file:**
```bash
toon-cli input.json -o output.toon --encode --indent 4 --delimiter ","
```

**2. Decode TOON from stdin to JSON and print to stdout:**
```bash
cat input.toon | toon-cli --decode --indent 2
```

**3. Encode JSON with key folding and token statistics:**
```bash
toon-cli data.json -o folded.toon --encode --keyFolding safe --stats
```

**4. Decode TOON with path expansion:**
```bash
toon-cli config.toon -o expanded.json --decode --expandPaths safe
```

**5. Decode TOON from a file with non-strict parsing:**
```bash
toon-cli data.toon --decode --strict false
```