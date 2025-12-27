
# Tutorial: Error Handling in TOON

## 1. Synopsis

When working with any data format, it's crucial to handle potential errors gracefully. Real-world data can be messy, incomplete, or malformed. This tutorial will guide you through the best practices for handling errors when decoding TOON strings, ensuring your applications are robust and resilient.

We will explore how the `@toon-format/toon` decoder behaves with invalid input and how to use standard `try...catch` blocks to manage parsing errors. We will also delve into the `strict` option in `DecodeOptions` to enforce stricter validation of your TOON data.

## 2. Prerequisites

Before you begin, ensure you have the `@toon-format/toon` package installed in your project.

```bash
npm install @toon-format/toon
```

## 3. Architecture

At its core, error handling for TOON decoding involves wrapping the `decode` function call within a `try...catch` block. This allows you to intercept any parsing errors and handle them in a controlled manner.

```mermaid
graph TD
    A["TOON String (potentially invalid)"] --> B{decode()};
    B -- "Valid TOON" --> C[Successfully Decoded Object];
    B -- "Invalid TOON" --> D{Catch Block};
    D --> E["Handle Error (e.g., log, return default)"];
```

## 4. Implementation Steps

### Step 1: Basic Error Handling with `try...catch`

The most straightforward way to handle errors is to wrap the `decode` function in a `try...catch` block. If the TOON string is malformed, the `decode` function will throw an error, which you can then catch and handle.

Let's see what happens when we try to decode an invalid TOON string.

```javascript
import { decode } from '@toon-format/toon';

const invalidToon = `
name: "John Doe"
age: 30oops
`;

try {
  const data = decode(invalidToon);
  console.log('Decoded data:', data);
} catch (error) {
  console.error('Failed to decode TOON string:', error.message);
}
```

***Verification***

When you run this code, the `decode` function will fail because `30oops` is not a valid number. The `catch` block will execute, and you will see an output similar to this:

```
Failed to decode TOON string: Invalid primitive value: 30oops
```

### Step 2: Enforcing Structural Integrity with the `strict` Option

The `decode` function provides a `strict` option within the `DecodeOptions` object. When `strict` is set to `true` (the default), the decoder performs additional checks to ensure the structure of the TOON data is sound. For example, it verifies that the number of items in an array matches the declared length.

Let's look at an example where the declared array length does not match the actual number of items.

```javascript
import { decode } from '@toon-format/toon';

// Invalid TOON: Declares 2 items, but provides only 1
const invalidArrayToon = `
items[2]:
- "one"
`;

try {
  // With strict: true (default), this will throw an error
  const data = decode(invalidArrayToon, { strict: true });
  console.log('Decoded data (strict):', data);
} catch (error) {
  console.error('Strict mode error:', error.message);
}

try {
  // With strict: false, this will not throw and will decode what it can
  const data = decode(invalidArrayToon, { strict: false });
  console.log('Decoded data (non-strict):', data);
} catch (error) {
  // This block will not be reached
  console.error('Non-strict mode error:', error.message);
}
```

***Verification***

Running this code will produce the following output:

```
Strict mode error: Expected 2 list array items, but found 1.
Decoded data (non-strict): { items: [ 'one' ] }
```

As you can see, `strict: true` helps you catch inconsistencies in your data, while `strict: false` offers a more lenient parsing mode.

## 5. Common Pitfalls

- **Invalid Primitive Values**: Ensure that numbers, booleans, and null values are correctly formatted (e.g., `true`, `false`, `null`, `123`, `1.23`).
- **Incorrect Indentation**: TOON relies on indentation to determine the structure of the data. Make sure your indentation is consistent.
- **Mismatched Array Lengths**: When using the `strict` mode, always ensure that the number of items in an array matches the length specified in the header.

## 6. Challenge Yourself

Write a function that takes a TOON string as input and attempts to decode it. If the decoding is successful, the function should return the decoded object. If an error occurs, the function should log the error to the console and return an empty object (`{}`).

Test your function with the following TOON strings:

1.  A valid TOON string.
2.  A TOON string with a syntax error.
3.  A TOON string with an incorrect array length, using `strict: true`.

This exercise will help you solidify your understanding of error handling with the `@toon-format/toon` library.
