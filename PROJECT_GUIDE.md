# SeerLord AI 架构指南 (SeerLord AI Architecture Guide)

本文档详细介绍了 SeerLord AI 的架构设计、文件结构以及开发指南。
本项目旨在打造一个**世界级 (World-Class)** 的 AI Agent 平台，强调高可用性、健壮性和可扩展性。

## 1. 核心架构设计 (Architecture Design)

本项目采用 **"微内核 + 插件" (Micro-Kernel + Plugin)** 架构，结合 **LangGraph** 编排引擎，支持复杂的长运行任务和多 Agent 协作。

新增 **Skills (技能)** 系统，提供轻量级的 "Fast Track" (快速通道)，用于处理简单、明确的指令，绕过复杂的规划流程。

### 架构流程图 (Architecture Diagram)

```mermaid
graph TD
    Start([Start]) --> SkillRouter["Skill Router<br/>(快速意图识别)"]
    
    SkillRouter -->|Match Found| SkillExecutor["Skill Executor<br/>(快速执行)"]
    SkillExecutor --> End([End])
    
    SkillRouter -->|No Match| Planner["Planner Node<br/>(全局规划)"]
    
    Planner --> CheckApproval{"需人工审批?"}
    CheckApproval -- Yes --> HumanApproval["Human Approval<br/>(Interrupt Point)"]
    CheckApproval -- No --> Dispatcher
    
    HumanApproval --> Dispatcher["Dispatcher Node<br/>(任务分发)"]
    
    Dispatcher -->|Task Done| FinalAnswer["Final Answer<br/>(结果汇总)"]
    FinalAnswer --> End
    
    Dispatcher -->|Chitchat| ChitchatNode[Chitchat Node]
    ChitchatNode --> Progress
    
    Dispatcher -->|Plugin A| PluginA[Plugin: Tutorial Generator]
    Dispatcher -->|Plugin B| PluginB[Plugin: FTA Agent]
    Dispatcher -->|Plugin C| PluginC[Plugin: News Reporter]
    
    subgraph PluginExecution ["Plugin Execution"]
        PluginA --> Critic
        PluginB --> Critic
        PluginC --> Critic
    end
    
    Critic["Critic Node<br/>(结果评估/打分)"]
    
    Critic -->|Satisfied| Progress["Progress Node<br/>(Step + 1)"]
    Critic -->|Retry (Feedback)| Dispatcher
    Critic -->|Replan (Major Fail)| Planner
    
    Progress --> Dispatcher
```

### 核心组件

*   **Skills (技能系统) [New]**:
    *   位于 `server/skills/`。
    *   **职责**: 处理单一、明确的原子任务（如“计算”、“查时间”）。
    *   **特点**: **Fast Track**。不经过 Planner 和 Dispatcher，直接执行并返回，响应速度极快，Token 消耗低。
    *   **注册**: 通过 `server/kernel/skill_registry.py` 自动扫描加载。

*   **Micro-Kernel (微内核)**:
    *   位于 `server/kernel/`。
    *   **职责**: 提供基础设施，包括路由 (Router)、状态持久化 (Persistence)、插件加载 (Registry) 和 MCP 工具管理 (MCP Manager)。
    *   **原则**: 内核无业务逻辑，只负责调度和资源管理。
    *   **健壮性设计**:
        *   **Global Exception Handling**: 全局异常捕获，防止服务崩溃。
        *   **Connection Pooling**: 数据库连接池生命周期管理，支持自动重连。
        *   **Lazy Loading**: 插件和资源按需加载，加快启动速度。

*   **Plugins (插件)**:
    *   位于 `server/plugins/`。
    *   **职责**: 每个插件是一个独立的 Agent，拥有独立的 Graph 和 Tools。
    *   **隔离性**: 插件之间通过标准消息协议通信，互不影响。

*   **MCP Integration (Model Context Protocol)**:
    *   **MCP Manager**: 位于 `server/kernel/mcp_manager.py`。
    *   **功能**: 支持通过标准 MCP 协议连接外部工具和服务（如文件系统、GitHub、数据库等）。
    *   **特性**: 自动重试、超时控制、动态 Schema 转换。

*   **Orchestration (编排)**:
    *   **Master Graph**: 主路由图，负责意图识别和分发。
    *   **Router Node**: 基于 LLM 的智能路由器，支持降级策略 (Fallback) 和手动干预。

### 人工介入 (Human-in-the-loop)

系统支持在关键节点（如规划生成后）进行人工介入确认。

1.  **中断点 (Interrupt Point)**:
    *   Master Graph 在 `Planner` 生成非 Chitchat 类计划后，会自动中断。
    *   状态机停留在 `human_approval` 节点前。

