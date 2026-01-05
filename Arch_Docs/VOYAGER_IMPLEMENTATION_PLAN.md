# SeerLord AI: Voyager-style Embodied Agent Implementation Plan

This document outlines the roadmap to implement a **Voyager-like** autonomous learning architecture within SeerLord AI.
The goal is to enable the agent to autonomously propose tasks, generate executable code (skills), verify them, and persist them for future reuse.

## 1. Core Concept Mapping

| Voyager Component | SeerLord Implementation Strategy |
| :--- | :--- |
| **Skill Library** | **Dynamic Skill Manager** (backed by Qdrant). Unlike static `server/skills`, this will store code snippets and embeddings dynamically. |
| **Automatic Curriculum** | **Curriculum Agent (Plugin)**. A specialized planner node that proposes the "Next Best Task" based on the ultimate goal and current skill set. |
| **Iterative Prompting** | **Code-Verify-Refine Loop**. A sub-graph within the plugin that generates code, runs it in a sandbox, and refines it based on stderr/stdout. |

## 2. Architecture Changes

### Phase 1: Infrastructure (The "Brain" & "Hands")

#### 1.1 Dynamic Skill Manager (`server/kernel/dynamic_skills.py`)
Extend the current `SkillRegistry` or create a parallel system.
*   **Storage**: Use Qdrant (via `MemoryManager`) to store skills.
    *   **Vector**: Embedding of the docstring/function capability.
    *   **Payload**: `{ "name": "...", "code": "...", "requirements": [...] }`
*   **Retrieval**: `retrieve_skills(query: str, k: int)` returns relevant code snippets.
*   **Loading**: A safe runtime loader that can execute retrieved code strings into a specific namespace.

#### 1.2 Execution Sandbox (The "Environment")
Voyager operates in Minecraft. SeerLord needs a general computing environment.
*   **Initial**: Use a local Python REPL (via `langchain_experimental.utilities.PythonREPL`).
*   **Advanced**: Docker container or restricted process for safety.
*   **Interface**: `execute_code(code: str) -> (stdout, stderr, success)`.

### Phase 2: The Voyager Agent Plugin (`server/plugins/voyager_agent/`)

Create a new plugin `voyager_agent` with the following Graph structure:

```mermaid
graph TD
    Start --> Curriculum[Curriculum Manager<br/>(Propose Next Task)]
    Curriculum --> SkillRetrieval[Skill Retriever<br/>(Find relevant tools)]
    SkillRetrieval --> Coder[Action Agent<br/>(Write Code)]
    
    Coder --> Executor[Executor<br/>(Run Code)]
    Executor --> Critic{Verification}
    
    Critic -- "Success" --> SkillCommitter[Skill Committer<br/>(Save to Library)]
    SkillCommitter --> Curriculum
    
    Critic -- "Fail" --> ErrorAnalyzer[Error Analyzer]
    ErrorAnalyzer --> Coder
    
    Critic -- "Max Retries" --> Curriculum
```

#### Node Details:
1.  **Curriculum Manager**:
    *   Input: User Goal + Completed Tasks History.
    *   Output: A specific, small scope task (e.g., "Write a function to fetch stock data").
2.  **Skill Retriever**:
    *   Query Qdrant for top-5 relevant skills.
    *   Injects them into the context as "Reference Code".
3.  **Action Agent (Coder)**:
    *   Prompt: "You have these skills. Write a NEW function to solve <Current Task>. Use the provided skills if helpful."
4.  **Executor**:
    *   Runs the generated code.
5.  **Skill Committer**:
    *   Extracts the function body.
    *   Generates a clean docstring.
    *   Saves to Qdrant.

## 3. Implementation Roadmap

### Step 1: Dynamic Skill Store
- [ ] Create `server/kernel/dynamic_skill_manager.py`.
- [ ] Implement `add_skill()` and `search_skills()` using `MemoryManager`.

### Step 2: The Agent Logic
- [ ] Create `server/plugins/voyager_agent/`.
- [ ] Implement `graph.py` with the loop described above.
- [ ] Implement `prompts.py` (Crucial: Voyager's success relies heavily on "Code as Policy" prompts).

### Step 3: Integration
- [ ] Register `voyager_agent` in `server/kernel/registry.py`.
- [ ] Add a `CodeInterpreter` tool (Python REPL).

## 4. Example Scenario: "Analyze Microsoft Stock"

1.  **User**: "Analyze MSFT stock."
2.  **Curriculum**: "First, I need to get the stock price. Task: Create `get_stock_price(ticker)`."
3.  **Retriever**: (Empty initially).
4.  **Coder**: Writes python code using `yfinance` or `requests`.
5.  **Executor**: Runs `get_stock_price('MSFT')`.
    *   *Error*: `ModuleNotFoundError: No module named 'yfinance'`.
6.  **Critic**: "Install yfinance or use standard library."
7.  **Coder**: Rewrites to use `pip install` or `requests`.
8.  **Executor**: Success. Output: "400.00".
9.  **Committer**: Saves `get_stock_price` to Skill Library.
10. **Curriculum**: "Next, calculate moving average..." (Now it can reuse `get_stock_price`).
