# Benchmarking Performance

Welcome to this tutorial on using the benchmarking suite to evaluate the performance of language models and data formats. This suite provides a structured approach to assessing how different AI models extract information and how efficiently various data serialization formats (like TOON, JSON, YAML, XML, and CSV) utilize tokens.

Our focus will be on two key aspects: **retrieval accuracy** for language models and **token efficiency** for data formats. Understanding these metrics is crucial for optimizing your applications for both performance and cost, especially when working with large language models.

## 1. Retrieval Accuracy Benchmarks

The retrieval accuracy benchmark evaluates how accurately language models can extract specific information from data presented in different formats. It helps us understand which models perform best with various data structures and serialization methods.

### 1.1 How it Works

At its core, the accuracy benchmark involves:

1.  **Dataset Generation**: Synthetic and real-world datasets are generated with known `groundTruth` answers for specific questions.
2.  **Prompt Construction**: For each question, data is formatted into a target format (e.g., TOON, JSON) and combined with the question and a `primer` (context for the model) to form a prompt.
3.  **Model Query**: The constructed prompt is sent to a language model (e.g., Anthropic, Google, OpenAI).
4.  **Answer Comparison**: The model's response is compared against the `groundTruth` to determine if it's correct. Latency and token usage are also tracked.

This process is orchestrated by `benchmarks/scripts/accuracy-benchmark.ts`, which uses the core logic defined in `benchmarks/src/evaluate.ts`.

### 1.2 Core Evaluation Logic

The `evaluateQuestion` function is central to this process. It takes a question, the formatted data, the data format name, and the language model, then constructs a prompt and calls the `generateText` function from `@ai-sdk/ai`.

```typescript
export async function evaluateQuestion(
  {
    question,
    formatName,
    formattedData,
    model,
  }:
  {
    question: Question
    formatName: string
    formattedData: string
    model: LanguageModelV2
  },
): Promise<EvaluationResult> {
  const primer = PRIMERS[formatName] ?? ''
  const fence = FENCE[formatName] ?? ''

  const prompt = `
${primer}

Given the following data in ${formatName} format:


'''${fence}
${formattedData}


'''

Question: ${question.prompt}

Answer format requirements:
- Provide only the value itself, no explanation
- For numbers: output digits only (no commas, currency symbols, or units)
- For dates/field names: use the exact string from the data
- For lists: output comma-separated values with no spaces

Answer:
`.trim()

  const startTime = performance.now()
  const { text, usage } = await generateText({ model, prompt })

  const actual = text.trim()
  const latencyMs = performance.now() - startTime

  const comparisonResult = compareAnswers(
    actual,
    question.groundTruth,
    question.answerType ?? 'string',
    question.normalizationOptions,
  )
  const isCorrect = comparisonResult.match

  return {
    questionId: question.id,
    format: formatName,
    model: model.modelId,
    expected: question.groundTruth,
    actual,
    isCorrect,
    inputTokens: usage.inputTokens,
    outputTokens: usage.outputTokens,
    latencyMs,
  }
}
```

### 1.3 Accuracy Benchmark Flow

Here's a visual representation of the accuracy benchmarking process:

```mermaid
graph TD
    A[Start]
    B{Select Models & Datasets}
    C[Generate Question & Ground Truth]
    D[Format Data (e.g., TOON, JSON)]
    E[Construct Prompt]
    F[Call LLM (generateText)]
    G[Get LLM Response]
    H{Compare Response to Ground Truth}
    I{Is Correct?}
    J[Record Results (Accuracy, Tokens, Latency)]
    K{More Questions?}
    L[Aggregate Results & Generate Report]
    M[End]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H -- Yes --> J
    H -- No --> J
    J --> K
    K -- Yes --> C
    K -- No --> L
    L --> M
```

## 2. Token Efficiency Benchmarks

The token efficiency benchmark focuses on comparing the token consumption of different data serialization formats when representing the same data. This is critical for managing costs and improving performance with token-gated language models.

### 2.1 How it Works

This benchmark involves:

1.  **Dataset Preparation**: Datasets are used as the source for the benchmark.
2.  **Data Formatting**: Each dataset is formatted into various serialization methods (TOON, JSON, YAML, XML, CSV).
3.  **Tokenization**: The formatted data (as strings) is then tokenized using a consistent tokenizer. The `encode` function from the `toon` package is used for TOON, and a generic `tokenize` utility handles others.
4.  **Comparison**: The token counts for each format are compared, typically against TOON, to calculate savings or overhead.

The `benchmarks/scripts/token-efficiency-benchmark.ts` script automates this process and generates a report.

### 2.2 Token Calculation Example

This snippet from `token-efficiency-benchmark.ts` shows how data is formatted and then tokenized to get the token count:

```typescript
  // Calculate tokens for each format
  for (const [formatName, formatter] of Object.entries(formatters)) {
    // Skip CSV for datasets that don't support it
    if (formatName === 'csv' && !supportsCSV(dataset))
      continue

    const formattedData = formatter(dataset.data)
    const tokens = tokenize(formattedData)
    tokensByFormat[formatName] = tokens
  }

  // Calculate savings vs TOON
  const toonTokens = tokensByFormat.toon!
  for (const [formatName, tokens] of Object.entries(tokensByFormat)) {
    const savings = tokens - toonTokens
    formatMetrics.push({
      name: formatName,
      tokens,
      savings,
      savingsPercent: formatName === 'toon' ? 0 : (savings / tokens) * 100,
    })
  }
```

### 2.3 Token Efficiency Benchmark Flow

Here's a visual overview of how the token efficiency benchmark operates:

```mermaid
graph TD
    A[Start]
    B{Select Datasets}
    C[Get Raw Data (JSON)]
    D{For Each Format (TOON, JSON, YAML, XML, CSV)}
    E[Format Data String]
    F[Tokenize Formatted Data]
    G[Record Token Count]
    H{All Formats Processed?}
    I[Compare Token Counts vs. TOON]
    J[Calculate Savings/Overhead]
    K{All Datasets Processed?}
    L[Aggregate Results & Generate Report]
    M[End]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H -- Yes --> I
    H -- No --> D
    I --> J
    J --> K
    K -- Yes --> L
    K -- No --> C
    L --> M
```

## 3. Running Benchmarks

While the exact execution commands depend on your setup, typically, you would run the TypeScript scripts directly using Node.js after building the project:

```bash
# Example for accuracy benchmark
npm run accuracy-benchmark

# Example for token efficiency benchmark
npm run token-efficiency-benchmark
```

These scripts will guide you through selecting models or datasets and then output detailed markdown reports in the `benchmarks/results` directory.

## Conclusion

The benchmarking suite is an invaluable tool for understanding and optimizing the performance of language models and data formats. By leveraging both retrieval accuracy and token efficiency benchmarks, developers can make informed decisions to build more effective and cost-efficient AI-powered applications. Experiment with different models and formats to discover the optimal configurations for your specific use cases.))
