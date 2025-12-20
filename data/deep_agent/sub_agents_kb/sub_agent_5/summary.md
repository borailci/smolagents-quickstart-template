
# Technical Analysis of AgentLightning Adapters and Emitters

## 1. Overview

This document provides a deep technical analysis of the `agentlightning.adapter` and `agentlightning.emitter` modules. The core purpose of these modules is to process and transform telemetry data, specifically OpenTelemetry traces, into formats suitable for downstream machine learning tasks, such as fine-tuning and reinforcement learning. 

- The **Adapters** (`adapter/`) are responsible for converting sequences of trace spans into structured data formats. Key formats include OpenAI-compatible conversation messages for fine-tuning and (State, Action, Reward) triplets for reinforcement learning.
- The **Emitters** (`emitter/`) provide a high-level API for developers to inject custom telemetry (messages and rewards) into the OpenTelemetry trace stream, which the adapters can then process.

## 2. File-by-File Analysis

### `agentlightning/adapter/base.py`

- **Purpose**: Defines the fundamental abstractions for all adapter components.
- **Key Components**:
  - `Adapter[T_from, T_to]`: A generic, callable base class for any synchronous data transformation. It standardizes the adapter pattern by requiring subclasses to implement a core `adapt` method.
  - `OtelTraceAdapter[T_to]`: A specialized adapter that operates on raw `opentelemetry.sdk.trace.ReadableSpan` objects.
  - `TraceAdapter[T_to]`: A specialization that works with the library's internal `agentlightning.types.Span` data type. This is the primary base class for most application-specific adapters in the module.

### `agentlightning/adapter/messages.py`

- **Purpose**: To convert a flat list of trace spans into structured, OpenAI-compatible chat conversation histories, suitable for creating fine-tuning datasets.
- **Key Components**:
  - `TraceToMessages(TraceAdapter[List[OpenAIMessages]])`: The main adapter. Its `adapt` method orchestrates the conversion by parsing `gen_ai.*` attributes from spans to reconstruct the entire conversation, including user prompts, assistant responses, and tool calls.
  - `group_genai_dict(...)`: A crucial utility function that transforms flattened, dot-notated span attributes (e.g., `gen_ai.prompt.0.role`) back into the nested dictionary and list structures that represent the original API payloads.
  - `convert_to_openai_messages(...)`: Consumes the raw data structures reconstructed by `group_genai_dict` and formats them into `OpenAIMessages` objects, which are TypedDicts that strictly conform to the OpenAI `ChatCompletionMessageParam` schema.

### `agentlightning/adapter/triplet.py`

- **Purpose**: To convert full traces into reinforcement learning trajectories, represented as a sequence of `Triplet` objects (prompt, response, reward).
- **Key Components**:
  - `TraceTree`: A powerful class that reconstructs the hierarchical tree structure of a trace from a flat list of spans. It is central to the entire process and is responsible for:
    - Re-parenting "orphan" spans to repair broken hierarchies caused by mixed tracing systems (`repair_hierarchy`).
    - Traversing the tree to find specific LLM call spans based on regex matching (`find_llm_calls`).
    - Associating reward spans with their corresponding LLM calls using configurable strategies (`match_rewards`).
  - `TracerTraceToTriplet(TraceToTripletBase)`: The primary adapter that utilizes a `TraceTree` instance to perform the conversion. It manages the entire pipeline: building the tree, repairing it, finding LLM calls, matching rewards, and finally converting each relevant span into a `Triplet`.
  - `LlmProxyTraceToTriplet(TraceToTripletBase)`: An experimental adapter designed for telemetry from an LLM proxy, where clock synchronization is not guaranteed. It relies on `sequence_id` for ordering instead of timestamps.

### `agentlightning/emitter/message.py`

- **Purpose**: Provides a simple API to emit textual messages as spans within the active trace.
- **Key Components**:
  - `emit_message(message: str, ...)`: The main public function. It creates a new OpenTelemetry span with a standardized name (`AGL_MESSAGE`) and attaches the message content to a specific attribute (`lightning.span.message.body`). This allows developers to inject logs or debug information directly into the trace stream for later analysis.

### `agentlightning/emitter/reward.py`

- **Purpose**: Provides a standardized way to emit scalar or multi-dimensional rewards as spans, making them discoverable by the `TraceToTriplet` adapter.
- **Key Components**:
  - `emit_reward(reward: float | Dict[str, Any], ...)`: The core function for emitting rewards. It creates a span (`AGL_ANNOTATION`) and records the reward value(s) in a structured format under the `lightning.span.reward` attribute. It supports single float values and dictionaries for multi-dimensional rewards.
  - `get_reward_value(span: SpanLike)`: A utility to extract the primary reward value from a span. It knows how to parse rewards emitted by `emit_reward` as well as legacy formats from AgentOps, ensuring backward compatibility.
  - `get_rewards_from_span(span: SpanLike)`: Extracts all reward dimensions from a span as a list of `RewardPydanticModel` objects.

## 3. Architecture & Data Flow

