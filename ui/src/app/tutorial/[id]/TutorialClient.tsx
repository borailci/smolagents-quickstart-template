'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import LoadingProgress from '@/components/LoadingProgress';
import FileSidebar from '@/components/FileSidebar';
import Toolbar from '@/components/Toolbar';
import MarkdownViewer from '@/components/MarkdownViewer';
import MarkdownEditor from '@/components/MarkdownEditor';
import { Codebase } from '@/types';

// Sample markdown content for demo purposes
const sampleMarkdownContent: { [key: string]: string } = {
    '/tutorials/smolagents/1_llms.md': `# Module 1: Large Language Model (LLM) Fundamentals

Welcome to the first module of our AI tutorial series! As your expert tutor, I'll guide you through the basics of Large Language Models (LLMs) in a clear, step-by-step way.

## I. Introduction to Large Language Models (LLMs)

### A. Core Definition

What are LLMs? They're just models that take text as input and output text. You give them a prompt, and they generate a response based on patterns learned from training data.

Imagine an LLM as a super-smart text machine. You give it some words (called a **prompt**), and it replies with more words (called **generation**). It's like chatting with a knowledgeable friend who predicts what you'll say next.

\`\`\`python
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
\`\`\`

### B. Key Parameters

LLMs have settings to control output:

- **Temperature**: 0.0 to 1.0. Low (0.1-0.3) for accurate, consistent answers.
- **Max Output Tokens**: Limits response length to save costs.
- **Context Window**: Max text (input + output) per call.

## II. LLM Workflow Diagram

Here's how an LLM processes your request:

\`\`\`mermaid
graph TD
    A[User Prompt] --> B[Tokenization]
    B --> C[Transformer Processing]
    C --> D[Attention Mechanism]
    D --> E[Generate Tokens]
    E --> F[Output Text]
    style A fill:#8B5CF6,color:#fff
    style F fill:#06B6D4,color:#fff
\`\`\`

## III. API Access Strategy

\`\`\`mermaid
graph LR
    A[Your Application] --> B[OpenRouter API]
    B --> C[Google AI]
    B --> D[OpenAI]
    B --> E[Anthropic]
    B --> F[Other Providers]
    style B fill:#8B5CF6,color:#fff
\`\`\`

### Getting Started

1. Sign up at [OpenRouter](https://openrouter.ai/)
2. Get your API key
3. Start making requests!

> **Pro Tip**: Use low temperatures (0.1–0.3) for tasks like code analysis where you need consistency over creativity.

## Summary

You've learned the basics of LLMs: what they are, how they work, and their limits. Keep practicing with prompts—it's key to mastering AI!

**Next Module:** [Module 2: RAG Systems](2_rag.md)
`,

    '/tutorials/smolagents/2_rag.md': `# Module 2: Retrieval-Augmented Generation (RAG)

Welcome to Module 2! Now we'll explore how to enhance LLMs with external knowledge using RAG.

## What is RAG?

RAG combines the power of LLMs with external knowledge retrieval. Instead of relying solely on what the model learned during training, RAG fetches relevant documents to provide context.

\`\`\`mermaid
graph TD
    A[User Query] --> B[Embedding Model]
    B --> C[Vector Database]
    C --> D[Retrieve Relevant Docs]
    D --> E[Combine with Query]
    E --> F[LLM Processing]
    F --> G[Enhanced Response]
    style A fill:#06B6D4,color:#fff
    style G fill:#8B5CF6,color:#fff
\`\`\`

## Key Components

### 1. Vector Database

Store your documents as embeddings for semantic search:

\`\`\`python
import chromadb
from chromadb.utils import embedding_functions

# Initialize ChromaDB
client = chromadb.Client()
collection = client.create_collection(
    name="documents",
    embedding_function=embedding_functions.DefaultEmbeddingFunction()
)

# Add documents
collection.add(
    documents=["Document 1 content", "Document 2 content"],
    ids=["doc1", "doc2"]
)
\`\`\`

### 2. Retrieval Pipeline

Query your knowledge base:

\`\`\`python
results = collection.query(
    query_texts=["What is machine learning?"],
    n_results=3
)
\`\`\`

## Best Practices

| Strategy | Description | Impact |
|----------|-------------|--------|
| Chunking | Split docs into smaller pieces | Higher precision |
| Overlap | Add overlap between chunks | Better context |
| Metadata | Store doc metadata | Enable filtering |

---

**Next Module:** [Module 3: Tool Integration](3_tools.md)
`,

    '/tutorials/smolagents/3_tools.md': `# Module 3: Tool Integration

Learn how to extend your AI agents with custom tools!

## Why Tools?

LLMs can reason and generate text, but they can't:
- Access real-time data
- Execute code
- Interact with external systems

Tools bridge this gap!

\`\`\`mermaid
graph LR
    A[AI Agent] --> B{Tool Router}
    B --> C[Web Search]
    B --> D[Calculator]
    B --> E[Code Executor]
    B --> F[File System]
    style A fill:#EC4899,color:#fff
\`\`\`

## Creating a Tool

\`\`\`python
from smolagents import tool

@tool
def get_weather(city: str) -> str:
    """Get current weather for a city.
    
    Args:
        city: The city name to get weather for
    
    Returns:
        Current weather description
    """
    # Implementation here
    return f"Weather in {city}: Sunny, 25°C"
\`\`\`

## Built-in Tools

- **WebSearchTool**: Search the internet
- **VisitWebpageTool**: Browse web pages
- **PythonInterpreterTool**: Execute Python code

> Tools transform LLMs from text generators into **action-taking agents**!

**Next Module:** [Module 4: Agent Architecture](4_agents.md)
`,

    '/tutorials/smolagents/4_agents.md': `# Module 4: Agent Architecture

Dive deep into how AI agents think and act!

## The Agent Loop

\`\`\`mermaid
graph TD
    A[Receive Task] --> B[Think/Plan]
    B --> C{Need Tool?}
    C -->|Yes| D[Select Tool]
    D --> E[Execute Tool]
    E --> F[Observe Result]
    F --> B
    C -->|No| G[Generate Response]
    style A fill:#8B5CF6,color:#fff
    style G fill:#10B981,color:#fff
\`\`\`

## Agent Types

### 1. ReAct Agent

Combines **Reasoning** and **Acting**:

\`\`\`python
from smolagents import CodeAgent, LiteLLMModel

model = LiteLLMModel(model_id="gpt-4")
agent = CodeAgent(tools=[get_weather], model=model)

result = agent.run("What's the weather in Paris?")
\`\`\`

### 2. Tool-Calling Agent

Uses structured tool calls:

\`\`\`python
from smolagents import ToolCallingAgent

agent = ToolCallingAgent(
    tools=[search_tool, calc_tool],
    model=model
)
\`\`\`

## Memory Systems

| Type | Persistence | Use Case |
|------|-------------|----------|
| Short-term | Per session | Context tracking |
| Long-term | Persistent | Learning patterns |
| Episodic | Query-based | Past experiences |

**Next Module:** [Module 5: Multi-Agent Systems](5_multi_agent.md)
`,

    '/tutorials/smolagents/5_multi_agent.md': `# Module 5: Multi-Agent Systems

The future of AI: agents working together!

## Why Multi-Agent?

\`\`\`mermaid
graph TD
    subgraph Orchestrator
        A[Manager Agent]
    end
    subgraph Workers
        B[Research Agent]
        C[Analysis Agent]
        D[Writing Agent]
    end
    A --> B
    A --> C
    A --> D
    B --> A
    C --> A
    D --> A
    style A fill:#8B5CF6,color:#fff
\`\`\`

## Patterns

### 1. Hierarchical

\`\`\`python
from smolagents import ManagedAgent

# Create specialized agents
researcher = CodeAgent(tools=[search_tool], model=model)
writer = CodeAgent(tools=[write_tool], model=model)

# Wrap as managed agents
managed_researcher = ManagedAgent(
    agent=researcher,
    name="researcher",
    description="Searches for information"
)

# Create orchestrator
orchestrator = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[managed_researcher]
)
\`\`\`

### 2. Collaborative

Agents communicate peer-to-peer:

\`\`\`mermaid
graph LR
    A[Agent A] <--> B[Agent B]
    B <--> C[Agent C]
    C <--> A
    style A fill:#06B6D4,color:#fff
    style B fill:#EC4899,color:#fff
    style C fill:#10B981,color:#fff
\`\`\`

## Best Practices

1. **Clear Roles**: Define specific responsibilities
2. **Minimal Communication**: Reduce overhead
3. **Error Handling**: Graceful degradation
4. **Monitoring**: Track agent interactions

> 🎉 Congratulations! You've completed the tutorial series!

---

Built with ❤️ using the Codebase Tutorial Generator
`
};

