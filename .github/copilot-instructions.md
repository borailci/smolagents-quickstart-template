# Smolagents Quickstart Template - AI Agent Guidelines

## Overview

This is a template for building AI agents using the Smolagents framework. It provides modular components for agents, toolkits, UI, and tracing, focused on tool-calling agents with filesystem and web API capabilities.

## Architecture

- **Agents**: Modular agents inheriting from `BaseAgent`, using Smolagents' `ToolCallingAgent` or manager agents for orchestration.
- **Toolkits**: Collections of tools wrapped as `@tool` decorated functions, e.g., filesystem operations via Langchain, web APIs.
- **UI**: Gradio-based chat interface for agent interaction.
- **Tracing**: OpenTelemetry integration with Phoenix for observability.
- **Data Flow**: Agents receive user input via UI, execute tools on workspace (`data/agent_workspace`), return responses.

## Key Components

- `agents/`: Agent classes like `ExampleToolCallingAgent` (uses `LiteLLMModel` with env vars `LITELLM_MODEL_ID` and `LITELLM_API_KEY`).
- `toolkits/`: Tool collections, e.g., `FileSystemToolkit.get_tools()` returns [read_file, write_file, file_search, list_workspace_dir, get_tree].
- `ui/`: `GradioAgentUI` launches chat interface on localhost with sharing enabled.
- `prompts/prompts.py`: Agent instructions, e.g., `EXAMPLE_TOOL_CALLING_AGENT` for tool usage guidance.
- `data/agent_workspace/`: Sandbox for agent file operations, with example files like `car.c` and `alan_turing.md`.

## Developer Workflows

- **Setup**: `uv sync` to install deps, `cp env.example .env`, configure API keys per `docs/api_key.md`.
- **Run**: `./run.sh` (sources `.env`, runs `uv run main.py`) or `uv run main.py` directly.
- **Debug**: Check logs via Loguru, trace via Phoenix UI (launched automatically).
- **Multi-Agent**: Uncomment manager agent in `main.py` for orchestration.

## Conventions

- Agents: Subclass `BaseAgent`, set `self.agent` to Smolagents agent instance, implement `run()` method.
- Tools: Define as `@tool` functions with docstrings, collect in toolkit classes with `get_tools()` static method.
- Env Vars: Use `AGENT_WORKSPACE_PATH` for workspace root (defaults to `data/agent_workspace`).
- Imports: Load dotenv in entry points, use Loguru for logging.
- File Paths: Relative to workspace root for agent operations, enforce sandboxing in custom tools like `get_tree`.

## Examples

- **Agent Creation**: `tool_calling_agent = ExampleToolCallingAgent(tools=joke_tools + filesystem_tools)`
- **Tool Usage**: `@tool def read_file(file_path: str) -> List[str]: return read_file_tool.invoke(...)`
- **UI Launch**: `ui = GradioAgentUI(agent=tool_calling_agent); ui.launch()`
- **Tracing**: Register Phoenix and instrument Smolagents in `main.py` before agent init.</content>
  <parameter name="filePath">/home/amirkia/Desktop/smolagents-quickstart-template/.github/copilot-instructions.md

Right now I am providing you a design pattern and I want you to read this and save this instructions to somewhere else in our codebase so you can turn back every time you try to implement the design pattern.

Flow
A Flow orchestrates a graph of Nodes. You can chain Nodes in a sequence or create branching depending on the Actions returned from each Node’s post().

1. Action-based Transitions
   Each Node’s post() returns an Action string. By default, if post() doesn’t return anything, we treat that as "default".

You define transitions with the syntax:

Basic default transition: node_a >> node_b This means if node_a.post() returns "default", go to node_b. (Equivalent to node_a - "default" >> node_b)

Named action transition: node_a - "action_name" >> node_b This means if node_a.post() returns "action_name", go to node_b.

It’s possible to create loops, branching, or multi-step flows.

2. Creating a Flow
   A Flow begins with a start node. You call Flow(start=some_node) to specify the entry point. When you call flow.run(shared), it executes the start node, looks at its returned Action from post(), follows the transition, and continues until there’s no next node.

