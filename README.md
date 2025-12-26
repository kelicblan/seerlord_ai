# SeerLord AI

[中文文档](README_zh.md) | **English**

> **SeerLord AI**: The next-generation modular AI agent orchestration platform based on micro-kernel architecture and LangGraph. It natively supports the MCP protocol and Human-in-the-loop collaboration, making complex agent development more stable and flexible.

## SeerLord AI: Redefining AI Agent Development Architecture

When building complex AI applications, we often face pain points such as severe code coupling, difficulty in extension, and chaotic state management. SeerLord AI was born to solve these problems.

As an **enterprise-grade AI Agent orchestration platform**, SeerLord AI adopts an advanced **"Micro-Kernel + Plugin"** architecture design. This means its core (Kernel) is only responsible for the most basic routing, memory management, and protocol adaptation, while all business capabilities (such as tutorial generation, real-time news, data analysis) are implemented through independent plugins. This design achieves true business isolation and plug-and-play capability.

## Why Choose SeerLord AI?

1. **Powerful Orchestration Capabilities**: Built on **LangGraph**, it natively supports complex graph-structured workflows (Graph Workflow), easily implementing advanced logic such as loops, branches, and fallbacks, rather than simple linear chains.
2. **Production-Grade Stability**: Fully asynchronous (Asyncio) backend design, with built-in database connection pool management and global exception circuit breaking mechanisms, ensuring robust operation in high-concurrency scenarios.
3. **Standardized Tool Ecosystem**: Fully integrates the **Model Context Protocol (MCP)**, making the connection between Agents and the external world (file systems, GitHub, databases) standardized and universal.
4. **Controllable Design**: Deeply integrates **Human-in-the-loop** mode. Agents can automatically pause during critical planning execution, waiting for human approval or correction, making every step of AI safe and controllable.
5. **Autonomous Evolutionary Skill Kernel (Voyager Agent)**: This is the **Core Highlight** of SeerLord AI. Unlike traditional agents with only preset generic capabilities, SeerLord integrates **Voyager Agent** as the foundational skill engine. It possesses the ability to **write code, self-correct, and accumulate/reuse skills**, enabling it to continuously learn new skills as tasks are executed, truly achieving "stronger with use."

## 🌟 Key Features

- **Dual-Mode Routing**: Supports both "Auto" intent recognition mode and "Manual" agent selection mode. Users can rely on AI for automatic planning or explicitly specify an Agent (e.g., Tutorial Agent) for deterministic execution.
- **Hierarchical Agent System**:
  - **Base Agent (Voyager Agent - The Core)**: The soul of the project. As a universal skill kernel, it empowers the system with autonomous learning and evolutionary capabilities. All other agents are built upon it, invoking its dynamically generated skills to solve specific problems.
  - **Business Agents**: e.g., `Tutorial Agent`, focused on domain-specific workflows. They do not reinvent the wheel but delegate to Voyager Agent for underlying capabilities, allowing them to focus on high-level logic.
- **Micro-Kernel Architecture**: A lightweight and stable core system responsible for lifecycle management, context sharing, and resource scheduling.
- **Skills Fast Track**: Provides a millisecond-level response execution path for simple commands (e.g., calculation, query), bypassing complex planning workflows.
- **Plugin System**: All business capabilities (such as news reporting, tutorial generation, financial analysis, etc.) are implemented via plugins, enabling plug-and-play functionality.
- **Agent Orchestration (LangGraph)**: Utilizes LangGraph to build complex stateful multi-agent workflows.
- **MCP Support**: Integrates the Model Context Protocol (MCP) for standardized context and tool interactions.
- **Dual-Engine Knowledge System**: Combines standard **RAG** (Vector-based with Qdrant) for efficient document retrieval and advanced **GraphRAG** (Graph-based with Neo4j) for deep entity relationship reasoning and hybrid search.
- **High-Performance Backend**: An asynchronous backend built with FastAPI, supporting SSE streaming responses.

## 🔌 Built-in Ecosystem

### Plugins (Agents)
SeerLord comes with a rich set of built-in plugins in `server/plugins/`:
- **Comic Book Generator**: Automatically generate comic strips from stories.
- **Data Analyst**: Analyze data and generate reports.
- **Deep Research**: Conduct in-depth research on complex topics.
- **Document Translator**: Translate documents while preserving formatting.
- **FTA Agent**: Fault Tree Analysis for system reliability engineering.
- **General Chat**: Standard conversational agent.
- **Novel Generator**: Assist in writing novels and creative stories.
- **Podcaster**: Generate podcast scripts and audio content.
- **PPT Generator**: Create presentation slides automatically.
- **Reasoning Engine**: Advanced reasoning capabilities for complex problems.

### MCP Services
Integrated MCP services in `mcp_services/` for extended capabilities:
- **Markdownify**: Convert web content to clean Markdown.
- **MDToFiles**: Split Markdown files into multiple files.
- **News**: Fetch and process real-time news updates.

## 🏗️ Architecture Flow

