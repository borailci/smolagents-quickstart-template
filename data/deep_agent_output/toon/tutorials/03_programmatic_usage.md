# Programmatic Usage: The `toon` Library

This tutorial introduces the core `toon` library, a powerful tool for converting data between JavaScript objects and the human-readable TOON (Typed Object Notation) format. TOON is designed for configuration files and data interchange, offering features like array headers, tabular data representation, and key folding for compactness.

We will focus on the fundamental `encode` and `decode` functions, demonstrating how to use them in a JavaScript/TypeScript project to convert between JSON objects and TOON strings.

## Installation

To get started, install the `toon` library using your preferred package manager:

```bash
npm install @toon-lang/toon
# or
yarn add @toon-lang/toon
# or
pnpm add @toon-lang/toon
```

## Encoding JavaScript Objects to TOON Strings

The `encode` function transforms a JavaScript object into a TOON formatted string. This is useful for saving configuration, generating human-readable data, or preparing data for systems that consume TOON.

### Basic Encoding

Let's take a simple JavaScript object and encode it:

```typescript
import { encode } from '@toon-lang/toon';

const userData = {
  name: 'Alice',
  age: 30,
  isActive: true,
  email: 'alice@example.com'
};

const toonString = encode(userData);
console.log(toonString);
```

**Output:**

```
name: Alice
age: 30
isActive: true
email: alice@example.com
```

### Encoding with Key Folding

TOON supports "key folding," a feature that condenses nested single-key objects into a single dot-separated key, making the output more compact. You can enable this with the `keyFolding: 'safe'` option.

```typescript
import { encode } from '@toon-lang/toon';

const configData = {
  server: {
    host: 'localhost',
    port: 8080
  },
  database: {
    type: 'postgresql',
    credentials: {
      user: 'admin',
      password: 'secret'
    }
  },
  logLevel: 'info'
};

const foldedToonString = encode(configData, { keyFolding: 'safe' });
console.log(foldedToonString);
```

**Output:**

```
server.host: localhost
server.port: 8080
database.type: postgresql
database.credentials.user: admin
database.credentials.password: secret
logLevel: info
```

### Encoding Flow Diagram

```mermaid
graph TD
    A[JavaScript Object] -->|Input| B(encode() function)
    B --> C{Resolve Encoding Options}
    C --> D{Normalize Value & Apply Replacer}
    D --> E[Encode JSON Value Recursively]
    E --> F{Key Folding (if enabled)}
    F --> G[Generate TOON Lines]
    G --> H[TOON String]
```

## Decoding TOON Strings to JavaScript Objects

The `decode` function performs the reverse operation, converting a TOON formatted string back into a JavaScript object. This is essential for parsing configuration files or data received in TOON format.

### Basic Decoding

Here's how to decode a simple TOON string:

```typescript
import { decode } from '@toon-lang/toon';

const toonInput = `
product: Laptop
price: 1200
available: true
features:
  - display: 15.6 inch
  - processor: Intel i7
`;

const decodedObject = decode(toonInput);
console.log(JSON.stringify(decodedObject, null, 2));
```

**Output:**

```json
{
  "product": "Laptop",
  "price": 1200,
  "available": true,
  "features": [
    {
      "display": "15.6 inch"
    },
    {
      "processor": "Intel i7"
    }
  ]
}
```

### Decoding with Path Expansion

If a TOON string was generated using key folding, you'll want to "expand paths" during decoding to reconstruct the original nested object structure. Use the `expandPaths: 'safe'` option for this.

```typescript
import { decode } from '@toon-lang/toon';

const foldedToonInput = `
app.name: My App
app.version: 1.0.0
db.host: db.example.com
db.port: 5432
`;

const expandedObject = decode(foldedToonInput, { expandPaths: 'safe' });
console.log(JSON.stringify(expandedObject, null, 2));
```

**Output:**

```json
{
  "app": {
    "name": "My App",
    "version": "1.0.0"
  },
  "db": {
    "host": "db.example.com",
    "port": 5432
  }
}
```

### Decoding Flow Diagram

```mermaid
graph TD
    A[TOON String] -->|Input| B(decode() function)
    B --> C{Resolve Decoding Options}
    C --> D[Split into Lines]
    D --> E{Stream Decoder (Events)}
    E --> F[Build Value From Events]
    F --> G{Expand Paths (if enabled)}
    G --> H[JavaScript Object]
```

## Conclusion

The `toon` library provides a straightforward API for converting between JavaScript objects and TOON strings. The `encode` and `decode` functions, along with their powerful options like `keyFolding` and `expandPaths`, offer flexibility for handling various data structures and optimizing output compactness. This makes `toon` an excellent choice for managing configurations and data interchange in your JavaScript/TypeScript projects.