# Best Practices and Troubleshooting for TOON

TOON (Typed Object Notation) is a human-readable, structured data format designed for configuration files and data interchange. It offers features like array headers, tabular data representation, and key folding for compactness. This tutorial outlines best practices for leveraging TOON effectively and provides guidance on troubleshooting common issues.

## When to Use TOON

TOON excels in scenarios where human readability, structured data, and efficiency are paramount. Consider using TOON over other formats like JSON, YAML, XML, or CSV when:

*   **Human Readability is Key**: TOON's syntax, with its clear key-value pairs, indentation, and array headers, is often more approachable for human editors compared to the verbosity of JSON or XML.
*   **Configuration Files**: Its focus on structured data and readability makes it ideal for application configuration where settings need to be easily understood and modified by developers or even end-users.
*   **Data Interchange with Compactness**: While human-readable, features like key folding allow TOON to achieve greater compactness than JSON for deeply nested objects, which can be beneficial in scenarios like prompt engineering for Language Models (LLMs) where token efficiency is important.
*   **Tabular Data Representation**: TOON's explicit array headers make it excellent for representing tabular data directly within the document, similar to CSV but with more context and structure. This avoids the need for external schemas or complex parsing logic.
*   **Streaming Operations**: The `toon` library supports both synchronous and asynchronous streaming, making it suitable for processing large datasets efficiently without loading everything into memory.

### Comparison with Other Formats

TOON often provides a good balance between human readability (like YAML) and programmatic parseability (like JSON), with added benefits for compactness and tabular data. Compared to JSON, TOON can offer better token efficiency for LLMs due to key folding.

## Tips for Writing Clear and Efficient TOON Files

Adhering to these best practices will help you create TOON files that are both easy to understand and efficient to process.

### 1. Leverage Key Folding for Compactness

Key folding is a powerful feature in TOON that allows compact representation of nested single-key objects. This significantly reduces verbosity, especially for deeply nested configurations, and improves token efficiency when passed to LLMs.

**Best Practice**: Use key folding for nested objects where appropriate. The `toon` library and CLI support a `
### 2. Use Explicit Array Headers for Tabular Data

TOON's array headers provide a clear and structured way to define tabular data. This is particularly useful for datasets that have a consistent schema.

**Best Practice**: For tabular data, always define an array header to specify the column names and optionally the number of rows. This makes the data self-describing and easier to parse.

```toon
# Example of a tabular array with header
users[2]{id,name,email}:
  1,Alice,alice@example.com
  2,Bob,bob@example.com
```

**Bad Example (without header - ambiguous)**:

```toon
# Ambiguous array representation
users:
  1,Alice,alice@example.com
  2,Bob,bob@example.com
```

In the bad example, it's unclear what `1`, `Alice`, and `alice@example.com` represent without external context. The header clarifies the structure.

### 3. Maintain Consistent Indentation

Consistent indentation is crucial for readability and correct parsing in TOON. It visually represents the nesting level of your data.

**Best Practice**: Choose an indentation style (e.g., 2 spaces, 4 spaces) and stick to it throughout your TOON files. The `toon-cli` offers an `--indent` option to help automate this.

```toon
# Good Indentation
config:
  database:
    host: localhost
    port: 5432
```

```toon
# Bad Indentation (difficult to read and potentially problematic)
config:
  database:
   host: localhost
  port: 5432
```

### 4. Choose Appropriate Delimiters

TOON supports different delimiters for values within arrays (e.g., comma, space). Selecting the right delimiter can improve readability based on your data.

**Best Practice**: Use delimiters that do not conflict with the data itself. For simple comma-separated values, a comma is fine. If your data contains commas, consider using a different delimiter like a space or pipe (`|`). The `toon-cli` provides a `--delimiter` option.

```toon
# Using comma as delimiter
items[2]{name,price}:
  "Apple, Red",0.99
  "Banana, Yellow",0.79
```

**Note**: When a value contains the chosen delimiter, it should be quoted.

### 5. Comments for Clarity

Use comments to explain complex sections, provide context, or temporarily disable parts of your configuration.

**Best Practice**: Add comments (`#`) to explain the purpose of specific sections, important values, or any non-obvious configurations. 

```toon
# This is the main application configuration
app:
  name: MyAwesomeApp
  # Enable debug mode only for development environments
  debug_mode: true
```

## Troubleshooting Common Issues

### 1. Parsing Errors (Syntax Issues)

TOON is a structured format, and minor syntax errors can lead to parsing failures. The `toon` library and CLI aim to provide informative error messages.

**Symptom**: The TOON parser throws an error indicating unexpected tokens, missing colons, or incorrect indentation.

**Possible Causes and Solutions**:

*   **Incorrect Indentation**: Ensure consistent indentation. Mixing tabs and spaces, or inconsistent spacing, is a common cause. Use a text editor that shows invisible characters, or use the `toon-cli` with the `--indent` option to reformat.

    ```bash
    toon-cli broken.toon -o fixed.toon --decode --indent 2
    ```

*   **Missing Colon (`:`)**: Every key-value pair must be separated by a colon.

    **Bad**:
    ```toon
    key value
    ```

    **Good**:
    ```toon
    key: value
    ```

