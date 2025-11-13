# Flow and Node Design Pattern

This document captures the Flow/Node orchestration pattern so we can reference it whenever we implement new pipelines.

## Core Concepts

- **Flow** orchestrates a graph of **Node** instances. Nodes can run sequentially or branch based on the `Action` string returned by `Node.post()`.
- If `post()` returns `None`, treat it as the action string `"default"`.
- Define transitions with the `node_a >> node_b` syntax:
  - `node_a >> node_b` is shorthand for `node_a - "default" >> node_b`.
  - `node_a - "action" >> node_b` routes to `node_b` only when `node_a.post()` returns `"action"`.
- Loops, branching, and multi-step flows are all possible via action-based transitions.

### Creating and Running a Flow

```python
flow = Flow(start=first_node)
flow.run(shared_state)
```

- `flow.run(shared)` executes the start node, reads its returned action, and follows the matching transition until it finds no next node.
- `node.run(shared)` runs only that node (useful for debugging). It does **not** proceed to successor nodes.
- Always prefer `flow.run(...)` in production so the full pipeline runs.

### Example: Branching and Looping

```python
review - "approved" >> payment
review - "needs_revision" >> revise
review - "rejected" >> finish

revise >> review
payment >> finish

flow = Flow(start=review)
```

- Actions like `"approved"`, `"needs_revision"`, or `"rejected"` determine the next node.
- Loops are achieved by pointing transitions back to earlier nodes.

## Nested Flows

- A `Flow` is also a `Node`, so you can embed flows inside other flows.
- Nested flows inherit parameters (merged from parent to child) and share the common `prep()`/`post()` lifecycle.
- `Flow` does **not** run `exec()`; it only orchestrates.

Example:

```python
node_a >> node_b
subflow = Flow(start=node_a)

subflow >> node_c
parent_flow = Flow(start=subflow)
```

Running `parent_flow.run(shared)` executes `node_a`, `node_b`, and then `node_c`.

## Node Lifecycle

Each `Node` has up to three steps, executed in order:

1. `prep(shared)`

   - Read and preprocess data from the shared store (global context).
   - Return `prep_res` for use in `exec()` and `post()`.

2. `exec(prep_res)`

   - Perform compute logic (LLM calls, API requests, long-running work).
   - Must **not** access shared state directly.
   - Supports retries via `max_retries` and `wait` parameters.

3. `post(shared, prep_res, exec_res)`
   - Postprocess results and write back to shared state.
   - Return an action string (`"default"` if `None`).

All steps are optional; implement only what the node needs.

### Retries and Fallbacks

- Configure retries with `Node(max_retries=3, wait=10)`.
- Access the current retry index via `self.cur_retry`.
- Override `exec_fallback(self, prep_res, exc)` to return a graceful fallback result instead of raising.

## Shared Store vs. Params

- **Shared store**: typically a dict shared across nodes (`shared = {"data": {}, "summary": {}}`). Use it for most data exchange.
- **Params**: per-node immutable dict set via `set_params()`. Useful for identifiers in batch operations. Parent flows overwrite child params.

Example of params usage:

```python
node = SummarizeFile()
node.set_params({"filename": "doc1.txt"})
node.run(shared)

flow = Flow(start=node)
flow.set_params({"filename": "doc2.txt"})
flow.run(shared)
```

## Batch Variants

### BatchNode

- `prep(shared)` returns an iterable of items.
- `exec(item)` runs once per item.
- `post(shared, prep_res, exec_res_list)` receives a list of results after all iterations.

```python
class MapSummaries(BatchNode):
    def prep(self, shared):
        return chunk_document(shared["data"], size=10_000)

    def exec(self, chunk):
        return call_llm(f"Summarize in 10 words: {chunk}")

    def post(self, shared, prep_res, exec_res_list):
        shared["summary"] = "\n".join(exec_res_list)
```

### BatchFlow

- Re-runs an entire flow with different param dicts.
- `prep(shared)` returns a list of param dictionaries (e.g., `[{"filename": "file1"}, ...]`).
- Child nodes access the merged params via `self.params`.

Nested batch flows merge params from outer to inner levels, enabling directory/file processing hierarchies.

## Async Variants

- Implement `AsyncNode` with `prep_async`, `exec_async`, and `post_async` (plus optional async fallback).
- Wrap async nodes inside `AsyncFlow`.
- Useful for async I/O, LLM calls, or awaiting user feedback.

```python
class SummarizeThenVerify(AsyncNode):
    async def prep_async(self, shared):
        return await read_file_async(shared["doc_path"])

    async def exec_async(self, prep_res):
        return await call_llm_async(f"Summarize: {prep_res}")

    async def post_async(self, shared, prep_res, exec_res):
        decision = await gather_feedback(exec_res)
        if decision == "approve":
            shared["summary"] = exec_res
            return "approve"
        return "deny"

summarize = SummarizeThenVerify()
finalize = Finalize()

summarize - "approve" >> finalize
summarize - "deny" >> summarize

flow = AsyncFlow(start=summarize)
await flow.run_async(shared)
```

## Shared Store Tips

- Decide on the shared data schema before wiring flows.
- Use shared state for data, logs, and coordination.
- Reserve params for lightweight identifiers or batch coordination.

## Quick Reference

- `flow = Flow(start=node)`
- `node_a >> node_b` equals default transition.
- `node_a - "custom" >> node_b` for named actions.
- `flow.run(shared)` drives the full pipeline.
- Nodes: `prep()` -> `exec()` -> `post()`.
- Configure retries with `max_retries` and `wait`.
- Shared store for data; params for identifiers.
- BatchNode/BatchFlow handle repeated work; AsyncFlow enables async orchestration.

Keep this guide handy when implementing Flow-driven orchestration so our agents stay consistent and maintainable.
