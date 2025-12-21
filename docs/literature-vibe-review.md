# 📚 Literature Vibe-Review

Simple guide for performing citation-backed research using MCP servers.

## 🛠️ 1. MCP Servers

- **arXiv MCP Server**: [blazickjp/arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server)

*Best for searching, downloading, and reading full arXiv papers.*

- **Paper Search MCP**: [openags/paper-search-mcp](https://github.com/openags/paper-search-mcp)

*Best for multi-source search (PubMed, bioRxiv) and Semantic Scholar citation tracing.*

---

## ⚙️ 2. MCP Configurations

### 🚀 Cursor

Configure these in **Settings > Features > MCP > Add New MCP Server**.

Detailed guide: [cursor.com/docs/context/mcp](https://cursor.com/docs/context/mcp)

**arXiv Server:**

- **Name**: `arxiv`

- **Type**: `command`

- **Command**: `uv tool run arxiv-mcp-server --storage-path "/path/to/paper/storage"`

**Paper Search Server:**

- **Name**: `paper-search`

- **Type**: `command`

- **Command**: `uv run --directory "/path/to/your/paper-search-mcp" -m paper_search_mcp.server`

### 💻 VS Code

Native Copilot configuration uses `mcp.json`.

Detailed guide: [code.visualstudio.com/docs/copilot/customization/mcp-servers](https://code.visualstudio.com/docs/copilot/customization/mcp-servers)

Copy-paste this into your configuration file:

```json
{
  "mcpServers": {
    "paper_search_server": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/your/paper-search-mcp",
        "-m",
        "paper_search_mcp.server"
      ],
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "" 
      }
    },
    "arxiv-mcp-server": {
      "command": "uv",
      "args": [
        "tool",
        "run",
        "arxiv-mcp-server",
        "--storage-path",
        "/path/to/paper/storage"
      ]
    }
  }
}
```

---

## 📝 3. Literature Review Prompts

### Prompt 1: Systematic Keyword Review

"Act as a Senior Research Scientist. Conduct a systematic literature review on **[TOPIC]** for the period **202{X}-202{Y}**.

1. Search papers using the suitable keywords to find the {N} most relevant papers.

2. For each, retrieve the abstract and key findings.

3. Synthesize a review categorized by themes.

**Constraint**: Zero hallucinations. Only cite papers retrieved via MCP tools. Use real arXiv IDs/DOIs. Feel free to use web search for finding correct citations if necessary."

### Prompt 2: Citation "Snowballing" (Tracing Lineage)

"Act as a Senior Research Scientist. Conduct a systematic literature review on **[TOPIC]** for the period **202{X}-202{Y}**.

I am providing these seed papers: **[LIST IDS]**.

1. Use the citation tools to find:
- {N} papers that have cited these (Forward Trace).

- {N} seminal works cited by these (Backward Trace).
2. Trace the evolution of the core concept between these works.

**Constraint**: Every citation must have a real DOI or link. If not found, state 'Reference not found' instead of guessing. Feel free to use web search for finding correct citations if necessary."
