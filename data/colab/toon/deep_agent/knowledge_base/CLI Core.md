'''
# CLI Core Technical Analysis

## 1. Overview

The `@toon-format/cli` package provides a command-line interface (CLI) for converting data between JSON and TOON formats. It allows users to read from `stdin` or a file, and write the converted output to `stdout` or a file. The CLI is built using the `citty` framework and provides various options to control the encoding and decoding process.

## 2. File-by-File Analysis

### `packages/cli/src/cli-entry.ts`

- **Purpose**: This is the main entry point for the CLI application. It imports the `mainCommand` from `./index.ts` and executes it using `runMain` from the `citty` library.

### `packages/cli/src/index.ts`

- **Purpose**: This file defines the structure and logic of the main CLI command.
- **Key Components**:
  - `mainCommand`: A `CommandDef` object created with `citty`'s `defineCommand`. It defines the CLI's metadata (name, description, version), arguments (flags and positional), and the main execution logic in the `run` function.
  - The `run` function parses arguments, validates them, determines the conversion mode (encode or decode), and calls the appropriate function from `conversion.ts`.

### `packages/cli/src/conversion.ts`

- **Purpose**: This file contains the core logic for the JSON to TOON and TOON to JSON conversions.
- **Key Components**:
  - `encodeToToon()`: Reads JSON data from the specified input, parses it, and then encodes it into the TOON format using the `encode` or `encodeLines` functions from the `@toon-format/toon` package. It can write the output in a streaming fashion to a file or `stdout`. It also includes an option to print token count statistics.
  - `decodeToJson()`: Reads TOON data from the input. It supports both a streaming decoding approach (`decodeStream`) for efficiency and a non-streaming approach (`decode`) when features like `expandPaths` are used. The resulting JSON is then written to the output, also in a streaming manner.
  - `writeStreamingJson()` / `writeStreamingToon()`: Helper functions for writing output to a file or `stdout` using streams to handle potentially large files without consuming excessive memory.

### `packages/cli/src/types.ts`

- **Purpose**: Defines shared TypeScript types used across the CLI module.
- **Key Components**:
  - `InputSource`: A discriminated union type that represents the source of the input data, which can be either standard input (`stdin`) or a file path (`file`).

## 3. Public Interface & API Reference

The public interface of this module is the `toon` command-line tool.

**Command:** `toon`

**Description:** TOON CLI — Convert between JSON and TOON formats

| Argument/Option | Alias | Type      | Description                                                     | Default     |
|-----------------|-------|-----------|-----------------------------------------------------------------|-------------|
| `input`         |       | positional| Input file path (omit or use "-" to read from stdin)            | (none)      |
| `--output`      | `-o`  | `string`  | Output file path                                                | (none)      |
| `--encode`      | `-e`  | `boolean` | Encode JSON to TOON (auto-detected by default)                  | `false`     |
| `--decode`      | `-d`  | `boolean` | Decode TOON to JSON (auto-detected by default)                  | `false`     |
| `--delimiter`   |       | `string`  | Delimiter for arrays: comma (,), tab (\t), or pipe (\|)      | `,`         |
| `--indent`      |       | `string`  | Indentation size                                                | `2`         |
| `--strict`      |       | `boolean` | Enable strict mode for decoding                                 | `true`      |
| `--key-folding` |       | `string`  | Enable key folding: `off`, `safe`                               | `off`       |
| `--flatten-depth` |     | `string`  | Maximum folded segment count when key folding is enabled        | `Infinity`  |
| `--expand-paths` |      | `string`  | Enable path expansion: `off`, `safe`                            | `off`       |
| `--stats`       |       | `boolean` | Show token statistics                                           | `false`     |

## 4. Integration Points

- **`@toon-format/toon`**: The core dependency that provides the actual `encode`, `decode`, `encodeLines`, and `decodeStream` functions for TOON processing.
- **`citty`**: A third-party library used to build the command-line interface, including argument parsing and command definition.
- **`consola`**: Used for logging user-friendly messages, successes, and errors to the console.
- **`tokenx`**: Used to estimate the number of tokens in the JSON and TOON content for statistical analysis.
- **Node.js APIs**: Utilizes built-in Node.js modules like `fs/promises` for file I/O, `path` for path manipulation, and `process` for `stdin`/`stdout` access.

## 5. Use Cases

- **Converting JSON to TOON**: A developer can pipe a JSON file to the CLI to convert it to TOON format, which can be more compact and human-readable.
  ```sh
  cat data.json | toon > data.toon
  ```
- **Converting TOON to JSON**: A developer can convert a TOON file back into standard JSON for use with other tools.
  ```sh
  toon data.toon -o data.json
  ```
- **Token Savings Analysis**: A user can check how many tokens are saved by converting a JSON file to TOON using the `--stats` flag.
  ```sh
  toon -e --stats -i data.json
  ```
'''