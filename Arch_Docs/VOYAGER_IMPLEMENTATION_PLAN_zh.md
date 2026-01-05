# SeerLord AI: Voyager 风格具身智能体实现计划

本文档概述了在 SeerLord AI 中实现 **类 Voyager** 自主学习架构的路线图。
目标是使 Agent 能够自主提出任务、生成可执行代码（技能）、验证这些技能，并将其持久化以供未来复用。

## 1. 核心概念映射

| Voyager 组件 | SeerLord 实现策略 |
| :--- | :--- |
| **技能库 (Skill Library)** | **动态技能管理器 (Dynamic Skill Manager)** (基于 Qdrant)。与静态的 `server/skills` 不同，它将动态存储代码片段和向量嵌入。 |
| **自动课程 (Automatic Curriculum)** | **课程 Agent (Plugin)**。一个专门的规划节点，根据最终目标和当前技能集提议“下一个最佳任务”。 |
| **迭代提示 (Iterative Prompting)** | **编码-验证-修正循环 (Code-Verify-Refine Loop)**。插件内的一个子图，负责生成代码、在沙箱中运行，并根据标准输出/错误输出进行修正。 |

## 2. 架构变更

### 第一阶段：基础设施 ("大脑" 与 "双手")

#### 1.1 动态技能管理器 (`server/kernel/dynamic_skills.py`)
扩展当前的 `SkillRegistry` 或创建一个并行系统。
*   **存储**：使用 Qdrant (通过 `MemoryManager`) 存储技能。
    *   **向量**：文档字符串/函数功能的 Embedding。
    *   **Payload**：`{ "name": "...", "code": "...", "requirements": [...] }`
*   **检索**：`retrieve_skills(query: str, k: int)` 返回相关的代码片段。
*   **加载**：一个安全的运行时加载器，可以将检索到的代码字符串执行到特定的命名空间中。

#### 1.2 执行沙箱 ("环境")
Voyager 在 Minecraft 中运行。SeerLord 需要一个通用计算环境。
*   **初始方案**：使用本地 Python REPL (通过 `langchain_experimental.utilities.PythonREPL`)。
*   **进阶方案**：Docker 容器或受限进程以保证安全。
*   **接口**：`execute_code(code: str) -> (stdout, stderr, success)`。

### 第二阶段：Voyager Agent 插件 (`server/plugins/voyager_agent/`)

创建一个新插件 `voyager_agent`，其图结构如下：

```mermaid
graph TD
    Start --> Curriculum[课程管理器<br/>(提议下一个任务)]
    Curriculum --> SkillRetrieval[技能检索器<br/>(查找相关工具)]
    SkillRetrieval --> Coder[行动 Agent<br/>(编写代码)]
    
    Coder --> Executor[执行器<br/>(运行代码)]
    Executor --> Critic{验证}
    
    Critic -- "成功" --> SkillCommitter[技能提交器<br/>(保存至库)]
    SkillCommitter --> Curriculum
    
    Critic -- "失败" --> ErrorAnalyzer[错误分析器]
    ErrorAnalyzer --> Coder
    
    Critic -- "达到最大重试次数" --> Curriculum
```

#### 节点详情：
1.  **课程管理器 (Curriculum Manager)**：
    *   输入：用户目标 + 已完成任务历史。
    *   输出：一个具体的、小范围的任务（例如，“编写一个获取股票数据的函数”）。
2.  **技能检索器 (Skill Retriever)**：
    *   在 Qdrant 中查询前 5 个相关技能。
    *   将它们作为“参考代码”注入上下文。
3.  **行动 Agent (Coder)**：
    *   Prompt：“你拥有这些技能。编写一个新的函数来解决 <当前任务>。如果有帮助，请使用提供的技能。”
4.  **执行器 (Executor)**：
    *   运行生成的代码。
5.  **技能提交器 (Skill Committer)**：
    *   提取函数体。
    *   生成清晰的文档字符串。
    *   保存到 Qdrant。

## 3. 实现路线图

### 步骤 1：动态技能存储
- [ ] 创建 `server/kernel/dynamic_skill_manager.py`。
- [ ] 使用 `MemoryManager` 实现 `add_skill()` 和 `search_skills()`。

### 步骤 2：Agent 逻辑
- [ ] 创建 `server/plugins/voyager_agent/`。
- [ ] 实现上述循环的 `graph.py`。
- [ ] 实现 `prompts.py`（关键：Voyager 的成功很大程度上依赖于“代码即策略”的提示词）。

### 步骤 3：集成
- [ ] 在 `server/kernel/registry.py` 中注册 `voyager_agent`。
- [ ] 添加 `CodeInterpreter` 工具 (Python REPL)。

## 4. 示例场景：“分析微软股票”

1.  **用户**：“分析 MSFT 股票。”
2.  **课程**：“首先，我需要获取股价。任务：创建 `get_stock_price(ticker)`。”
3.  **检索器**：（初始为空）。
4.  **Coder**：使用 `yfinance` 或 `requests` 编写 Python 代码。
5.  **执行器**：运行 `get_stock_price('MSFT')`。
    *   *错误*：`ModuleNotFoundError: No module named 'yfinance'`。
6.  **Critic**：“安装 yfinance 或使用标准库。”
7.  **Coder**：重写代码以使用 `pip install` 或 `requests`。
8.  **执行器**：成功。输出：“400.00”。
9.  **提交器**：将 `get_stock_price` 保存到技能库。
10. **课程**：“接下来，计算移动平均线...” （现在它可以复用 `get_stock_price`）。