// Default content for files not in the sample
const defaultContent = `# Tutorial Coming Soon

This tutorial module is being generated by our AI agents.

Check back soon for comprehensive learning content!

\`\`\`mermaid
graph TD
    A[AI Agents] --> B[Processing]
    B --> C[Tutorial Ready!]
    style C fill:#10B981,color:#fff
\`\`\`
`;

export default function TutorialClient({ codebase, id }: { codebase: Codebase, id: string }) {
    const [isLoading, setIsLoading] = useState(true);
    const [isReady, setIsReady] = useState(false);
    const [activeFile, setActiveFile] = useState<string>(
        codebase.files.length > 0 ? codebase.files[0].path : ''
    );
    const [content, setContent] = useState<string>('');
    const [isEditMode, setIsEditMode] = useState(false);
    const [contentScale, setContentScale] = useState(1);

    // Load content when active file changes
    useEffect(() => {
        if (activeFile) {
            const fileContent = sampleMarkdownContent[activeFile] || defaultContent;
            setContent(fileContent);
        }
    }, [activeFile]);

    // Handle loading complete
    const handleLoadingComplete = useCallback(() => {
        setIsLoading(false);
        setTimeout(() => setIsReady(true), 100);
    }, []);

    // Toggle edit mode
    const handleToggleEditMode = useCallback(() => {
        setIsEditMode(prev => !prev);
    }, []);

    // Handle content change in editor
    const handleContentChange = useCallback((newContent: string) => {
        setContent(newContent);
    }, []);

    // Handle save
    const handleSave = useCallback((savedContent: string) => {
        // In a real app, this would save to the server
        console.log('Saving content:', savedContent.substring(0, 100) + '...');
        // For demo, save to localStorage
        localStorage.setItem(`tutorial-${id}-${activeFile}`, savedContent);
    }, [id, activeFile]);

    // Keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
                e.preventDefault();
                handleToggleEditMode();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleToggleEditMode]);

    // Zoom handlers
    const handleZoomIn = () => setContentScale(prev => Math.min(prev + 0.1, 1.5));
    const handleZoomOut = () => setContentScale(prev => Math.max(prev - 0.1, 0.7));

    const currentFile = codebase.files.find(f => f.path === activeFile);

    return (
        <>
            {/* Loading screen */}
            <LoadingProgress
                isVisible={isLoading}
                onComplete={handleLoadingComplete}
                accentColor={codebase.color}
                codebaseName={codebase.name}
            />

            {/* Main content */}
            <AnimatePresence>
                {isReady && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.5 }}
                        className="min-h-screen"
                    >
                        {/* Toolbar */}
                        <Toolbar
                            codebaseName={codebase.name}
                            currentFileName={currentFile?.title || 'Unknown'}
                            isEditMode={isEditMode}
                            onToggleEditMode={handleToggleEditMode}
                            onZoomIn={handleZoomIn}
                            onZoomOut={handleZoomOut}
                            accentColor={codebase.color}
                        />

                        <div className="flex">
                            {/* Sidebar */}
                            <FileSidebar
                                files={codebase.files}
                                activeFile={activeFile}
                                onFileSelect={setActiveFile}
                                accentColor={codebase.color}
                            />

                            {/* Content area */}
                            <main className="flex-1 min-h-[calc(100vh-8rem)]">
                                <AnimatePresence mode="wait">
                                    {isEditMode ? (
                                        <motion.div
                                            key="editor"
                                            initial={{ opacity: 0, x: 20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            exit={{ opacity: 0, x: -20 }}
                                            transition={{ duration: 0.3 }}
                                            className="h-[calc(100vh-8rem)] p-4"
                                        >
                                            <MarkdownEditor
                                                content={content}
                                                onChange={handleContentChange}
                                                onSave={handleSave}
                                                accentColor={codebase.color}
                                            />
                                        </motion.div>
                                    ) : (
                                        <motion.div
                                            key="viewer"
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            exit={{ opacity: 0, x: 20 }}
                                            transition={{ duration: 0.3 }}
                                            className="p-6 md:p-10 max-w-4xl mx-auto"
                                            style={{
                                                transform: `scale(${contentScale})`,
                                                transformOrigin: 'top center'
                                            }}
                                        >
                                            <MarkdownViewer
                                                content={content}
                                                accentColor={codebase.color}
                                            />
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </main>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