Example: Simple Sequence
Here’s a minimal flow of two nodes in a chain:

node_a >> node_b
flow = Flow(start=node_a)
flow.run(shared)

When you run the flow, it executes node_a.
Suppose node_a.post() returns "default".
The flow then sees "default" Action is linked to node_b and runs node_b.
node_b.post() returns "default" but we didn’t define node_b >> something_else. So the flow ends there.
Example: Branching & Looping
Here’s a simple expense approval flow that demonstrates branching and looping. The ReviewExpense node can return three possible Actions:

"approved": expense is approved, move to payment processing
"needs_revision": expense needs changes, send back for revision
"rejected": expense is denied, finish the process
We can wire them like this:

# Define the flow connections

review - "approved" >> payment # If approved, process payment
review - "needs_revision" >> revise # If needs changes, go to revision
review - "rejected" >> finish # If rejected, finish the process

revise >> review # After revision, go back for another review
payment >> finish # After payment, finish the process

flow = Flow(start=review)

Let’s see how it flows:

If review.post() returns "approved", the expense moves to the payment node
If review.post() returns "needs_revision", it goes to the revise node, which then loops back to review
If review.post() returns "rejected", it moves to the finish node and stops
approved
needs_revision
rejected
Review Expense
Process Payment
Revise Report
Finish Process
Running Individual Nodes vs. Running a Flow
node.run(shared): Just runs that node alone (calls prep->exec->post()), returns an Action.
flow.run(shared): Executes from the start node, follows Actions to the next node, and so on until the flow can’t continue.
node.run(shared) does not proceed to the successor. This is mainly for debugging or testing a single node.

Always use flow.run(...) in production to ensure the full pipeline runs correctly.

3. Nested Flows
   A Flow can act like a Node, which enables powerful composition patterns. This means you can:

Use a Flow as a Node within another Flow’s transitions.
Combine multiple smaller Flows into a larger Flow for reuse.
Node params will be a merging of all parents’ params.
Flow’s Node Methods
A Flow is also a Node, so it will run prep() and post(). However:

It won’t run exec(), as its main logic is to orchestrate its nodes.
post() always receives None for exec_res and should instead get the flow execution results from the shared store.
Basic Flow Nesting
Here’s how to connect a flow to another node:

# Create a sub-flow

node_a >> node_b
subflow = Flow(start=node_a)

# Connect it to another node

subflow >> node_c

# Create the parent flow

parent_flow = Flow(start=subflow)

When parent_flow.run() executes:

It starts subflow
subflow runs through its nodes (node_a->node_b)
After subflow completes, execution continues to node_c
Example: Order Processing Pipeline
Here’s a practical example that breaks down order processing into nested flows:

# Payment processing sub-flow

validate_payment >> process_payment >> payment_confirmation
payment_flow = Flow(start=validate_payment)

# Inventory sub-flow

check_stock >> reserve_items >> update_inventory
inventory_flow = Flow(start=check_stock)

# Shipping sub-flow

create_label >> assign_carrier >> schedule_pickup
shipping_flow = Flow(start=create_label)

# Connect the flows into a main order pipeline

payment_flow >> inventory_flow >> shipping_flow

# Create the master flow

order_pipeline = Flow(start=payment_flow)

# Run the entire pipeline

order_pipeline.run(shared_data)

Node
A Node is the smallest building block. Each Node has 3 steps prep->exec->post:

prep(shared)
Read and preprocess data from shared store.
Examples: query DB, read files, or serialize data into a string.
Return prep_res, which is used by exec() and post().
exec(prep_res)
Execute compute logic, with optional retries and error handling (below).
Examples: (mostly) LLM calls, remote APIs, tool use.
⚠️ This shall be only for compute and NOT access shared.
⚠️ If retries enabled, ensure idempotent implementation.
⚠️ Defer exception handling to the Node’s built-in retry mechanism.
Return exec_res, which is passed to post().
post(shared, prep_res, exec_res)
Postprocess and write data back to shared.
Examples: update DB, change states, log results.
Decide the next action by returning a string (action = "default" if None).
Why 3 steps? To enforce the principle of separation of concerns. The data storage and data processing are operated separately.