```mermaid
graph TD
    Start([Start]) --> CheckMode{"Manual Mode?"}
    
    CheckMode -- Yes --> Planner["Planner Node<br/>(Single Task Plan)"]
    CheckMode -- No --> SkillRouter["Skill Router<br/>(Fast Intent Recognition)"]
    
    SkillRouter -->|"Match Found"| SkillExecutor["Skill Executor<br/>(Fast Execution)"]
    SkillExecutor --> End([End])
    
    SkillRouter -->|"No Match"| Planner
    
    Planner --> CheckApproval{"Human Approval Needed?"}
    CheckApproval -- Yes --> HumanApproval["Human Approval<br/>(Interrupt Point)"]
    CheckApproval -- No --> Dispatcher
    
    HumanApproval --> Dispatcher["Dispatcher Node<br/>(Task Dispatching)"]
    
    Dispatcher -->|"Task Done"| FinalAnswer["Final Answer<br/>(Result Summary)"]
    FinalAnswer --> End
    
    Dispatcher -->|Chitchat| ChitchatNode[Chitchat Node]
    ChitchatNode --> Progress
    
    Dispatcher -->|"Plugin A"| PluginA[Plugin: Tutorial Generator]
    Dispatcher -->|"Plugin B"| PluginB[Plugin: FTA Agent]
    Dispatcher -->|"Plugin C"| PluginC[Plugin: News Reporter]
    
    subgraph PluginExecution ["Plugin Execution"]
        PluginA -.->|Delegate Skill| Voyager[Base: Voyager Agent]
        PluginA --> Critic
        PluginB --> Critic
        PluginC --> Critic
        Voyager --> Critic
    end
    
    Critic["Critic Node<br/>(Evaluation/Scoring)"]
    
    Critic -->|Satisfied| Progress["Progress Node<br/>(Step + 1)"]
    Critic -->|"Retry (Feedback)"| Dispatcher
    Critic -->|"Replan (Major Fail)"| Planner
    
    Progress --> Dispatcher
```

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **Frameworks**: FastAPI, LangChain, LangGraph
- **Database**: PostgreSQL (optional; for persistence/checkpoints)
- **Vector Store**: Qdrant (optional; for memory & skill retrieval & RAG)
- **Graph Database**: Neo4j (optional; for Knowledge Graph & GraphRAG)
- **Utilities**: Pydantic, Loguru, SSE-Starlette
- **Admin Console**: Vue 3 + Vite + TypeScript (in `admin/`)

## 📂 Directory Structure

```
seerlord_ai/
├── admin/              # Vue3 admin console (optional)
├── server/
│   ├── core/           # Core configuration & LLM wrappers
│   ├── kernel/         # Micro-kernel implementation (Registry, MCP Manager, Memory Manager)
│   ├── rag/            # RAG implementation (Qdrant-based document retrieval)
│   ├── ske/            # SeerLord Knowledge Engine (Neo4j-based GraphRAG)
│   ├── plugins/        # Plugins directory (contains various Agent implementations)
│   ├── skills/         # Skills directory (Fast Track atomic capabilities)
│   └── main.py         # Application entry point
├── mcp_services/       # MCP service implementations
├── scripts/            # Utility scripts
├── mcp.json            # MCP server configuration (loaded on startup if present)
└── pyproject.toml      # Project dependencies configuration
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 18+ (optional; for `admin/` and some MCP servers)
- PostgreSQL (optional; checkpoints & skill metadata)
- Qdrant (optional; vector memory & skill retrieval)
- Neo4j (optional; Knowledge Graph & GraphRAG)

### Installation

It is recommended to use Poetry or pip for installation.

```bash
# Install dependencies using pip
pip install -r requirements.txt
```

### Configuration

Copy the example environment variable file and modify the configuration:

```bash
cp .env.example .env
# Edit the .env file to configure your LLM provider and (optional) DB/Qdrant
```

Key notes:
- `LLM_PROVIDER` supports `openai` and `ollama` (OpenAI-compatible `/v1` endpoints are supported).
- If you do not configure DB, LangGraph will fall back to in-memory checkpoints.
- If you do not configure Qdrant, memory & vector-based skill retrieval will be disabled.
- If you do not configure Neo4j, Knowledge Graph & GraphRAG features will be unavailable.
- The API enforces `X-API-Key` (tenant key) on most `/api/*` and `/agent` routes; for local dev you can use `sk-admin-test` (see `server/api/auth.py`).

### Start the Service

```bash
# Start the backend service
python run.py
```

Alternative:
```bash
python -m server.main
```

### Health Check

- `GET http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

### First-Boot Admin User (Optional)

If you want to create the very first admin user (only works when the user table is empty):

1. Set `SETUP_TOKEN` in `.env`
2. Call:
   - `POST http://localhost:8000/api/v1/setup/initialize`
   - Header: `X-Setup-Token: <SETUP_TOKEN>`
   - Body: `{"username":"admin","password":"change_me_please"}`

### Admin Console (Optional)

```bash
cd admin
npm install
npm run dev
```

Set `VITE_API_URL` (and optionally `VITE_TENANT_API_KEY`) to point to your backend.

## 📄 License

This project is open-sourced under the [MIT License](LICENSE).

You are free to:
- ✅ Use it commercially
- ✅ Modify the code
- ✅ Distribute copies
- ✅ Use it privately

Just include the original license and copyright notice in any copy of the software/source.
