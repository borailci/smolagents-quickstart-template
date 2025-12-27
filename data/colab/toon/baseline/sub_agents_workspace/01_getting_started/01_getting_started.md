'''
# Getting Started with TOON

This tutorial will guide you through the basics of using the `@toon-format/toon` library to encode and decode data in the Token-Oriented Object Notation (TOON) format.

## 1. Goal

The primary goal of TOON is to provide a compact, human-readable, and schema-aware data format that is highly efficient for Large Language Model (LLM) prompts. By the end of this tutorial, you will know how to convert JSON data into a TOON string and back.

## 2. Prerequisites

Before you begin, ensure you have [Node.js](https://nodejs.org/) installed. You can install the `@toon-format/toon` package using your favorite package manager:

```bash
npm install @toon-format/toon
# or
yarn add @toon-format/toon
# or
pnpm add @toon-format/toon
```

## 3. Core Concepts: Encoding & Decoding

TOON revolves around two primary operations: encoding and decoding. The process is straightforward: you encode your structured data (like a JavaScript object) into a TOON string and decode a TOON string back into structured data.

```mermaid
graph TD
    A[JavaScript Object] -->|`encode()`| B(TOON String);
    B -->|`decode()`| C[JavaScript Object];
```

## 4. Implementation

Let's walk through a practical example. We'll take a simple JavaScript object, encode it into a TOON string, and then decode it back.

### Encoding Data

First, import the `encode` function and create an object to work with.

```javascript
import { encode } from '@toon-format/toon';

const user = {
  name: 'Alice',
  age: 30,
  roles: ['admin', 'editor']
};

const toonString = encode(user);

console.log(toonString);
```

Running this code will produce the following output, which is the TOON representation of the `user` object:

```
name: Alice
age: 30
roles[]:
  - admin
  - editor
```

As you can see, the format is clean, easy to read, and uses indentation to represent structure, much like YAML.

### Decoding Data

Now, let's take that `toonString` and convert it back into a JavaScript object using the `decode` function.

```javascript
import { decode } from '@toon-format/toon';

const toonString = `
name: Alice
age: 30
roles[]:
  - admin
  - editor
`;

const userObject = decode(toonString);

console.log(userObject);
```

This will give you back the original object:

```json
{
  "name": "Alice",
  "age": 30,
  "roles": [
    "admin",
    "editor"
  ]
}
```

## 5. Conclusion

You have successfully learned how to use the `@toon-format/toon` library to encode JavaScript objects into the TOON format and decode them back. This simple yet powerful tool helps create more readable and token-efficient data representations, especially for LLM applications.
'''