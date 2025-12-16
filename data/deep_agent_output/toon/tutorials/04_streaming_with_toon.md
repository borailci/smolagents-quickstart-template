# Streaming with the `toon` Library

The `toon` library is designed not only for convenient encoding and decoding of TOON data but also for efficiently handling large datasets through its streaming capabilities. This tutorial will guide you through using `toon`'s streaming APIs for both encoding and decoding, including asynchronous examples.

Streaming is crucial when dealing with datasets that are too large to fit into memory, or when you need to process data as it arrives without waiting for the entire input to be available. The `toon` library provides functions that allow you to process TOON data line by line or event by event, making it highly suitable for such scenarios.

## 1. Streaming Encoding: `encodeLines`

The `encodeLines` function allows you to encode a JavaScript value into TOON format as an iterable sequence of lines. Instead of returning a single large string, it yields TOON lines one at a time. This is particularly useful when writing large TOON outputs directly to a file, an HTTP response, or `stdout` without buffering the entire content in memory.

### How it Works

`encodeLines` takes a JavaScript object or array and returns an `Iterable<string>`. You can then iterate over this iterable to get each line of the TOON output.

```python
import { encodeLines } from '@your-org/toon';

const largeData = {
  users: Array.from({ length: 1000 }, (_, i) => ({
    id: i + 1,
    name: `User ${i + 1}`,
    email: `user${i + 1}@example.com`,
    settings: {
      notifications: true,
      theme: 'dark',
    },
  })),
  metadata: {
    timestamp: new Date().toISOString(),
    version: '1.0',
  },
};

console.log('--- Streaming Encoding Output ---');
for (const line of encodeLines(largeData, { indent: 2, keyFolding: 'safe' })) {
  console.log(line);
}
console.log('---------------------------------');

// Example of collecting lines into an array (for demonstration, generally avoid for truly large data)
const linesArray = Array.from(encodeLines({
  product: {
    id: 123,
    name: 'Example Product',
    price: 99.99
  }
}));
console.log('Collected Lines:', linesArray.join('\n'));
```

In this example, `encodeLines` processes `largeData` and generates each TOON line on demand. This approach conserves memory compared to generating the entire TOON string at once.

## 2. Streaming Decoding: `decodeStreamSync` and `decodeStream`

For decoding, `toon` provides both synchronous (`decodeStreamSync`) and asynchronous (`decodeStream`) streaming functions. These functions yield `JsonStreamEvent` objects, representing the parsed JSON data model without building the full JavaScript value tree in memory.

### Understanding `JsonStreamEvent`s

When you stream decode, you don't get the final JavaScript object directly. Instead, you receive a sequence of events. These events describe the structure and content of the TOON data as it's parsed. Common event types include:

*   `{ type: 'startObject' }`: Marks the beginning of an object.
*   `{ type: 'endObject' }`: Marks the end of an object.
*   `{ type: 'key', key: 'someKey' }`: Indicates an object key.
*   `{ type: 'startArray' }`: Marks the beginning of an array.
*   `{ type: 'endArray' }`: Marks the end of an array.
*   `{ type: 'primitive', value: someValue }`: Represents a primitive value (string, number, boolean, null).

### 2.1 Synchronous Streaming Decoding: `decodeStreamSync`

`decodeStreamSync` is suitable when your TOON input is already available as an `Iterable<string>` (e.g., an array of lines or a synchronous file reader).

```python
import { decodeStreamSync } from '@your-org/toon';

const toonInputLines = [
  'product:',
  '  id: 456',
  '  name: \'Another Product\'',
  '  details:',
  '    category: Electronics',
  '    weight: 1.5kg',
  'users[2]{id,name}:',
  '  1,Alice',
  '  2,Bob',
];

console.log('--- Synchronous Streaming Decoding Output ---');
for (const event of decodeStreamSync(toonInputLines, { strict: true })) {
  console.log(event);
}
console.log('---------------------------------------------');
```

In this example, `decodeStreamSync` processes `toonInputLines` and yields each `JsonStreamEvent` synchronously. This allows for custom processing logic to be applied as the data stream is parsed.

### 2.2 Asynchronous Streaming Decoding: `decodeStream`

`decodeStream` is the most powerful streaming decoding function, designed for scenarios where your TOON input comes from an asynchronous source, such as a network stream, an asynchronous file reader, or `stdin`.

This function accepts an `AsyncIterable<string>` or `Iterable<string>` and returns an `AsyncIterable<JsonStreamEvent>`.

```python
import { decodeStream } from '@your-org/toon';

// Simulate an async source of TOON lines
async function* getAsyncToonLines(): AsyncIterable<string> {
  yield 'config:';
  await new Promise(resolve => setTimeout(resolve, 50)); // Simulate async delay
  yield '  appName: MyApp';
  await new Promise(resolve => setTimeout(resolve, 50));
  yield '  version: 2.0';
  await new Promise(resolve => setTimeout(resolve, 50));
  yield 'features[]:';
  await new Promise(resolve => setTimeout(resolve, 50));
  yield '  - dark_mode: true';
  await new Promise(resolve => setTimeout(resolve, 50));
  yield '  - notifications: false';
}

async function processAsyncToonStream() {
  console.log('--- Asynchronous Streaming Decoding Output ---');
  for await (const event of decodeStream(getAsyncToonLines(), { strict: true })) {
    console.log(event);
  }
  console.log('----------------------------------------------');
}

processAsyncToonStream();
```

Here, `getAsyncToonLines` simulates an asynchronous data source. `decodeStream` processes these lines as they become available, yielding `JsonStreamEvent`s. This is ideal for high-performance applications that need to handle streaming data without blocking the event loop.

### Streaming Decoding Flow

The process of streaming decoding can be visualized as follows:

```mermaid
graph TD
    A[TOON Lines (Sync/Async Iterable)] -->|Input| B(decodeStreamSync / decodeStream)
    B -->|Parse Line| C{Streaming Line Cursor}
    C -->|Yield Event| D[JsonStreamEvent Stream]
    D --> E[Custom Processing Logic]

    subgraph B_details [Internal Decoding Process]
        B_details_1[Scan Lines] --> B_details_2[Parse Tokens]
        B_details_2 --> B_details_3[Manage State & Emit Events]
    end
```

This diagram illustrates how raw TOON lines are fed into the streaming decoder, processed by the internal parser and state manager, and then emitted as `JsonStreamEvent`s for consumption by your application logic.

## Conclusion

The streaming capabilities of the `toon` library, particularly `encodeLines`, `decodeStreamSync`, and `decodeStream`, provide powerful tools for handling large and continuous datasets. By processing data line by line or event by event, you can build more memory-efficient and responsive applications, especially in environments where data arrives asynchronously. Remember that when using streaming decode, you'll be working with `JsonStreamEvent`s, allowing you to implement custom logic to reconstruct or transform the data as needed.