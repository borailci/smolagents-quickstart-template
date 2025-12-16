# Benchmarking Suite Knowledge Base

## 1. Overview
The benchmarking suite is designed to evaluate the performance of different language models and data formats, specifically focusing on retrieval accuracy and token efficiency. It provides a structured way to compare various AI models (e.g., Anthropic, Google, OpenAI, XAI) and data serialization formats (e.g., TOON, JSON, YAML, XML, CSV) against a diverse set of synthetic and real-world datasets. The primary goals are to assess how accurately models can extract information from different data formats and how efficiently each format utilizes tokens, especially for the custom TOON format.

## 2. Key Components

### `benchmarks/src/evaluate.ts`
This file contains the core logic for evaluating a single question against a specific language model and data format. It defines the `evaluateQuestion` function, which constructs a prompt based on a `primer` for the data format, the formatted data, and the question itself. It then uses the `@ai-sdk/ai` `generateText` function to get the model's answer and compares it against a `groundTruth` to determine correctness. It also tracks latency and token usage.

### `benchmarks/src/datasets.ts`
This module is responsible for generating and defining various datasets used in the benchmarks. It utilizes `faker.js` to create synthetic data for different structures like tabular employee records, nested e-commerce orders, analytics time-series data, and deeply nested configurations. It also includes real-world data like GitHub repositories. Datasets are categorized into `ACCURACY_DATASETS` (smaller, for faster evaluation) and `TOKEN_EFFICIENCY_DATASETS` (larger, to amplify token differences). Each dataset includes metadata about its structure and CSV support.

### `benchmarks/scripts/accuracy-benchmark.ts`
This script orchestrates the retrieval accuracy benchmark. It prompts the user to select models, generates questions from the defined datasets, and then runs `evaluateQuestion` for each model-question-format combination. It handles rate limiting for model API calls using `p-queue`, saves interim results, and finally compiles a detailed markdown report summarizing the accuracy of each model across different formats and datasets.

### `benchmarks/scripts/token-efficiency-benchmark.ts`
This script focuses on comparing the token efficiency of various data formats. It iterates through the `TOKEN_EFFICIENCY_DATASETS`, formats each dataset into TOON, JSON, YAML, XML, and CSV (where applicable), and then tokenizes the output. It calculates and reports the number of tokens used by each format and the savings or overhead compared to the TOON format. The script generates a markdown report with bar charts and detailed examples to visualize token usage.

## 3. Data Flow & Dependencies

The data flow begins in `datasets.ts` where various data structures are defined and populated (either synthetically or from static JSON files). These datasets are then imported by the benchmark scripts.

For **accuracy benchmarks**, `accuracy-benchmark.ts` generates questions based on these datasets. Each question, along with formatted data (generated on-the-fly using formatters defined elsewhere but utilized by `evaluate.ts`), is passed to the `evaluateQuestion` function in `evaluate.ts`. This function interacts with external AI model providers (Anthropic, Google, OpenAI, XAI) via the `@ai-sdk/provider` and `@ai-sdk/ai` libraries. The results (correctness, tokens, latency) are then collected, stored, and aggregated into a final markdown report.

For **token efficiency benchmarks**, `token-efficiency-benchmark.ts` takes the datasets, formats them using different serialization methods (including `encode` from the `toon` package), and then tokenizes the resulting strings. The token counts are analyzed and presented in a markdown report.

**External Dependencies:**
*   `@ai-sdk/provider`, `@ai-sdk/anthropic`, `@ai-sdk/google`, `@ai-sdk/openai`, `@ai-sdk/xai`: For interacting with various large language models.
*   `@ai-sdk/ai`: For the `generateText` function used in evaluation.
*   `faker-js/faker`: For generating realistic synthetic data for datasets.
*   `PQueue`: For managing concurrency and rate-limiting API calls to models.
*   `@clack/prompts`: For interactive command-line prompts and progress indicators.
*   `node:fs/promises`, `node:path`, `node:process`: Node.js built-in modules for file system operations and process control.