All steps are optional. E.g., you can only implement prep and post if you just need to process data.

Fault Tolerance & Retries
You can retry exec() if it raises an exception via two parameters when define the Node:

max_retries (int): Max times to run exec(). The default is 1 (no retry).
wait (int): The time to wait (in seconds) before next retry. By default, wait=0 (no waiting). wait is helpful when you encounter rate-limits or quota errors from your LLM provider and need to back off.
my_node = SummarizeFile(max_retries=3, wait=10)

When an exception occurs in exec(), the Node automatically retries until:

It either succeeds, or
The Node has retried max_retries - 1 times already and fails on the last attempt.
You can get the current retry times (0-based) from self.cur_retry.

class RetryNode(Node):
def exec(self, prep_res):
print(f"Retry {self.cur_retry} times")
raise Exception("Failed")

Graceful Fallback
To gracefully handle the exception (after all retries) rather than raising it, override:

def exec_fallback(self, prep_res, exc):
raise exc

By default, it just re-raises exception. But you can return a fallback result instead, which becomes the exec_res passed to post().

Example: Summarize file
class SummarizeFile(Node):
def prep(self, shared):
return shared["data"]

    def exec(self, prep_res):
        if not prep_res:
            return "Empty file content"
        prompt = f"Summarize this text in 10 words: {prep_res}"
        summary = call_llm(prompt)  # might fail
        return summary

    def exec_fallback(self, prep_res, exc):
        # Provide a simple fallback instead of crashing
        return "There was an error processing your request."

    def post(self, shared, prep_res, exec_res):
        shared["summary"] = exec_res
        # Return "default" by not returning

summarize_node = SummarizeFile(max_retries=3)

# node.run() calls prep->exec->post

# If exec() fails, it retries up to 3 times before calling exec_fallback()

action_result = summarize_node.run(shared)

print("Action returned:", action_result) # "default"
print("Summary stored:", shared["summary"])

Communication
Nodes and Flows communicate in 2 ways:

Shared Store (for almost all the cases)

A global data structure (often an in-mem dict) that all nodes can read ( prep()) and write (post()).
Great for data results, large content, or anything multiple nodes need.
You shall design the data structure and populate it ahead.

Separation of Concerns: Use Shared Store for almost all cases to separate Data Schema from Compute Logic! This approach is both flexible and easy to manage, resulting in more maintainable code. Params is more a syntax sugar for Batch.

Params (only for Batch)

Each node has a local, ephemeral params dict passed in by the parent Flow, used as an identifier for tasks. Parameter keys and values shall be immutable.
Good for identifiers like filenames or numeric IDs, in Batch mode.
If you know memory management, think of the Shared Store like a heap (shared by all function calls), and Params like a stack (assigned by the caller).

1. Shared Store
   Overview
   A shared store is typically an in-mem dictionary, like:

shared = {"data": {}, "summary": {}, "config": {...}, ...}

It can also contain local file handlers, DB connections, or a combination for persistence. We recommend deciding the data structure or DB schema first based on your app requirements.

Example
class LoadData(Node):
def post(self, shared, prep_res, exec_res): # We write data to shared store
shared["data"] = "Some text content"
return None

class Summarize(Node):
def prep(self, shared): # We read data from shared store
return shared["data"]

    def exec(self, prep_res):
        # Call LLM to summarize
        prompt = f"Summarize: {prep_res}"
        summary = call_llm(prompt)
        return summary

    def post(self, shared, prep_res, exec_res):
        # We write summary to shared store
        shared["summary"] = exec_res
        return "default"

load_data = LoadData()
summarize = Summarize()
load_data >> summarize
flow = Flow(start=load_data)

shared = {}
flow.run(shared)

Here:

LoadData writes to shared["data"].
Summarize reads from shared["data"], summarizes, and writes to shared["summary"]. 2. Params
Params let you store per-Node or per-Flow config that doesn’t need to live in the shared store. They are:

