# TOON CLI Usage

This tutorial will guide you through the usage of the TOON Command Line Interface (CLI), a powerful tool for converting between JSON and TOON formats.

## 1. Goal

By the end of this tutorial, you will be able to:

*   Install and use the TOON CLI.
*   Convert JSON files to TOON and vice versa.
*   Use various options to customize the conversion process.

## 2. Prerequisites

*   Node.js and npm (or a compatible package manager) installed.
*   The `@toon-format/cli` package installed globally:

```bash
npm install -g @toon-format/cli
```

## 3. Architecture

The TOON CLI can operate in two primary modes: `encode` (JSON to TOON) and `decode` (TOON to JSON). The CLI automatically detects the mode based on the input, but you can also explicitly specify it.

```mermaid
graph TD
    A[Input (JSON or TOON)] --> B{TOON CLI};
    B --> |Encode| C[TOON Output];
    B --> |Decode| D[JSON Output];
```

## 4. Implementation

The TOON CLI is invoked using the `toon` command.

### Basic Usage

The general syntax is:

```bash
toon [input] [options]
```

*   `[input]`: The path to the input file. If omitted or set to `-`, the CLI reads from standard input (stdin).

### Options

The CLI provides several options to control the conversion process:

| Option | Alias | Description | Default |
| --- | --- | --- | --- |
| `--output` | `-o` | Output file path. If omitted, the CLI writes to standard output (stdout). | - |
| `--encode` | `-e` | Force encoding to TOON. | Auto-detected |
| `--decode` | `-d` | Force decoding to JSON. | Auto-detected |
| `--delimiter`| | Delimiter for arrays: `comma` (`,`), `tab` (`\t`), or `pipe` (`|`). | `,` |
| `--indent` | | Indentation size for JSON output. | `2` |
| `--strict` | | Enable strict mode for decoding. | `true` |
| `--keyFolding` | | Enable key folding: `off`, `safe`. | `off` |
| `--flattenDepth`| | Maximum folded segment count when key folding is enabled. | `Infinity` |
| `--expandPaths`| | Enable path expansion: `off`, `safe`. | `off` |
| `--stats` | | Show token statistics. | `false` |

### Examples

#### Encoding JSON to TOON

Given a `data.json` file:

```json
{
  "name": "John Doe",
  "age": 30,
  "skills": ["JavaScript", "Python", "TOON"]
}
```

You can convert it to TOON using:

```bash
toon data.json -o data.toon
```

This will create a `data.toon` file with the following content:

```toon
name: John Doe
age: 30
skills: JavaScript, Python, TOON
```

#### Decoding TOON to JSON

Conversely, you can convert `data.toon` back to JSON:

```bash
toon data.toon -o new_data.json
```

This will produce a `new_data.json` file identical to the original `data.json`.

#### Using with Pipes (stdin/stdout)

The TOON CLI seamlessly integrates with shell pipelines.

**Encoding:**

```bash
cat data.json | toon > data.toon
```

**Decoding:**

```bash
cat data.toon | toon > new_data.json
```

### Advanced Features

#### Key Folding

Key folding allows you to represent nested objects in a more compact way. Use the `--keyFolding safe` option to enable it.

**Example:**

Given this JSON:

```json
{
  "user": {
    "name": "Jane Doe",
    "address": {
      "city": "New York",
      "country": "USA"
    }
  }
}
```

Encoding with key folding:

```bash
toon input.json --keyFolding safe > output.toon
```

Results in `output.toon`:

```toon
user.name: Jane Doe
user.address.city: New York
user.address.country: USA
```

#### Path Expansion

Path expansion is the reverse of key folding, used during decoding to convert a flattened TOON structure back into a nested JSON object. Use the `--expandPaths safe` option.

**Example:**

Given `input.toon`:

```toon
user.name: Jane Doe
user.address.city: New York
user.address.country: USA
```

Decoding with path expansion:

```bash
toon input.toon --expandPaths safe > output.json
```

This will recreate the original nested JSON structure.

## 5. Conclusion

The TOON CLI is a versatile and powerful tool for working with TOON and JSON data. Its support for file-based conversion, stdin/stdout pipelines, and advanced features like key folding and path expansion makes it an essential utility for any developer working with these formats.