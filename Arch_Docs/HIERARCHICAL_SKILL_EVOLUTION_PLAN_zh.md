# SeerLord AI: 分层进化技能系统设计 (Hierarchical Evolutionary Skill System)

本文档基于用户需求，设计了一套支持**多层级回退匹配**与**自主进化**的技能系统。
该系统旨在让 Agent 像人类专家一样，通过不断的实践（提问-回答-反馈），从具体案例中抽象出通用方法（归纳），又能利用通用方法解决新领域的具体问题（演绎）。

## 1. 核心理念

1.  **分层抽象 (Hierarchical Abstraction)**：技能不再是扁平的，而是树状结构的。
    *   **L1 具体技能 (Specific Skill)**：针对特定领域的硬编码或高度优化逻辑（如：`LearnEnglishSkill`）。
    *   **L2 领域技能 (Domain Skill)**：针对某一类问题的通用模版（如：`LanguageLearningSkill`）。
    *   **L3 元技能 (Meta Skill)**：最高层的认知策略（如：`GeneralLearningSkill`）。
2.  **动态回退 (Dynamic Fallback)**：匹配逻辑遵循“具体优先，向上回退”原则。
3.  **持续进化 (Continuous Evolution)**：每次交互不仅是消耗技能的过程，更是训练技能的过程。

## 2. 架构设计

### 2.1 技能数据结构 (Skill Schema)

我们需要重新定义 Skill 的存储结构（在 Qdrant/PostgreSQL 中）：

```json
{
  "id": "skill_uuid",
  "name": "learn_german_basic",
  "description": "基础德语学习助手",
  "level": 1, // 1=具体, 2=领域, 3=元
  "parent_id": "skill_language_learning_uuid", // 指向 L2 父节点
  "embedding": [...], // 向量化表示
  "content": {
    "prompt_template": "你是一位{language}老师...",
    "knowledge_base": ["德语语法基础", "常用问候语"],
    "code_logic": "def process(input): ..." // 可选的代码逻辑
  },
  "usage_stats": {
    "success_count": 10,
    "last_used": "2023-10-27"
  }
}
```

### 2.2 核心流程

#### A. 技能路由 (The Router) - "自底向上匹配"

当用户输入：“我想学习量子力学”

1.  **检索 (Retrieve)**：在向量库中搜索最相似的 Top-N 技能。
2.  **评估 (Evaluate)**：
    *   检查相似度是否超过阈值（例如 0.85）。
    *   **Case 1: 命中具体技能**（如已有 `LearnQuantumPhysics`）：直接调用。
    *   **Case 2: 未命中具体，命中领域技能**（如命中 `ScienceLearning`）：调用该领域技能，并传入特定参数（Subject="量子力学"）。
    *   **Case 3: 全未命中**：调用 L3 `GeneralLearningSkill`（学习类技能）。

#### B. 技能执行 (The Executor)

技能不再仅仅是代码，它是一个 **Agent**。
*   **L3 技能执行**：本质上是一个强大的 Prompt 工程师 Agent。它会分析用户的需求，动态生成解决策略。
*   **L2/L1 技能执行**：使用更固化的 Prompt 或代码，效率更高，效果更稳定。

#### C. 技能进化 (The Evolver) - "自顶向下派生" & "自底向上归纳"

这是一个在后台运行的 **异步 Agent**，在每次对话结束后触发。

**输入**：用户提问 + AI 回答 + 用户反馈（显式或隐式）+ 当前使用的技能 ID。

**逻辑分支**：

1.  **实例化 (Instantiation)**：
    *   **场景**：使用了 L2 `LanguageLearningSkill` 成功教了用户德语。
    *   **动作**：Evolver 发现“德语”是一个高频新词，于是基于 L2 的模板，固化一个新的 L1 技能 `LearnGermanSkill`。
    *   **结果**：下次用户问德语，直接命中 L1，响应更快更准。

2.  **优化 (Refinement)**：
    *   **场景**：使用了 L1 `LearnEnglishSkill`，但用户纠正了语法解释。
    *   **动作**：Evolver 提取纠正信息，更新 `LearnEnglishSkill` 的 Prompt 或知识库。

3.  **归纳 (Induction)**：
    *   **场景**：系统里有 `LearnPython` 和 `LearnJava`，Evolver 发现它们有很多相似的 Prompt 结构。
    *   **动作**：创建一个新的 L2 `CodingSkill`，作为它们的父级。

## 3. 实现计划

### Phase 1: 基础架构 (The Skeleton)
1.  **Skill Model**: 定义支持层级关系的 Pydantic 模型。
2.  **Vector Store**: 配置 Qdrant 以支持元数据过滤（Level, ParentID）。
3.  **Router**: 实现“回退匹配”逻辑。

### Phase 2: 预置种子技能 (The Seed)
1.  **L3 GeneralLearning**: 一个通用的学习方法论 Prompt（费曼学习法等）。
2.  **L2 LanguageLearning**: 语言学习的通用模版（词汇、语法、发音）。
3.  **L1 LearnEnglish**: 具体的英语教学配置。

### Phase 3: 进化 Agent (The Evolver)
1.  **Evolution Graph**: 一个专门的 LangGraph，用于分析对话历史并操作 Skill DB。
    *   Node 1: **Analysis** (这次交互发生了什么？)
    *   Node 2: **Decision** (需要新建、更新还是合并技能？)
    *   Node 3: **Action** (执行 DB 操作)

## 4. 示例演示

**用户**：“教我德语。”

1.  **Router**:
    *   搜 `LearnGerman` (L1) -> 无。
    *   搜 `LanguageLearning` (L2) -> 命中！
2.  **Executor**:
    *   加载 `LanguageLearning` 模版。
    *   填充变量 `target_language="German"`。
    *   生成回答。
3.  **Response**: "你好！学习德语的第一步是..."
4.  **Background Evolver**:
    *   观察到 `LanguageLearning` 被用于 "German" 且交互成功。
    *   **决定**：创建一个新的 L1 技能 `LearnGerman`，继承自 `LanguageLearning`，但预填充了德语特定的 Prompt。
    *   **保存**：写入数据库。

**用户 (次日)**：“教我德语。”

1.  **Router**:
    *   搜 `LearnGerman` (L1) -> **命中！** (直接使用优化过的专用技能)。

---

## 5. 项目代码落地 (SeerLord Context)

*   **Skill Schema**: `server/kernel/hierarchical_skills.py`
*   **Router**: 修改 `server/kernel/master_graph.py` 中的 `skill_router_node`。
*   **Evolver / Skill Manager**: 由 `server/plugins/voyager_agent/` (Voyager Agent) 承担。Voyager Agent 作为一个基础技能内核，负责实际的技能检索、动态生成与进化，其他业务 Agent (如 Tutorial Agent) 通过调用 Voyager 的能力来实现具体业务逻辑的技能增强。