*   **Malformed Array Headers**: Array headers must follow the `name[rows]{columns}:` syntax. Ensure brackets and curly braces are correctly used.

    **Bad**:
    ```toon
    users{id,name}:
    ```

    **Good**:
    ```toon
    users[2]{id,name}:
    ```

*   **Unquoted Special Characters**: If a key or value contains spaces, colons, or delimiters, it must be enclosed in quotes.

    **Bad**:
    ```toon
    my key: my value
    ```

    **Good**:
    ```toon
    "my key": "my value"
    ```

*   **Strict Mode**: By default, the `toon` decoder operates in `strict` mode. This means it will reject any non-compliant TOON syntax. If you encounter issues with seemingly valid TOON, consider temporarily disabling strict mode to see if it's a subtle compliance issue. However, disabling strict mode should be used with caution as it might lead to unexpected data interpretations.

    ```bash
    toon-cli input.toon --decode --strict false
    ```

### 2. Unexpected Data Structures After Decoding

Sometimes, a TOON file might decode but result in a JavaScript object that doesn't match expectations, especially regarding nested structures.

**Symptom**: A flat object when nested was expected, or vice-versa.

**Possible Causes and Solutions**:

*   **Key Folding During Encoding / Missing Path Expansion During Decoding**: If the original data was encoded with key folding (e.g., `user.profile.name: Alice`), and you decode it without `expandPaths`, you will get a flat key. 

    **Solution**: Always use `expandPaths` during decoding if the TOON was potentially created with key folding.

    ```bash
    toon-cli folded.toon -o expanded.json --decode --expandPaths safe
    ```

    Or, in code:

    ```typescript
    import { decode } from '@toon';
    const decodedValue = decode(toonInput, { expandPaths: 'safe' });
    ```

*   **Incorrect Delimiter/Indentation in Input**: While parsing, incorrect delimiters or indentation might lead to misinterpretation of object boundaries or array elements.

    **Solution**: Re-verify your TOON file's formatting. Consider using a TOON linter if available, or visually inspect for inconsistencies.

### 3. Performance Issues with Large Files

Processing very large TOON files can sometimes lead to memory or performance bottlenecks.

**Symptom**: Application slows down, or runs out of memory when processing large TOON inputs.

**Possible Causes and Solutions**:

*   **Non-Streaming Operations**: If you are using `decode` or `encode` directly on very large strings, the entire content is loaded into memory. 

    **Solution**: Utilize the streaming APIs for both encoding and decoding (`encodeLines`, `decodeFromLines`, `decodeStreamSync`, `decodeStream`). The `toon-cli` uses streaming by default unless `expandPaths` is enabled, which requires reading the entire content.

    ```typescript
    import { decodeStream } from '@toon';

    async function processStream(toonStream: AsyncIterable<string>) {
      for await (const event of decodeStream(toonStream)) {
        // Process events as they arrive, without holding the entire object in memory
        console.log(event);
      }
    }
    ```

*   **`expandPaths='safe'` for Large Files**: As noted in the `packages_cli.md` documentation, using `expandPaths='safe'` requires reading the entire TOON content into memory before processing. This can be memory-intensive for very large files.

    **Solution**: If memory is an issue and full path expansion is not strictly necessary, consider decoding without `expandPaths` or process the data in smaller chunks if possible.

## Data Flow Diagram: TOON CLI Conversion

Here's a Mermaid diagram illustrating the data flow within the TOON CLI when performing a conversion.

```mermaid
graph LR
    A[Input Source: File or Stdin] --> B{CLI Main Command}
    B --> C{Detect Mode: Encode or Decode}

    C -- Encode --> D[encodeToToon Function]
    D --> E[Read Input JSON] 
    E --> F[Parse JSON] 
    F --> G[TOON Library: encode(data, options)]
    G -- TOON Lines Stream --> H[Write Output: File or Stdout (TOON)]
    H -- Optional: --stats --> I[Token Statistics Calculation]

    C -- Decode --> J[decodeToJson Function]
    J --> K[Read Input TOON] 
    K --> L[TOON Library: decode(toonInput, options)]
    L -- JSON Object --> M[Stringify JSON] 
    M --> N[Write Output: File or Stdout (JSON)]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style H fill:#bbf,stroke:#333,stroke-width:2px
    style N fill:#bbf,stroke:#333,stroke-width:2px
    style B fill:#ccf,stroke:#333,stroke-width:2px
    style C fill:#ccf,stroke:#333,stroke-width:2px
    style D fill:#ddf,stroke:#333,stroke-width:2px
    style G fill:#ddf,stroke:#333,stroke-width:2px
    style J fill:#ddf,stroke:#333,stroke-width:2px
    style L fill:#ddf,stroke:#333,stroke-width:2px
    style E fill:#eee,stroke:#333,stroke-width:1px
    style F fill:#eee,stroke:#333,stroke-width:1px
    style K fill:#eee,stroke:#333,stroke-width:1px
    style M fill:#eee,stroke:#333,stroke-width:1px
    style I fill:#fcf,stroke:#333,stroke-width:1px
```
