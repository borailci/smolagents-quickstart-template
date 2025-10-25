# Our goal in this project
from a high level perspective, given a codebase in any language, we want to design and develop a system that can generate a knowledge base of that codebase and then use this knowledge base for various downstream tasks such as code generation, code explanation, code debugging, etc.
By knowledge base we mean a set of static, pre-build markdown files that explain the codebase in a structured way in detail, similar to what we see in DeepWiki (https://deepwiki.org/).

##  Downstream tasks
In this project, the downstream task for group doing their "ara proje" is:
- Generate a tutorial in the form of multiple markdown files that explains how the codebase works and how to use it. This tutorial should be beginner friendly and should cover all the important aspects of the codebase. This tutorial can be used by either junior developers who are new to the codebase or by senior developers who are new to the codebase and want to get up to speed quickly.
These markdown files should contain real or example code snippets, explanations, diagrams (ASCII art or preferably Mermaid), and any other relevant information that can help the user understand the codebase better.
These markdown files should be generated using the knowledge base generated from the codebase and retreiving code snippets from the codebase itself using a **custom retrieval mechanism** such as the agent opening the code files dynamically **while generating the tutorial**. OPTIONALLY, RAG can also be used for this purpose.

In this project the downstream task for group doing their "final proje" is:
- design a chatbot that users can interact with to ask questions about the codebase. The chatbot should be able to answer questions about the codebase, provide code snippets, explain how certain parts of the codebase work, and help users navigate the codebase effectively.
This chatbot should be able to understand natural language queries and provide accurate and relevant responses using on BOTH the **knowledge base** generated from the codebase and retreiving code snippets from the codebase itself using either **RAG or a custom retrieval mechanism** such as the agent opening the code files dynamically, both at the knowledge base generation phase and during user interaction (runtime).

##  Expected output
- The output of the "ara proje" is a set of markdown files that explain the codebase in a structured way without any chatbot GUI. A very simple UI that accepts url of the github repo as user input and generates and saves the markdown files in local machine is sufficient. The input can also be a local path to the codebase.

- The output of the "final proje" is a chatbot GUI that users can interact with to ask questions about the codebase. 

IN BOTH CASES, THE KNOWLEDGE BASE MUST BE GENERATED FIRST AND THEN USED FOR THE DOWNSTREAM TASK. THE KNOWLEDGE BASE MUST NOT BE GENERATED ON THE FLY DURING THE DOWNSTREAM TASK. THE KNOWLEDGE BASE IS AN INTERMEDIATE STEP THAT BOTH PROJECTS MUST IMPLEMENT AND USE. 

A mermaid diagram showing the pre-processing phase with sub-agents architecture for knowledge base generation, followed by the knowledge base as a common intermediate step, and then the runtime phase with two subgraphs for tutorial generation and chatbot:

```mermaid
graph TD
    subgraph "Pre-processing Phase"
        A[Codebase] --> B["Agent (Sub-agents Architecture Methodology)"]
        B --> C[Generate Knowledge Base]
    end
    subgraph "Knowledge Base"
        C --> D["Knowledge Base (Markdown Files)"]
    end
    subgraph "Runtime Phase"
        subgraph "Tutorial Generation"
            D --> E[Tutorial Generation Process]
        end
        subgraph "Chatbot"
            D --> F[Chatbot Process]
        end
    end
    style D fill:#f9f,stroke:#333,stroke-width:4px
```

The pre-processing phase involves the agent using a sub-agents architecture methodology to generate the knowledge base from the codebase. The knowledge base is then used as a common intermediate step for both the tutorial generation process and the chatbot process in the runtime phase.


## Methodology: Sub-agents Architecture
To generate the knowledge base from the codebase, we will use a sub-agents architecture methodology. Before diving into the details of this methodology, let's first understand in order to generate the knowledge base, what options we have, what are their pros and cons, and why we chose this particular methodology.

Here we compare three different methodologies for generating the knowledge base from the codebase and discuss their pros and cons and why we chose the sub-agents architecture methodology.
We do not use options 1 and 2 because of their limitations discussed below. We only use option 3: Sub-agents Architecture Methodology. However, we discuss all three options so you can better understand the trade-offs and why we chose this particular methodology.

### Option 1: Monolithic Agent or LLM
#### 1.1: Single LLM 
Lets say we want to use a single LLM: In this appraoch we have to linearly feed the whole codebase to the LLM as a single prompt or in multiple sequential prompts. In either case, the LLM has to process the whole codebase in a single context window and generate the knowledge base either in a single output or in multiple sequential outputs. 

Challenge: This is not feasible for large codebases that exceed the context window of the LLM. Even for small codebases, this approach is not efficient as the LLM has to process the whole codebase in a single context window, which can lead to hallucination, distraction, and loss of important information.

#### 1.2: Single Agent with Tool Use
In this approach, we use a single agent that can utilize external tools, such as read_file tool to read the codebase files one by one and generate the knowledge base incrementally. In this appraoch the agent can decide the order of reading the files based on its own strategy and generate the knowledge base accordingly. This is better than the previous approach because it allows for more flexibility and efficiency in processing the codebase, as the agent can focus on one file at a time and use its own judgment to determine the most relevant information to include in the knowledge base.

Challenge: However, this approach still has limitations. The single agent has to manage the entire process of reading the files, understanding the code, and generating the knowledge base, which can be overwhelming and lead to suboptimal results. The agent may also struggle to maintain context and coherence across multiple files, leading to a disjointed knowledge base. AND MOST IMPORTANTLY, again the agent has a context window limitation (context window limitaiton of LLM it uses). Whe the codebase is large, the agent cannot read ALL files even one by one because the cumulative context of all files read so far may exceed the context window of the LLM used by the agent.

### Option 2: Multi-Agent System
In this approach, we use multiple agents that can work together to read the codebase files and generate the knowledge base. Each agent can be responsible for a specific part of the codebase or a specific task, such as reading files, understanding code, or generating the knowledge base. The agents can communicate and collaborate with each other to achieve the overall goal of generating the knowledge base.
For example we can have a manager agent which coordinates the work of multiple worker agents. Each worker agent can be responsible for reading a specific directory or a set of files, understanding the code, and generating a part of the knowledge base. The manager agent can then collect the outputs from the worker agents and combine them to form the final knowledge base.
This solves the context window limitation of the previous approaches, as each agent can work within its own context window and focus on a specific part of the codebase.

Challenge: This approach is currenlty widely used and is feasible for large codebases. However in this case the challenegs are:
- Communication and coordination between agents can be complex and may lead to inefficiencies or errors.
- Whenever a worker agent finishes its task, it needs to communicate its results to the manager agent, again if the codebase is tool large, even a single worker agent may not be able to read all its assigned files within the context window limit of the LLM it uses. Also if we even increase the number of worker agents, these worker agents has to return their results to the manager agent, and the cumulative context of all results returned so far may exceed the context window of the LLM used by the manager agent.
- The most important challenge: before we start the process, we need to decide how many worker agents we need based on the size of the codebase. In multi-agent systems, the number of agents is fixed before the process starts. However, in our case, the size of the codebase may vary significantly, and we may not know in advance how many agents we need to effectively process the codebase. This can lead to either underutilization or overutilization of agents, resulting in inefficiencies and suboptimal results.
- Another minor challenge: the supervisor can delegate task to a single worker agent at a time. Usually it cannot assing task to multiple worker agents in parallel.

### Option 3: Sub-agents Architecture Methodology
In this approach, we use a single main agent (manager agent) that can dynamically create and manage sub-agents and runtime. Each sub-agent can be responsible for reading a specific file, understanding the code, and generating a part of the knowledge base. Each subagent is created at runtime by the main agent whenever needed and is destroyed after its task is completed. Each  subagent has its own memory, its own workspace, amnmd its own access to only an specific part of the codebase (for example a single directory) that is assigned to it by the main agent.

### Analogy of comparing multi-agent systems vs sub-agents architecture
To better understand the difference between multi-agent systems and sub-agents architecture, let's consider an analogy:
- Multi-agent system is like a company with multiple employees (agents) who have fixed roles and responsibilities. The number of employees is fixed, and they work together to achieve the company's goals. Whenever an employee finishes their task, they report back to the manager (supervisor agent) who oversees the entire operation. The manager has to review the results of the first employee before assigning the next task to another employee.
- Sub-agents architecture is like a freelance project where a project manager (main agent) hires freelancers (sub-agents) on demand to complete specific tasks. The project manager can hire as many freelancers as needed based on the project's requirements. Each freelancer works independently on their assigned task and delivers the results back to the project manager. Once the task is completed, the freelancer is no longer needed and can be let go.


### Wrap-up
The sub-agents architecture methodology combines the advantages of both previous approaches while mitigating their challenges. It allows for dynamic allocation of resources based on the size and complexity of the codebase, enabling efficient processing without being constrained by fixed numbers of agents or context window limitations. The main agent can create sub-agents as needed, allowing for parallel processing of files and better management of context and coherence across the knowledge base. This methodology is well-suited for generating a comprehensive and structured knowledge base from large and complex codebases.

a diagram of a main agent creating multiple sub-agents at runtime to read files from a codebase and generate a knowledge base:

```mermaid
graph TD
    A[Main Agent] --> B[Sub-Agent 1]
    A --> C[Sub-Agent 2]
    A --> D[Sub-Agent N]
    B --> E[Read File 1]
    C --> F[Read File 2]
    D --> G[Read File N]
    E --> H[Generate Part of Knowledge Base 1]
    F --> I[Generate Part of Knowledge Base 2]
    G --> J[Generate Part of Knowledge Base N]
    H --> K[Knowledge Base]
    I --> K
    J --> K
    style K fill:#f9f,stroke:#333,stroke-width:4px
```

please note that in this diagram the main agent dynamically creates multiple sub-agents at runtime to read files from the codebase and generate parts of the knowledge base. It is different form a multi-agent system (That I have already implemented in this codebase or is widely used in different frameworks) where the number of agents is fixed before the process starts. In multi-agent systems, the manager delegates a single task to a single worker agent at a time, whereas in sub-agents architecture, the main agent can create multiple sub-agents in parallel to work on different files simultaneously and write the results directly to a persistent memory( in our case the knowledge base) without needing to return the results to the main agent first.

below is a mermaid diagram showing a mutlti-agent system which uses supervisor architecture for comparison. here we show through numbers that the supervisor first delegates to worker 1, worker 1 returns results to supervisor, then supervisor delegates to worker 2, worker 2 returns results to supervisor, and so on. In contrast in sub-agents architecture, the main agent can create multiple sub-agents in parallel to work on different files simultaneously and write the results directly to a persistent memory( in our case the knowledge base) without needing to return the results to the main agent first.

```mermaid
graph TD
    A[Supervisor Agent] -->|1| B[Worker Agent 1]
    B --> C[Read File 1]
    C --> D[Generate Part of Knowledge Base 1]
    D --> E[Return Results to Supervisor]:::step1
    E --> A
    A -->|2| F[Worker Agent 2]
    F --> G[Read File 2]
    G --> H[Generate Part of Knowledge Base 2]
    H --> I[Return Results to Supervisor]:::step2
    I --> A
    A -->|3| J[Worker Agent N]
    J --> K[Read File N]
    K --> L[Generate Part of Knowledge Base N]
    L --> M[Return Results to Supervisor]:::step3
    M --> A
    classDef step1 fill:#f96,stroke:#333,stroke-width:2px
    classDef step2 fill:#6f9,stroke:#333,stroke-width:2px
    classDef step3 fill:#69f,stroke:#333,stroke-width:2px
```


## How to implement sub-agents
Please refer to the `docs/methodology_implementation.md` file for detailed instructions on how to implement the sub-agents architecture methodology in this project.