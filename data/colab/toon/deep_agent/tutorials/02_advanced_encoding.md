# Advanced TOON Encoding: Customizing Your Output

## 1. Synopsis

While TOON's default encoding is optimized for many use cases, you often need more control over the final output. Whether you're formatting data for a specific model, improving human readability, or creating more compact structures, the `EncodeOptions` interface provides the necessary tools. This tutorial explores how to use `indent`, `delimiter`, and `keyFolding` to tailor the encoded TOON string to your exact requirements.

## 2. Prerequisites

Before you begin, ensure you have the `@toon-format/toon` package installed in your project.

```bash
npm install @toon-format/toon
```

## 3. Architecture: The Encoding Pipeline

The `encode` function is not just a simple serializer. It includes a processing pipeline where your options can modify the structure and format of the output.

```mermaid
graph TD
    A["Input JavaScript Object"] --> B{encode(input, options)};
    B --> C{Apply Options};
    C -- "indent: number" --> D["Adjust Whitespace"];
    C -- "delimiter: Delimiter" --> E["Format Tabular Arrays"];
    C -- "keyFolding: 'safe'" --> F["Collapse Nested Keys"];
    subgraph Output Generation
        D --> G;
        E --> G;
        F --> G;
    end
    G["Final TOON String"] --> H[Output];

```

## 4. Implementation Steps

Let's start with a sample JavaScript object that we will use to demonstrate the effects of different encoding options.

```javascript
import { encode } from '@toon-format/toon';

const data = {
  user: {
    id: "u-123",
    details: {
      name: "Alex Doe",
      email: "alex.doe@example.com",
    },
  },
  posts: [
    { id: "p-001", title: "First Post", views: 150 },
    { id: "p-002", title: "Second Post", views: 250 },
  ],
};
```

### Step 1: Default Encoding

First, let's see the output of the standard `encode` function with no options.

```javascript
const defaultToon = encode(data);
console.log(defaultToon);
```

***Verification***

The default output uses an indent of 2 spaces and standard object notation.

```toon
user:
  id: u-123
  details:
    name: Alex Doe
    email: alex.doe@example.com
posts: (3)
- id | title | views
- p-001 | First Post | 150
- p-002 | Second Post | 250
```

### Step 2: Customizing Indentation with `indent`

The `indent` option controls the number of spaces used for each level of nesting, making the output more or less compact.

```javascript
const indentedToon = encode(data, { indent: 4 });
console.log(indentedToon);
```

***Verification***

Observe how the nested objects under `user` now have a 4-space indent.

```toon
user:
    id: u-123
    details:
        name: Alex Doe
        email: alex.doe@example.com
posts: (3)
- id | title | views
- p-001 | First Post | 150
- p-002 | Second Post | 250
```

### Step 3: Changing the `delimiter`

The `delimiter` option changes the character used to separate columns in tabular arrays. This is useful if your data contains the default pipe (`|`) character.

```javascript
import { encode, DELIMITERS } from '@toon-format/toon';

const delimitedToon = encode(data, { delimiter: DELIMITERS.comma });
console.log(delimitedToon);
```

***Verification***

The `posts` table now uses a comma as its column separator.

```toon
user:
  id: u-123
  details:
    name: Alex Doe
    email: alex.doe@example.com
posts: (3)
- id , title , views
- p-001 , First Post , 150
- p-002 , Second Post , 250
```

### Step 4: Compacting Output with `keyFolding`

`keyFolding` is a powerful option for creating highly compact TOON. When set to `'safe'`, it collapses nested objects that have only a single key at each level into a single line with dotted keys.

```javascript
const foldedData = {
  config:
    {
      system:
        {
          api:
            {
              endpoint: "https://api.example.com/v1"
            }
        }
    }
};

const foldedToon = encode(foldedData, { keyFolding: 'safe' });
console.log(foldedToon);
```

***Verification***

Instead of multiple nested levels, the structure is flattened into a single, easy-to-read line.

```toon
config.system.api.endpoint: https://api.example.com/v1
```

## 5. Common Pitfalls

- **`keyFolding` Only Affects Single-Key Chains**: The `keyFolding: 'safe'` option will not apply if any object in the chain has more than one key. For example, our original `data` object would not be folded because the `user` object contains both `id` and `details` at the same level.

- **Invalid Delimiters**: The `delimiter` must be one of the pre-defined `Delimiter` types exported from the library. You cannot use an arbitrary character.

## 6. Challenge Yourself

Modify the original `data` object so that the `details` object is a candidate for key folding. Then, encode it using both `keyFolding: 'safe'` and a `delimiter` of your choice from the `DELIMITERS` constant. Analyze the output to see how both options are applied simultaneously.