## 4. Code Deep Dive

### Core Evaluation Logic (`evaluate.ts`)
This snippet shows how a prompt is constructed and sent to an AI model for evaluation.

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

\
\
\`\`\`${fence}
${formattedData}
\
\
\`\`\`

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

### Dataset Generation Example (`datasets.ts`)
This function demonstrates how synthetic employee data is generated for a tabular dataset.

```typescript
function generateEmployees(count: number): { employees: Employee[] } {
  return {
    employees: Array.from({ length: count }, (_, i): Employee => {
      const yearsExp = faker.number.int({ min: 1, max: 25 })
      return {
        id: i + 1,
        name: faker.person.fullName(),
        email: faker.internet.email().toLowerCase(),
        department: departments[i % departments.length]!,
        salary: faker.number.int({ min: 45000, max: 150000 }),
        yearsExperience: yearsExp,
        active: faker.datatype.boolean(0.8), // 80% active
      }
    }),
  }
}

const tabularDataset: Dataset = {
  name: 'tabular',
  description: 'Uniform employee records',
  data: generateEmployees(100),
  metadata: {
    supportsCSV: true,
    structureClass: 'uniform',
    tabularEligibility: 100,
  },
}
```

### Running Accuracy Benchmark Tasks (`accuracy-benchmark.ts`)
This excerpt illustrates how evaluation tasks are queued and processed, with progress updates and rate-limiting.

```typescript
  // Queue all tasks
  const modelResultPromises = tasks.map(task =>
    queue.add(async () => {
      // Format data on-demand
      const dataset = ACCURACY_DATASETS.find(d => d.name === task.question.dataset)!
      const formatter = formatters[task.formatName]!
      const formattedData = formatter(dataset.data)

      const result = await evaluateQuestion({
        question: task.question,
        formatName: task.formatName,
        formattedData,
        model,
      })

      // Progress update after task completes
      updateProgress()

      return result
    }),
  )

  // Wait for all tasks to complete
  const modelResults = await Promise.all(modelResultPromises)
```

## 5. Potential Pitfalls

*   **API Rate Limits**: The accuracy benchmark implements `PQueue` for rate-limiting model API calls. Misconfiguration of `MODEL_RPM_LIMITS` or `DEFAULT_CONCURRENCY` could lead to exceeding API limits or inefficient use of available RPMs.
*   **Reproducibility**: While `faker.seed(12345)` is used for synthetic data generation, ensuring full reproducibility across all aspects (e.g., model responses, tokenization) can be challenging due to external API calls and potential non-determinism in model behavior or tokenizers.
*   **Prompt Engineering Sensitivity**: The `evaluateQuestion` function relies heavily on the `primer` and the overall prompt structure. Small changes in the prompt could significantly impact model accuracy results. The current prompts aim for neutrality and explicit instructions, but this remains a sensitive area.
*   **Dataset Representation**: The `tabularEligibility` metadata property and the `supportsCSV` flag are crucial for correctly running benchmarks. Incorrectly classifying a dataset could lead to invalid comparisons (e.g., trying to represent deeply nested data in CSV).
*   **Performance Overhead**: Running benchmarks for numerous models, formats, and questions can be time-consuming, especially with rate limits. The `DRY_RUN` feature helps, but comprehensive runs require significant execution time. The token efficiency benchmark relies on a tokenizer, which needs to be consistent and accurate to ensure meaningful comparisons. The current implementation uses `encode` from the `toon` package, implying a specific tokenizer is in use for TOON, and it needs to be ensured that tokenization for other formats is comparable or representative of how models would process them.
*   **Report Generation**: The report generation logic relies on consistent data structures from the evaluation steps. Any inconsistencies or missing data points could lead to errors or incomplete reports. The reports are generated in Markdown, which is suitable for human readability but might require further parsing for automated analysis.