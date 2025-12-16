# Deep Agent Pipeline Status Report

**Date:** 2025-12-16
**Version:** 2.2 (Self-Correcting)

## 1. Architecture Overview

The pipeline implements a **Hierarchical Autonomous Agent** pattern ("Deep Agents"), designed to transform a raw codebase into high-quality educational tutorials. It operates in two sequential phases:

1.  **Knowledge Base (KB) Generation**: A Supervisor Agent spawns Sub-Agents to analyze the codebase and generate component-level documentation.
2.  **Tutorial Generation**: A Supervisor Agent spawns Sub-Agents to write tutorials using the generated Knowledge Base.

### Core Workflow
```mermaid
graph TD
    User[User / CLI] -->|Start| KBSup[KB Supervisor Agent]
    
    subgraph Phase 1: Knowledge Base
    KBSup -->|Plan| Target[Identify Targets (Files/Dirs)]
    KBSup -->|Spawn| KBSub[KB Analyzer Sub-Agent]
    KBSub -->|Read/Write| Workspace[Sub-Agent Workspace]
    Workspace -->|Validate| Validation[Validation Logic]
    Validation -->|Feedback| KBSup
    KBSup -->|Retry (if needed)| RetrySub[Retry Agent]
    KBSup -->|Finalize| KBStore[Knowledge Base (/data/knowledge_base)]
    end
    
    KBStore -->|Input| TutSup[Tutorial Supervisor Agent]
    
    subgraph Phase 2: Tutorials
    TutSup -->|Plan| Topic[Identify Tutorial Topics]
    TutSup -->|Spawn| TutSub[Tutorial Writer Sub-Agent]
    TutSub -->|Read KB/Code| KBStore
    TutSub -->|Write| TutWorkspace[Tutorial Workspace]
    TutWorkspace -->|Validate| TutValidation[Validation Logic]
    TutValidation -->|Feedback| TutSup
    TutSup -->|Finalize| FinalTuts[Tutorials (/data/tutorials)]
    end
```

## 2. Key Optimizations & Current State

### A. Performance & Efficiency
*   **File Pre-loading (New):** The `spawn_analyzer_agent` tool now pre-reads the content of "focus files" (up to 3000 chars) and injects them directly into the Sub-Agent's task prompt.
    *   *Result:* Reduces Sub-Agent steps from ~5-8 to ~1-2 per file (mostly just writing output).
    *   *Reduction:* Eliminates redundant `read_codebase_file` calls.
*   **Integrated Validation:** Validation runs *immediately* within the `spawn` tool after the Sub-Agent finishes.
    *   *Result:* Supervisor gets success/failure feedback in a single turn, removing the need for separate `read_agent_output` and `evaluate` steps.
*   **Lazy Loading:** Sub-Agents are spawned with `minimal_tools=False` (full access) for Retries, but focused tools for initial runs.

### B. Reliability & Determinism
*   **Retry Logic:** 
    *   KBs: Retries have full file system access (`list`, `tree`, `read`) to fix "file not found" errors.
    *   Tutorials: Retries prioritize correcting specific feedback using RAG and KB access.
*   **Deterministic Finalization:** `FinalizeTutorialsTool` logic sorts workspaces so that `retry_N_...` folders always overwrite original attempts. This ensures the *latest corrected version* is the one saved.
*   **Fallback Handling:** Relaxed validation for "no response" text to prevent false positives on valid documentation containing that phrase.

### C. Self-Correction & Auto-Healing (New)
*   **Supervisor Self-Repair:** The Supervisor can now read sub-agent outputs (`read_workspace_file`) and fix minor issues like formatting or missing headers directly (`rewrite_workspace_file`) without spawning a new agent.
*   **Smart Validation:** Validation distinguishes between critical errors (truncation, empty) which trigger retries, and minor warnings (bold/italic balance) which are either auto-fixed or ignored.

### D. Tools & Capabilities

#### Supervisor Agent Tools
| Tool | Purpose | Status |
|------|---------|--------|
| `get_codebase_overview` | High-level tree & README analysis | Active |
| `list_codebase_directory` | Explore folder structure | Active |
| `read_codebase_file` | Read specific files (for planning) | Active |
| `write_workspace_file` | **Core:** Write Plan / generic files | **New** |
| `read_workspace_file` | **Fixing:** Read Sub-Agent output | **New** |
| `rewrite_workspace_file` | **Fixing:** Overwrite Sub-Agent output | **New** |
| `spawn_analyzer_agent` | **Core:** Creates sub-agent + Pre-loads content + Validates | **Optimized** |
| `spawn_tutorial_agent` | **Core:** Creates tutorial writer + Validates | **Optimized** |
| `retry_agent` | Spawns a targeted fixer agent (Only for critical errors) | Active |
| `finalize_knowledge_base`| Moves drafts to final KB folder | Active |
| `finalize_tutorials` | Moves drafts to final Tutorials folder (Priority Logic) | **Optimized** |

#### Sub-Agent Tools (KB Analyzer)
| Tool | Purpose | Usage |
|------|---------|-------|
| `write_workspace_file` | Write `summary.md` | Primary |
| `read_codebase_file` | Read source code | Secondary (Fallback) |
| `list_codebase_directory`| List files | Retry / Fallback |
| `get_codebase_tree` | See structure | Retry / Fallback |

#### Sub-Agent Tools (Tutorial Writer)
| Tool | Purpose | Usage |
|------|---------|-------|
| `write_tutorial_file` | Write tutorial markdown | Primary |
| `read_knowledge_base_file`| Read KB docs | Primary |
| `read_codebase_file` | Extract code snippets | Primary |
| `retrieve_relevant_context`| RAG Search | Auxiliary |

## 3. Pros & Cons

### ✅ Pros
1.  **Speed**: IO Pre-loading significantly drastically reduces execution time and token usage per Sub-Agent.
2.  **Robustness**: Retry agents have "superpowers" (more tools) compared to initial agents, increasing fix rates.
3.  **Quality Control**: Strict validation (Mermaid syntax, length, empty checks) prevents bad data from entering the KB.
4.  **Isolation**: Sub-agents work in sandboxed directories; failed agents don't corrupt the main KB.
5.  **Clean Architecture**: Supervisor doesn't micromanage; it delegates and reviews.

### ⚠️ Cons / Risks
1.  **Context Window**: Pre-loading files consumes Supervisor context. If 10 files * 3k chars are pre-loaded, it might hit token limits (mitigated by `MAX_READ_LINES`).
2.  **Complexity**: The interaction between `spawn`, `validation`, and `retry` logic is complex to debug if something hangs.
3.  **Gemini Limits**: High concurrency can still trigger `429 RESOURCE_EXHAUSTED` (Vertex AI), though retry logic handles this gracefully.
4.  **"Lost" Drafts**: If the Supervisor crashes mid-loop, drafts remain in `sub_agents_worsapce` until the next resume (which is supported).

## 4. Next Steps / Recommendations
1.  **Monitor Context Usage**: Watch for "Context length exceeded" errors on very large files.
2.  **RAG Tuning**: Ensure Tutorial Agents use `retrieve_relevant_context` effectively (currently usage is low).
3.  **Parallelization**: Currently sequential. Could implement parallel Sub-Agent execution for massive speedup (requires async refactor).