Immutable during a Node’s run cycle (i.e., they don’t change mid-prep->exec->post).
Set via set_params().
Cleared and updated each time a parent Flow calls it.
Only set the uppermost Flow params because others will be overwritten by the parent Flow.

If you need to set child node params, see Batch.

Typically, Params are identifiers (e.g., file name, page number). Use them to fetch the task you assigned or write to a specific part of the shared store.

Example

# 1) Create a Node that uses params

class SummarizeFile(Node):
def prep(self, shared): # Access the node's param
filename = self.params["filename"]
return shared["data"].get(filename, "")

    def exec(self, prep_res):
        prompt = f"Summarize: {prep_res}"
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        filename = self.params["filename"]
        shared["summary"][filename] = exec_res
        return "default"

# 2) Set params

node = SummarizeFile()

# 3) Set Node params directly (for testing)

node.set_params({"filename": "doc1.txt"})
node.run(shared)

# 4) Create Flow

flow = Flow(start=node)

# 5) Set Flow params (overwrites node params)

flow.set_params({"filename": "doc2.txt"})
flow.run(shared) # The node summarizes doc2, not doc1

Batch
Batch makes it easier to handle large inputs in one Node or rerun a Flow multiple times. Example use cases:

Chunk-based processing (e.g., splitting large texts).
Iterative processing over lists of input items (e.g., user queries, files, URLs).

1. BatchNode
   A BatchNode extends Node but changes prep() and exec():

prep(shared): returns an iterable (e.g., list, generator).
exec(item): called once per item in that iterable.
post(shared, prep_res, exec_res_list): after all items are processed, receives a list of results (exec_res_list) and returns an Action.
Example: Summarize a Large File
class MapSummaries(BatchNode):
def prep(self, shared): # Suppose we have a big file; chunk it
content = shared["data"]
chunk_size = 10000
chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
return chunks

    def exec(self, chunk):
        prompt = f"Summarize this chunk in 10 words: {chunk}"
        summary = call_llm(prompt)
        return summary

    def post(self, shared, prep_res, exec_res_list):
        combined = "\n".join(exec_res_list)
        shared["summary"] = combined
        return "default"

map_summaries = MapSummaries()
flow = Flow(start=map_summaries)
flow.run(shared)

2. BatchFlow
   A BatchFlow runs a Flow multiple times, each time with different params. Think of it as a loop that replays the Flow for each parameter set.

Key Differences from BatchNode
Important: Unlike BatchNode, which processes items and modifies the shared store:

BatchFlow returns parameters to pass to the child Flow, not data to process
These parameters are accessed in child nodes via self.params, not from the shared store
Each child Flow runs independently with a different set of parameters
Child nodes can be regular Nodes, not BatchNodes (the batching happens at the Flow level)
Example: Summarize Many Files
class SummarizeAllFiles(BatchFlow):
def prep(self, shared): # IMPORTANT: Return a list of param dictionaries (not data for processing)
filenames = list(shared["data"].keys()) # e.g., ["file1.txt", "file2.txt", ...]
return [{"filename": fn} for fn in filenames]

# Child node that accesses filename from params, not shared store

class LoadFile(Node):
def prep(self, shared): # Access filename from params (not from shared)
filename = self.params["filename"] # Important! Use self.params, not shared
return filename

    def exec(self, filename):
        with open(filename, 'r') as f:
            return f.read()

    def post(self, shared, prep_res, exec_res):
        # Store file content in shared
        shared["current_file_content"] = exec_res
        return "default"

# Summarize node that works on the currently loaded file

class Summarize(Node):
def prep(self, shared):
return shared["current_file_content"]

    def exec(self, content):
        prompt = f"Summarize this file in 50 words: {content}"
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        # Store summary in shared, indexed by current filename
        filename = self.params["filename"]  # Again, using params
        if "summaries" not in shared:
            shared["summaries"] = {}
        shared["summaries"][filename] = exec_res
        return "default"

# Create a per-file flow

