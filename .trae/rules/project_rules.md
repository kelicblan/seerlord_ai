# Project Rules: Python Backend & Vue3 Frontend

## Tech Stack Definition
- **Backend**: Python 3.10+, FastAPI (implied), LangChain, LangGraph.
- **Frontend**: Vue 3 (Composition API), Vite, markstream-vue(markstream插件，https://www.ai-elements-vue.com),Element Plus(ui组件,https://element-plus.org), TypeScript.
- **Data Exchange**: REST API, Streaming (SSE/Events).

## 1. Backend Rules (Python & LangGraph)
- **Type Hints**: MUST use Python type hints everywhere. Use `pydantic` for data validation.
- **Async/Await**: Prefer asynchronous implementation for I/O bound tasks.
- **LangGraph**: 
  - Define explicit `State` using `TypedDict` or Pydantic.
  - Nodes must be pure functions where possible.
  - Use `astream_events` for real-time feedback.
- **Logging**: Use structured logging (e.g., `loguru`). No `print()`.

## 2. Frontend Rules (Vue 3 + Element Plus)
- **Script Setup**: MUST use `<script setup lang="ts">`. NO Options API.
- **Element Plus**: 
  - Use auto-import for components.
  - Use `ElMessage` for notifications.
- **State Management**: Use specific `composables` (e.g., `useAgent.ts`) for business logic. Keep UI dumb.
- **Markdown**: Use a streaming-compatible markdown renderer for agent responses.

## 3. Integration & Directory Structure
- **API**: Backend returns structured JSON or standard SSE streams.
- **Folder Structure**:
  - `backend/app/agents`: Graph definitions.
  - `backend/app/tools`: Custom tools with Google-style docstrings.
  - `frontend/src/api`: Axios wrappers.
  - `frontend/src/views`: Page components.

## 4. Documentation Requirements
- Add a docstring to every Agent Node explaining its input/output state changes.
- If installing new packages, explicitly list them to be added to `requirements.txt` or `package.json`.