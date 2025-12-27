'''
# Toon Shared Utilities Analysis

## 1. Overview

The `toon/src/shared` directory contains utility modules that provide fundamental functionalities for the `@toon-format/toon` package. These modules handle the low-level tasks of parsing and serializing the Token-Oriented Object Notation (TOON) format. Their responsibilities include identifying literal values (booleans, nulls, numbers), managing string escaping and unescaping, and validating whether keys and string values require quoting. These utilities are crucial for ensuring the correctness and efficiency of the TOON encoder and decoder.

## 2. File-by-File Analysis

### `packages/toon/src/shared/literal-utils.ts`

- **Purpose**: This module provides functions to detect and validate literal values based on their string representation. It is used during the parsing phase to distinguish numbers, booleans, and nulls from plain strings.
- **Key Components**:
  - `isBooleanOrNullLiteral()`: Checks if a token exactly matches "true", "false", or "null".
  - `isNumericLiteral()`: Validates if a string is a well-formed numeric literal according to JSON-like rules, notably prohibiting leading zeros on integers (e.g., `01` is invalid).

### `packages/toon/src/shared/string-utils.ts`

- **Purpose**: This module is responsible for handling the complexities of string manipulation, specifically escaping and unescaping special characters. It also includes helper functions for parsing string content, like finding the end of a quoted section.
- **Key Components**:
  - `escapeString()`: Escapes special characters (`\`, `"`, `\n`, `\r`, `\t`) in a string so it can be safely embedded in a TOON document.
  - `unescapeString()`: Converts escape sequences back into their corresponding characters.
  - `findClosingQuote()`: A utility for parsing that finds the matching closing double-quote for a string, correctly handling escaped quotes within it.
  - `findUnquotedChar()`: Locates a specific character within a string that is not inside a quoted section, essential for finding structural delimiters.

### `packages/toon/src/shared/validation.ts`

- **Purpose**: This module contains validation logic to determine whether identifiers (keys) and string values can be written in an unquoted form. This is key to TOON's goal of being human-readable and compact.
- **Key Components**:
  - `isValidUnquotedKey()`: Checks if a string is a valid key that can be used without quotes (must start with a letter or underscore, and can contain letters, numbers, underscores, or dots).
  - `isIdentifierSegment()`: A stricter version of `isValidUnquotedKey` that disallows dots, used for safely folding and expanding object keys.
  - `isSafeUnquoted()`: A comprehensive check to determine if a string value can be safely left unquoted. It returns `false` if the string could be misinterpreted as another type (like a number or boolean), contains structural characters, or includes whitespace that needs preserving.

## 3. API Reference

The following table provides a complete reference for all public functions exported from the `toon/src/shared` modules.

| Function                | Signature                                                    | Description                                                                                                                                                           |
| ----------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `isBooleanOrNullLiteral`| `(token: string): boolean`                                   | Checks if the input string is `"true"`, `"false"`, or `"null"`.                                                                                                          |
| `isNumericLiteral`      | `(token: string): boolean`                                   | Validates if the string is a valid numeric literal. Rejects numbers with leading zeros (e.g., `05`) but allows `0` and decimals like `0.5`.                                |
| `escapeString`          | `(value: string): string`                                    | Escapes backslashes, double quotes, newlines, carriage returns, and tabs.                                                                                             |
| `unescapeString`        | `(value: string): string`                                    | Converts `\n`, `\t`, `\r`, `\\`, and `\"` escape sequences into their actual character representation. Throws a `SyntaxError` on invalid escape sequences.          |
| `findClosingQuote`      | `(content: string, start: number): number`                   | Finds the index of the next closing double quote (`"`) in a string, starting the search from the `start` index and correctly skipping escaped quotes (`\"`). Returns -1 if not found. |
| `findUnquotedChar`      | `(content: string, char: string, start = 0): number`         | Finds the index of a character in the content that is not enclosed within double quotes. Returns -1 if not found.                                                         |
| `isValidUnquotedKey`    | `(key: string): boolean`                                     | Checks if a key can be used without quotes (starts with `[A-Z_]`, followed by `[\w.]*`).                                                                                |
| `isIdentifierSegment`   | `(key: string): boolean`                                     | Checks if a key segment is a valid identifier for dot-notation (starts with `[A-Z_]`, followed by `[\w]*`). Does not allow dots.                                          |
| `isSafeUnquoted`        | `(value: string, delimiter: string = DEFAULT_DELIMITER): boolean` | Determines if a string value can be safely encoded without quotes by checking for conflicts with literals, structural characters, and whitespace.                      |
'''