load_file = LoadFile()
summarize = Summarize()
load_file >> summarize
summarize_file = Flow(start=load_file)

# Wrap in a BatchFlow to process all files

summarize_all_files = SummarizeAllFiles(start=summarize_file)
summarize_all_files.run(shared)

Under the Hood
prep(shared) in the BatchFlow returns a list of param dicts—e.g., [{"filename": "file1.txt"}, {"filename": "file2.txt"}, ...].
The BatchFlow loops through each dict. For each one:
It merges the dict with the BatchFlow’s own params (if any): {**batch_flow.params, **dict_from_prep}
It calls flow.run(shared) using the merged parameters
IMPORTANT: These parameters are passed to the child Flow’s nodes via self.params, NOT via the shared store
This means the sub-Flow is run repeatedly, once for every param dict, with each node in the flow accessing the parameters via self.params. 3. Nested or Multi-Level Batches
You can nest a BatchFlow in another BatchFlow. For instance:

Outer batch: returns a list of directory param dicts (e.g., {"directory": "/pathA"}, {"directory": "/pathB"}, …).
Inner batch: returning a list of per-file param dicts.
At each level, BatchFlow merges its own param dict with the parent’s. By the time you reach the innermost node, the final params is the merged result of all parents in the chain. This way, a nested structure can keep track of the entire context (e.g., directory + file name) at once.

class FileBatchFlow(BatchFlow):
def prep(self, shared): # Access directory from params (set by parent)
directory = self.params["directory"] # e.g., files = ["file1.txt", "file2.txt", ...]
files = [f for f in os.listdir(directory) if f.endswith(".txt")]
return [{"filename": f} for f in files]

class DirectoryBatchFlow(BatchFlow):
def prep(self, shared):
directories = [ "/path/to/dirA", "/path/to/dirB"]
return [{"directory": d} for d in directories]

# The actual processing node

class ProcessFile(Node):
def prep(self, shared): # Access both directory and filename from params
directory = self.params["directory"] # From outer batch
filename = self.params["filename"] # From inner batch
full_path = os.path.join(directory, filename)
return full_path

    def exec(self, full_path):
        # Process the file...
        return f"Processed {full_path}"

    def post(self, shared, prep_res, exec_res):
        # Store results, perhaps indexed by path
        if "results" not in shared:
            shared["results"] = {}
        shared["results"][prep_res] = exec_res
        return "default"

# Set up the nested batch structure

process_node = ProcessFile()
inner_flow = FileBatchFlow(start=process_node)
outer_flow = DirectoryBatchFlow(start=inner_flow)

# Run it

outer_flow.run(shared)

(Advanced) Async
Async Nodes implement prep_async(), exec_async(), exec_fallback_async(), and/or post_async(). This is useful for:

prep_async(): For fetching/reading data (files, APIs, DB) in an I/O-friendly way.
exec_async(): Typically used for async LLM calls.
post_async(): For awaiting user feedback, coordinating across multi-agents or any additional async steps after exec_async().
Note: AsyncNode must be wrapped in AsyncFlow. AsyncFlow can also include regular (sync) nodes.

Example
class SummarizeThenVerify(AsyncNode):
async def prep_async(self, shared): # Example: read a file asynchronously
doc_text = await read_file_async(shared["doc_path"])
return doc_text

    async def exec_async(self, prep_res):
        # Example: async LLM call
        summary = await call_llm_async(f"Summarize: {prep_res}")
        return summary

    async def post_async(self, shared, prep_res, exec_res):
        # Example: wait for user feedback
        decision = await gather_user_feedback(exec_res)
        if decision == "approve":
            shared["summary"] = exec_res
            return "approve"
        return "deny"

summarize_node = SummarizeThenVerify()
final_node = Finalize()

# Define transitions

summarize_node - "approve" >> final_node
summarize_node - "deny" >> summarize_node # retry

flow = AsyncFlow(start=summarize_node)

async def main():
shared = {"doc_path": "document.txt"}
await flow.run_async(shared)
print("Final Summary:", shared.get("summary"))

asyncio.run(main())