1.  **Instrumentation**: The application code, instrumented with AgentLightning or a compatible OpenTelemetry tracer, runs. During execution, it generates spans for LLM calls, tool calls, etc.
2.  **Emission**: The developer can use `emit_reward()` or `emit_message()` to inject custom, domain-specific information (like the result of an evaluation or a debug note) into the trace as distinct spans.
3.  **Collection**: A trace processor or collector gathers all the spans belonging to a single trace.
4.  **Adaptation**: This collection of spans is passed to an adapter.
    - If `TraceToMessages` is used, the spans are processed to reconstruct a chronological chat history, suitable for a JSONL fine-tuning file.
    - If `TracerTraceToTriplet` is used, the spans are first assembled into a `TraceTree`. The tree is analyzed to identify agent-specific LLM calls and to associate them with later reward spans. The final output is a list of `Triplet` objects.
5.  **Downstream Consumption**: The structured data from the adapters is used to train ML models (e.g., via RL or SFT). 

## 4. Code Deep Dive

### `TraceTree.repair_hierarchy()`

This method is critical for handling traces from complex agent frameworks where different components might use different tracing contexts. This can result in LLM call spans appearing at the root of the trace instead of being nested under the agent span that initiated them. The repair logic finds the correct parent for these detached spans by identifying an ancestor span that temporally envelops it (the child span's start and end times are within the parent's). This ensures that agent-based filtering and reward matching works correctly.

```python
def repair_hierarchy(self) -> None:
    """Repair missing parent-child relationships introduced by mixed tracing systems."""
    nodes_to_repair = list(self.children)

    for repair_node in nodes_to_repair:
        # Find the closest parent span (but not the root itself)
        closest_parent = None
        closest_duration = float("inf")
        for node in self.traverse():
            if node.id == repair_node.id or node is self:
                continue
            # Check if the node envelops the repair_node in time
            if node.start_time <= repair_node.start_time and node.end_time >= repair_node.end_time:
                duration_delta = (node.end_time - repair_node.end_time) + (repair_node.start_time - node.start_time)
                if duration_delta > 0 and duration_delta < closest_duration:
                    closest_duration = duration_delta
                    closest_parent = node

        # Re-parent the node
        if closest_parent is not None:
            self.children.remove(repair_node)
            closest_parent.children.append(repair_node)
```

### `TracerTraceToTriplet.adapt()`

The `adapt` method in this class shows the end-to-end orchestration of converting spans to a trajectory. It highlights the modular steps of the process: creating the tree, optionally repairing it, and then invoking the trajectory extraction logic.

```python
def adapt(self, source: Union[Sequence[Span], Sequence[ReadableSpan]], /) -> List[Triplet]:
    """Convert tracer spans into Triplet trajectories."""
    source_normalized = [
        Span.from_opentelemetry(span, "dummy", "dummy", 0) if isinstance(span, ReadableSpan) else span
        for span in source
    ]
    trace_tree = TraceTree.from_spans(source_normalized)
    if self.repair_hierarchy:
        trace_tree.repair_hierarchy()
    trajectory = trace_tree.to_trajectory(
        llm_call_match=self.llm_call_match,
        agent_match=self.agent_match,
        exclude_llm_call_in_reward=self.exclude_llm_call_in_reward,
        reward_match=self.reward_match,
        _skip_empty_token_spans=self._skip_empty_token_spans,
    )
    return trajectory
```

## 5. Integration Points & API Reference

- **Dependencies**: These modules rely heavily on `opentelemetry-sdk`, `pydantic`, and the internal `agentlightning.types` module.
- **Dependents**: Any system performing offline training (SFT, DPO, PPO) on data captured from AgentLightning-instrumented applications would be a consumer of these adapters.

### Public Interface

- **Emitters**
  - `emit_reward(reward: float | Dict[str, Any], ...)`: Primary entry point for injecting reward data.
  - `emit_message(message: str, ...)`: Entry point for injecting log-style messages.
- **Adapters**
  - `TracerTraceToTriplet(...)`: Instantiated to convert traces to RL trajectories.
  - `TraceToMessages()`: Instantiated to convert traces to conversation histories.

### API Reference Table

| Class / Function              | Signature                                                                                                | Purpose                                                                          |
|-------------------------------|----------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| `Adapter`                     | `adapt(self, source: T_from) -> T_to`                                                                    | Abstract method for data conversion.                                             |
| `TracerTraceToTriplet`        | `__init__(self, repair_hierarchy: bool = True, llm_call_match: str, ...)`                                | Configures and creates an adapter for converting traces to triplets.             |
| `TraceToMessages`             | `adapt(self, source: Sequence[Span]) -> List[OpenAIMessages]`                                            | Converts a sequence of spans into OpenAI-compatible message lists.               |
| `emit_reward`                 | `(reward: float | Dict, *, primary_key: str | None, ...)`                                              | Emits a reward value as a distinct span in the current trace.                    |
| `emit_message`                | `(message: str, attributes: Dict | None, ...)`                                                             | Emits a textual message as a span.                                               |

