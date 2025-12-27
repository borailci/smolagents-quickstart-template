
# Working with Tabular Arrays

## 1. Goal

This tutorial explains how to leverage one of TOON's most powerful features for data compaction: **Tabular Arrays**. You will learn how the TOON encoder automatically detects and serializes arrays of similar objects into a highly efficient, table-like structure.

## 2. Prerequisites

- You should have the `@toon-format/toon` package installed.
- A basic understanding of the TOON encoding process.

## 3. Architecture: The Tabular Decision

The TOON encoder follows a specific logic path when it encounters an array. It inspects the array's contents to decide on the most efficient encoding strategy. The decision to create a tabular array is a key optimization.

```mermaid
graph TD
    A["Input: An Array"] --> B{Is it an array of objects?};
    B -->|Yes| C{Do all objects have the exact same keys?};
    B -->|No| F["Encode as a standard list (using '-')"];

    C -->|Yes| D{Are all values in all objects primitives? (string, number, bool, null)};
    C -->|No| F;

    D -->|Yes| E["Encode as a Compact Tabular Array"];
    D -->|No| F;
```

## 4. Implementation Steps

The beauty of tabular arrays is that they are created **automatically** by the encoder when the data structure is right. You don't need to call a special function; you just need to format your data correctly.

### Step 1: The Perfect Case for a Table

Let's start with a standard JavaScript array of objects where each object has the same shape. This is the ideal input for generating a tabular array.

**Input Data (JavaScript)**
```javascript
import { encode } from '@toon-format/toon';

const products = [
  { id: 101, name: "Fusion Reactor", status: "active" },
  { id: 102, name: "Warp Drive", status: "inactive" },
  { id: 103, name: "Plasma Injector", status: "active" },
];

const toonOutput = encode(products);
console.log(toonOutput);
```

***Verification***:

When you run this code, the TOON encoder inspects the `products` array. It sees:
1.  It's an array of objects.
2.  All three objects have the *exact* same keys: `id`, `name`, and `status`.
3.  All values associated with these keys are primitives (numbers and strings).

Therefore, it produces the following highly compact TOON output.

**TOON Output**
```toon
[3]{id,name,status}:
  101,"Fusion Reactor","active"
  102,"Warp Drive","inactive"
  103,"Plasma Injector","active"
```
Notice the header `[3]{id,name,status}:`. This defines the "columns" of the table. Each subsequent line is a "row," containing only the values in the same order.

### Step 2: When Data is Not Tabular

Now, let's look at an array that *looks* similar but has inconsistencies that prevent it from being encoded as a table.

**Input Data (JavaScript)**
```javascript
import { encode } from '@toon-format/toon';

const devices = [
  { id: 201, name: "Sensor A" },
  { id: 202, name: "Actuator B", connected: true }, // Extra key
  { id: 203, details: { firmware: "v1.2" } }, // 'name' is missing, and has a nested object
];

const toonOutput = encode(devices);
console.log(toonOutput);

```

***Verification***:

The encoder analyzes this array and finds several disqualifying factors:
1.  The second object has a `connected` key that the first doesn't.
2.  The third object is missing the `name` key.
3.  The third object contains a value that is a nested object (`details`), not a primitive.

Because the objects are not uniform, the encoder falls back to the standard list format.

**TOON Output**
```toon
[3]:
- id: 201
  name: "Sensor A"
- id: 202
  name: "Actuator B"
  connected: true
- id: 203
  details:
    firmware: "v1.2"
```
This output is still perfectly valid and readable, but it is not as compact as the tabular format.

## 5. Common Pitfalls

- **Inconsistent Keys**: The most common reason for failed tabular encoding. Even a single object with an extra or missing key will cause the encoder to fall back to the list format. Keys are case-sensitive.
- **Non-Primitive Values**: If any object in the array has a value that is another object or an array, the entire array cannot be encoded as a table.
- **Empty Arrays**: An empty array `[]` is simply encoded as `[0]:`, as there is no header information to extract.

## 6. Challenge Yourself

Take the `devices` array from Step 2. Your task is to refactor it into two separate arrays that can **both** be encoded as tabular arrays. Create a new root object to hold these two new arrays.

- One array should contain the devices with `id` and `name`.
- The other array should contain devices with `id` and a `firmware` version.

Encode the final object and observe how the TOON output now contains two distinct, compact tables.
