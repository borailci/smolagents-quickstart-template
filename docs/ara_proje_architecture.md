# Ara Proje Architecture Plan

## Overview

This plan translates the project methodologies (`docs/how_to.md`, `docs/methodology_overview.md`, `docs/methodology_vibe_coding.md`) into concrete implementation steps for the Ara Proje (tutorial generation). The system operates in two major phases: a pre-processing phase that builds a markdown knowledge base via sub-agents, and a downstream phase that uses the knowledge base to produce beginner-friendly tutorials.

```
Codebase -> Sub-Agent Pipeline -> Knowledge Base (markdown) -> Tutorial Generator -> Tutorials (markdown)
```

## Phase 1 — Knowledge Base Generation (Sub-Agent Pipeline)

### High-Level Flow

1. **Main Agent Initialization**

   - Loads configuration (codebase path, output roots).
   - Retrieves repository tree and key files (e.g., README, entry point) using safe workspace tools.
   - Applies deterministic planning: find first-level directories under `src/` (fallback to top-level files/directories if `src/` missing).

2. **Task Decomposition**

   - For each selected directory, prepare a task payload describing scope, required outputs, formatting guidelines, and file hints.
   - Additional optional tasks: global overview, configuration, tests, docs.

3. **spawn_sub_agents Tool**

   - Input: number of tasks, list of task descriptions.
   - Loop sequentially, creating a dedicated workspace per task (`data/sub_agents_workspace/sub_agent_{i}/`).
   - Instantiate a `ToolCallingAgent` with scoped tools (read-only access to codebase, write-only access to its workspace, plus listing + tree helpers).
   - Run the agent with provided task; the agent writes markdown output (e.g., `analysis.md`, `summary.md`).
   - Return only a summary with workspace paths; main agent must read results explicitly later.

4. **Aggregation**
   - Main agent uses read-only tools to gather all markdown files from sub-agent workspaces.
   - Produces synthesized knowledge base: merges, deduplicates, adds table of contents, cross-links. Output stored under `data/knowledge_base/` (e.g., `overview.md`, `api.md`, `models.md`).

### Scoped Tooling Requirements

- **Security:** All file operations must resolve absolute paths (`os.path.abspath`/`realpath`) and ensure they remain within the allowed root. Reject traversal attempts.
- **Tools per Sub-Agent:**
  - `read_codebase_file(path)`
  - `list_codebase_directory(path=".")`
  - `get_codebase_tree()`
  - `write_workspace_file(path, content)` (auto-create directories, markdown friendly)
- **Main Agent Tools:**
  - Existing workspace tools (`read_file`, `write_file`, `list_workspace_dir`, `get_tree`)
  - `spawn_sub_agents`

### Prompting & Instructions

- **Main Agent Prompt:** Emphasize deterministic planning, requirement to inspect `src/`, README, config. Outline workflow steps, naming conventions, markdown quality, and instructions to read sub-agent outputs. Remind to avoid direct sub-agent context.
- **Sub-Agent Prompt Template:** Provide structured sections (Purpose, Key Components, APIs, Data Flow), enforce markdown headings, demand code snippets and cross-links. Encourage Mermaid diagrams when relevant.

## Phase 2 — Tutorial Generation

### Inputs

- Knowledge base files under `data/knowledge_base/`
- Original codebase for snippet retrieval (same read-only tools as sub-agents).

### Workflow

1. Load knowledge base metadata (toc, file paths).
2. Define tutorial outline (3–5 chapters) targeting beginners: overview, setup, architecture, workflows, extending/testing.
3. For each chapter:
   - Pull relevant knowledge base sections.
   - Retrieve supporting code snippets directly from source files (ensure custom retrieval per methodology).
   - Compose markdown with narrative + snippets + diagrams (prefer Mermaid).
   - Save under `data/tutorials/` (e.g., `01_getting_started.md`).
4. Build index file summarizing tutorials and linking to knowledge base sections.

### Retrieval Strategy

- Use lightweight deterministic retrieval: path filters + regex selectors based on knowledge base references.
- Optionally augment with embedding/RAG if time allows (not required).

## Interface & Orchestration

- Provide a single entrypoint (CLI command or minimal UI panel) that accepts a repo path/URL, synchronizes it into a read-only directory (`data/codebase_input/`), and runs:
  1. Knowledge base pipeline
  2. Tutorial generation
- Report output locations and basic metrics (number of files, execution time, encountered warnings).

## Testing & Validation

- Unit tests for scoped path validation (include negative traversal cases).
- Tests for `spawn_sub_agents` verifying workspace isolation and summary output.
- Integration smoke test using `data/agent_workspace/sample_codebase/` to ensure pipeline produces knowledge base and tutorials.
- Markdown linting/structure checks (headings, TOC presence).

## Next Steps

1. Implement secure path utilities and scoped tool wrappers.
2. Create prompts and agent classes reflecting this architecture.
3. Build `spawn_sub_agents` tool and integration with main agent.
4. Implement aggregation + knowledge base writer.
5. Develop tutorial generator module and entrypoint.
6. Add automated tests and documentation updates.