2.  **API 交互**:
    *   前端检测到状态为 `interrupt`。
    *   用户审查 Plan。
    *   用户发送 `Command(resume=True)` 或更新状态。
    *   系统继续执行 `Dispatcher`。

### 数据流向

1.  **用户请求** -> **FastAPI** (Global Exception Handler & Middleware)
2.  **Master Graph** (Router) -> 分析意图 (带重试机制)
3.  **Human Review** (Conditional) -> 关键任务人工确认
4.  **Plugin Dispatch** -> 激活特定 Agent Graph
5.  **Tool Execution** -> 调用本地工具或 MCP 远程工具 (带超时保护)
6.  **State Persistence** -> 异步写入 PostgreSQL (Checkpointing)
7.  **响应** -> 流式返回 (SSE)

---

## 2. 文件结构 (File Structure)

```text
seerlord_ai/
├── server/
│   ├── core/
│   │   ├── config.py          # [配置] 强类型配置管理 (Pydantic Settings)
│   │   └── llm.py             # [LLM工厂] 支持超时、重试的 LLM 实例工厂
│   ├── kernel/                # [微内核]
│   │   ├── interface.py       # [接口] 插件标准接口
│   │   ├── registry.py        # [注册表] 插件自动发现
│   │   ├── skill_registry.py  # [技能注册表] Skills 自动发现
│   │   ├── master_graph.py    # [主图] 核心路由与编排
│   │   ├── mcp_manager.py     # [MCP] Model Context Protocol 管理器
│   │   └── persistence.py     # [持久化] 
│   ├── plugins/               # [插件库] (复杂 Agent)
│   │   ├── tutorial_generator/# [示例] 教程生成 Agent
│   │   ├── fta_agent/         # [示例] 故障分析 Agent
│   │   └── _example_agent/    # [模板] 标准开发模板 (不自动加载)
│   ├── skills/                # [技能库] (原子能力)
│   │   ├── calculator.py      # [示例] 计算器
│   │   └── current_time.py    # [示例] 当前时间
│   ├── static/                # [静态资源] Web 控制台
│   └── main.py                # [入口] FastAPI 应用，生命周期管理
├── mcp.json                   # [MCP配置] 外部工具服务器配置
├── pyproject.toml             # [依赖]
└── .env                       # [环境] 密钥与参数
```

---

## 3. 配置说明 (Configuration)

推荐使用 `.env` 文件管理敏感信息。系统启动时会自动校验关键配置。

### 关键配置项

*   **LLM 设置**:
    *   `LLM_PROVIDER`: `openai` 或 `ollama`
    *   `LLM_TIMEOUT`: 请求超时时间 (默认 30s)
    *   `LLM_MAX_RETRIES`: 最大重试次数 (默认 3)
    *   `OPENAI_API_KEY`: 必填 (如使用 OpenAI)

*   **数据库 (PostgreSQL)**:
    *   `DATABASE_URL`: 完整连接字符串 (优先)
    *   或者使用 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` 组合。
    *   **注意**: 若未配置数据库，系统将自动回退到**内存存储 (MemorySaver)**，重启后数据丢失。

*   **MCP (Model Context Protocol)**:
    *   在项目根目录创建 `mcp.json` 配置外部服务器。

示例 `.env`:
```ini
LLM_PROVIDER=openai
LLM_TIMEOUT=60
LLM_MAX_RETRIES=3
OPENAI_API_KEY=sk-xxxx
OPENAI_MODEL=gpt-4o

# 生产环境建议配置数据库
# DATABASE_URL=postgresql://user:pass@localhost:5432/seerlord
```

---

## 4. MCP 工具集成 (MCP Integration)

本项目完全支持 Model Context Protocol (MCP)。要添加外部工具：

1.  在根目录创建 `mcp.json`。
2.  配置服务器命令。

示例 `mcp.json`:
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\workspace"]
    },
    "git": {
      "command": "python",
      "args": ["path/to/git_server.py"]
    }
  }
}
```
系统启动时会自动连接这些服务器，并将工具动态注册到 Agent 可用的工具集中。

---

## 5. 开发指南 (Developer Guide)

### 增加一个新的 Agent Plugin

1.  **参考示例**: 项目包含一个完整的示例 Agent，位于 `app/plugins/_example_agent/`。
    *   该目录以 `_` 开头，因此**不会**在启动时自动加载。
    *   **使用方法**: 复制该文件夹并重命名（去掉 `_`），例如 `my_agent`。
    *   **全功能演示**: 该示例 (`ResearchAssistant`) 展示了：
        *   **Local Planner**: 任务拆解。
        *   **Tools**: 本地工具与 MCP 工具 (Search)。
        *   **Memory**: 长期记忆读写。
        *   **Critic**: 自我反思循环。
    *   该示例包含完整的目录结构、详细的中文注释、Schema定义、State管理以及反思 (Critic) 机制。

