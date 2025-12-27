'''
# Plan for Tutorial Series: Getting Started with TOON

This document outlines a plan for a series of tutorials to introduce developers to the TOON format, CLI, and library.

## Tutorial Series Outline

### 1. Introduction to TOON

*   **Goal**: Introduce the TOON format and its benefits.
*   **Content**:
    *   What is TOON (Token-Oriented Object Notation)?
    *   Why use TOON? (token efficiency, human-readability, schema-awareness).
    *   Basic syntax and a comparison with JSON.
    *   A simple example of a TOON file.
*   **Mermaid Diagram**:

    ```mermaid
    graph TD
        A[JSON] --> B{TOON Conversion};
        B --> C[TOON];
        C --> B;
    ```

### 2. Using the TOON CLI

*   **Goal**: Teach users how to use the TOON command-line interface.
*   **Content**:
    *   Installation: `npm install -g @toon-format/cli`
    *   Converting JSON to TOON: `toon < input.json > output.toon`
    *   Converting TOON to JSON: `toon --reverse < input.toon > output.json`
    *   Working with files and pipes.
*   **Code Snippets**:

    ```bash
    # Install the CLI
    npm install -g @toon-format/cli

    # Convert JSON to TOON
    echo '{"name": "John", "age": 30}' | toon

    # Convert TOON to JSON
    echo '(name "John" age 30)' | toon --reverse
    ```

### 3. Using the TOON Library

*   **Goal**: Show developers how to use the TOON library in their projects.
*   **Content**:
    *   Installation: `npm install @toon-format/toon`
    *   Parsing TOON strings to JavaScript objects.
    *   Stringifying JavaScript objects to TOON strings.
*   **Code Snippets**:

    ```javascript
    import { parse, stringify } from '@toon-format/toon';

    const toonString = '(name "John" age 30)';
    const obj = parse(toonString);
    console.log(obj); // { name: 'John', age: 30 }

    const newObj = { city: "New York", country: "USA" };
    const newToonString = stringify(newObj);
    console.log(newToonString); // (city "New York" country "USA")
    ```

### 4. Advanced TOON: Schemas

*   **Goal**: Introduce the concept of schemas in TOON for improved efficiency.
*   **Content**:
    *   What are TOON schemas?
    *   How schemas can reduce token count.
    *   Defining a schema.
    *   Using a schema with the TOON library.
*   **Mermaid Diagram**:

    ```mermaid
    graph TD
        A[JSON + Schema] --> B{TOON Conversion};
        B --> C[Compressed TOON];
    ```
'''