2.  **创建目录**: `app/plugins/my_agent/`

3.  **实现逻辑**:
    *   `graph.py`: 定义 StateGraph。
    *   `plugin.py`: 继承 `AgentPlugin`，返回编译后的 graph。
    *   `state.py`: 定义强类型 State。
    *   `schema.py`: 定义 Pydantic 模型用于结构化输出。

4.  **使用 MCP 工具**:
    *   在插件中导入 `app.kernel.mcp_manager.mcp_manager`。
    *   调用 `mcp_manager.get_tool("server_name", "tool_name")` 获取工具。

### 最佳实践 (Best Practices)

*   **错误处理**: 不要在 Node 中直接抛出未处理异常。捕获异常并返回包含错误信息的 State。
*   **超时控制**: LLM 调用和工具调用都已默认开启超时保护，但编写长时间运行的逻辑时仍需注意 checkpointer 的状态保存。
*   **类型安全**: 始终使用 Pydantic 模型定义 State 和 Tool Schema。

### Agent 设计模式：分层规划 (Hierarchical Planning)

**Q: Planner 可以在 Agent 中设定吗？**
**A: 可以，且非常推荐。**

SeerLord AI 采用分层规划架构：

1.  **Global Planner (全局规划器)**:
    *   位于 `app/kernel/master_graph.py`。
    *   **职责**: 宏观调度。识别用户意图，将任务分发给最合适的 Agent (Plugin)。
    *   **粒度**: 粗粒度（例如 "调用教程生成器"、"调用故障分析师"）。

2.  **Local Planner (本地规划器)**:
    *   位于各个 Agent 内部 (如 `app/plugins/_example_agent/graph.py`)。
    *   **职责**: 微观执行。将 Agent 接收到的特定任务拆解为具体的执行步骤（如 "搜索资料" -> "撰写大纲" -> "生成内容" -> "自我反思"）。
    *   **实现方式**: 在 Agent 的 Graph 中添加一个 `local_planner` 节点，使用 LLM 生成结构化的 `Plan` 对象。

**建议**:
对于复杂任务，**不要**依赖 Global Planner 完成所有细节规划。Global Planner 应该只负责 "找对人"，而 Agent 应该负责 "做对事"。请参考 `_example_agent` 中的 `local_planner_node` 实现。

---

## 6. 长期记忆 (Long-Term Memory)

本项目集成了 `pgvector`，支持基于语义搜索的长期记忆功能。

### 架构说明
*   **MemoryManager**: 位于 `app/kernel/memory_manager.py`。
*   **存储**: PostgreSQL `agent_memories` 表。
*   **索引**: 使用 IVFFlat 索引加速向量检索。

### 使用方法

在任何 Agent Plugin 中，都可以通过 `memory_manager` 存取记忆。

```python
from app.kernel.memory_manager import memory_manager

async def some_node(state):
    # 1. 检索相关记忆
    memories = await memory_manager.retrieve_relevant(query="用户之前的偏好")
    context = "\n".join([m["content"] for m in memories])
    
    # 2. 生成回答...
    response = "..."
    
    # 3. 保存新经验
    await memory_manager.save_experience(
        content=f"用户偏好: {user_preference}",
        metadata={"source": "chat", "topic": "preference"}
    )
```

### 配置要求
1.  **数据库**: PostgreSQL 必须安装 `vector` 扩展 (通常需超级用户权限安装: `CREATE EXTENSION vector;`)。
2.  **配置**: 在 `.env` 中设置 Embedding 模型。
    ```ini
    EMBEDDING_PROVIDER=openai
    EMBEDDING_MODEL=text-embedding-3-small
    EMBEDDING_DIM=1536
    ```

---

## 7. 快速启动 (Quick Start)

1.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    pip install loguru asyncpg psycopg2-binary langchain-ollama tenacity mcp
    ```

2.  **配置环境**:
    复制 `.env.example` 到 `.env` 并填入 Key。

3.  **运行服务**:
    *   **推荐方式 (兼容 Windows/Linux)**:
        ```bash
        python run_server.py
        ```
    *   **或者 (Linux/Mac)**:
        ```bash
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
        ```

4.  **验证**:
    访问 `http://localhost:8000/api/v1/health` 检查健康状态。
    访问 `http://localhost:8000` 使用 Web 控制台。

---

## 8. 故障排查 (Troubleshooting)

*   **Connection Refused (DB)**: 检查 PostgreSQL 是否启动。系统会自动降级到内存存储，但会有警告日志。
*   **MCP 连接失败**: 检查 `mcp.json` 中的命令路径是否绝对路径，或确保命令在 `PATH` 中。
*   **LLM Timeout**: 增加 `.env` 中的 `LLM_TIMEOUT` 值。
