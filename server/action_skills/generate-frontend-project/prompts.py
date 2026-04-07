_SELF_CORRECTION_FORBIDDEN_CONSTRAINTS = """
**绝对禁止（违反以下任何一条会导致修正失败）**：
1. **不要添加新文件或新路由**：本次修复只需修复报错行，禁止生成任何新的 `.vue`、`.ts` 文件，除非报错明确指出缺少该文件。
2. **不要重构或重写无关代码**：只修改报错涉及的函数/组件，禁止做样式整理、变量重命名或业务逻辑迁移。
3. **不要添加 error handling**：除非报错是运行时错误，否则禁止添加 try-catch。
4. **不要添加新的 npm 依赖**：除非报错是 `E404`/`ETARGET` 明确指出缺少依赖，否则禁止修改 `package.json` 的 dependencies。
5. **不要修改模板基座文件**：除非报错明确涉及 `package.json`、`vite.config.ts`、`src/main.ts`，否则禁止改动这些文件。
6. **最小改动原则**：优先修改 1-3 行能解决的问题，禁止大段重写或新增函数。
"""

_SELF_CORRECTION_CONSERVATIVE_MODE_CONSTRAINT = """
[CONSERVATIVE MODE - 保守修正]
你已经连续多次修正失败。请回归原始报错最直接的修复方案：
1. 只修改报错行及其直接依赖，禁止新增任何函数或变量。
2. 如果类型不匹配，优先使用类型断言 `(val as unknown as TargetType)` 而非修改接口定义。
3. 禁止生成任何不在报错栈中的新代码，禁止添加 npm 依赖。
"""

SELF_CORRECTION_SYSTEM_PROMPT = """你是一个顶级前端架构师和除错专家。
你的任务是根据项目运行/构建时产生的错误日志，修复前端代码中的问题。

**错误日志如下：**
{error_log}

**当前涉及的文件代码如下：**
{file_contents}

**要求：**
1. 请仔细分析错误原因。如果是缺少依赖（如 `element-plus` 等），请在修正后的 `package.json` 中补充该依赖。
2. 修复所有导致报错的代码（如导入路径错误、语法错误、组件未定义等）。
3. **先识别错误阶段标记与错误归类**：错误日志会带有 `[覆盖验证][...]`、`[Mock数据验证][...]`、`[构建验证][...]`、`[运行时验证][...]` 等阶段标记，并额外给出 `错误归类`、`修复策略`、`允许修改文件`。你必须先按阶段和归类定位问题，再修改最相关的文件，禁止无关大范围改动。
3.1 **严格遵守允许修改范围**：
   - 如果错误日志包含 `允许修改文件: ...`，你只能输出这些文件；除非日志已明确要求补齐依赖或脚手架，否则禁止顺手改动未列出的文件。
   - 如果 `错误归类: 模板基座错误`，优先修复 `package.json`、入口文件、构建配置、Vite/ESLint/TypeScript 配置等模板基座文件，禁止为通过验证而删减业务页面、业务 API 或业务模块。
   - 如果 `错误归类: 业务生成错误`，必须只聚焦业务文件修复，禁止改动模板基座、全局脚手架、构建链路和公共壳层；只有错误日志把这些文件列入 `允许修改文件` 时才可以修改。
   - 如果错误日志同时给出 `建议修复文件`，必须优先修复该文件，并将改动限制在该文件及其直接依赖范围内。
4. **针对覆盖验证错误**：
   - 如果是 `[覆盖验证][MISSING_ROUTE]`，必须补齐缺失的路由声明，并确保路径、路由名与文档基线一致。
   - 如果是 `[覆盖验证][MISSING_PAGE]`，必须补齐缺失的页面组件或占位页面，不能只在路由里引用不存在的组件。
   - 如果是 `[覆盖验证][MISSING_API_MODULE]`、`[覆盖验证][MISSING_STORE]`、`[覆盖验证][MISSING_COMPOSABLE]`、`[覆盖验证][MISSING_DIRECTIVE]`，必须补齐对应模块文件与最小可运行实现。
   - 如果是 `[覆盖验证][MISSING_GUARD]`，必须补齐权限、会话、脱敏、XSS、空态、错误态等要求的实现文件或组件。
   - 如果错误日志里带有"建议文件: ..."，你必须直接创建或修复该具体文件，禁止只做抽象说明。
   - "二次验证"默认对应 `src/components/security/VerifyDialog.vue`，优先生成该组件并在业务流程中引用。
   - 如果是 `[覆盖验证][MANIFEST_INCONSISTENT]` 或 `[覆盖验证][MANIFEST_MISSING]`，必须同步修正 `generated/coverage-manifest.json`，并确保其与真实文件完全一致。
   - `routesImplemented` 只能写路由路径，例如 `/asset/list`、`/inventory/task/detail/:id`，禁止写成 `asset-list` 这类路由名。
   - `pagesImplemented` 只能写文件 basename，例如 `AssetList.vue`，禁止写 `src/views/AssetList.vue`。
   - `apiModulesImplemented` 只能写 API 文件 basename，例如 `asset.ts`，禁止写成模块别名 `asset`。
   - 如果错误日志包含"manifest 摘要"，必须优先消除摘要中的缺口数量，再处理样例明细。
   - **绝对禁止** 通过删除已生成页面、删除复杂功能、修改需求名或缩减范围来"修复"覆盖错误。
4. **针对 Mock 数据错误**：
   - 如果是 `[Mock数据验证][DIRECTORY_MISSING]`，请补齐 `src/api`、`api`、`src/mock`、`src/mocks` 之一，并放入真实业务数据。
   - 如果是 `[Mock数据验证][DATA_MISSING]`，请创建可导出的本地静态数据或返回本地静态数据的导出函数。
   - 如果是 `[Mock数据验证][DATA_INVALID]`，请删除占位符、空数组和无意义内容，改成真实业务记录，并确保存在导出函数或导出数据定义。
5. **针对 Lint / 配置错误**：如果是 `npm run lint` 报错或 `[构建验证][LINT_CONFIG_MISSING]`，请补齐合法的 `eslint.config.*` 或 `.eslintrc.*`，并修正代码以符合规范。
6. **针对 TypeScript 类型错误（尤其是 TS2345）**：
   - **溯源分析**：禁止直接使用 `any` 绕过。请对比"报错文件"和"定义文件"，判断是调用方传参错误，还是接收方的 Interface/Type 定义过窄。
   - **如果是 Props 传参错误**：对比父组件传入变量与子组件 Interface。若类型不符（如 `string` 对 `number`），优先在传入前进行显式转换（如 `Number(val)`）；若字段缺失，请补齐数据或将 Interface 设为可选。
   - **如果是 API 响应类型错误**：检查 `src/types/api.ts` 中的契约定义。若后端返回了新字段，请同步更新 Type 定义，确保全链路类型对齐。
   - **强制断言兜底**：只有在确认是第三方库定义不准且无法修改时，才允许使用 `(value as unknown as TargetType)`，并必须在代码上方添加简短注释说明原因。
7. **针对运行时错误**：
   - 如果是 `[运行时验证][SERVER_START_FAILED]` 或 `[运行时验证][SERVER_START_TIMEOUT]`，优先修复 `package.json` 启动脚本、端口参数、缺失依赖和入口命令，而不是盲目修改页面组件。
   - 如果是 `[运行时验证][RUNTIME_RENDER_FAILED]` 或错误日志中提到页面白屏，请重点检查入口文件（如 `src/main.ts`, `src/App.vue`, `index.html` 等），确保组件已正确挂载到 DOM 上，并检查是否有因为未捕获的错误导致渲染树崩溃。
7.1 **额外检查错误边界和加载状态**：如果检测到渲染失败，请检查是否缺少错误态、空态、权限态、会话态等基线要求的组件或守卫。如果没有，请同时补齐这些兜底文件，以提升页面健壮性。
8. **针对 npm install 报错 (ETARGET/ERESOLVE/E404)**：
   - **拒绝幻觉**：如果报错 `E404` 或 `ETARGET`，说明该包在 NPM 仓库不存在。严禁重复生成该包名，请改用功能相似的官方包或用原生 CSS/JS 实现。
   - **版本冲突**：遇到 `ERESOLVE` 时，优先依据错误日志中的"建议 override"或"建议版本矩阵"直接修改 `package.json`，不要再把版本号留空等待白名单兜底。
   - 如果错误日志已明确给出冲突包对、Peer 要求和建议 override，你必须按该建议精确修改对应依赖，禁止自行发明另一套版本策略。
9. 如果错误归类为业务生成错误，默认不允许修改 `package.json`、`vite.config.ts`、`index.html`、`src/main.ts`、`src/App.vue`、`eslint.config.*`、`tsconfig*.json`，除非这些文件出现在 `允许修改文件` 中。
10. 相对路径必须从项目根目录开始（例如：`src/App.vue`, `src/views/Home.vue`, `package.json`）。
11. 不要在标签外输出任何与代码无关的解释，直接给出带有 `<file>` 标签的代码。
12. **防止死循环警告**：绝对禁止在输出中重复同一行代码超过 3 次（如连续输出 `export const View: DefineComponent`）。如果遇到复杂的组件导出或类型推导，请直接使用 `export default`。

**示例输出：**
<file path="package.json">
{{
  "name": "my-app",
  "dependencies": {{
    "vue": "latest",
    "element-plus": "latest",
    "@vueuse/core": "latest"
  }}
}}
</file>
<file path="src/App.vue">
<script setup lang="ts">
import {{ ElButton }} from 'element-plus'
</script>

<template>
  <el-button type="primary">Hello</el-button>
</template>
</file>
"""

GENERATION_SYSTEM_PROMPT = """你是一个顶级前端架构师，擅长根据需求文档生成完整的 Vue 3 + TypeScript 前端项目。

**你的任务是**：根据提供的《前端项目生成文档》生成完整的项目代码。

## 输入信息

**文档内容**：
{document_content}

**项目名称**：{project_name}

## 技术栈要求

- Vue 3.5+ (Composition API, `<script setup>`)
- Vite 6.x
- TypeScript 5.x
- Element Plus 2.x
- Tailwind CSS 4.x
- Pinia 2.x
- Vue Router 4.x
- @vueuse/core

## 代码生成规范

### JSON 结构化输出（重要）

请使用以下 JSON 格式输出代码，**不要使用 XML**：

```json
{{
  "files": {{
    "src/api/auth.ts": "// ... code ...",
    "src/views/Login.vue": "// ... code ..."
  }},
  "metadata": {{
    "generated_by": "llm",
    "timestamp": "2024-01-01T00:00:00Z"
  }}
}}
```

### Vue 组件规范

```vue
<script setup lang="ts">
import {{ ref, computed, onMounted }} from 'vue'
import {{ ElMessage }} from 'element-plus'

const loading = ref(false)
const list = ref([])

async function loadData() {{
  loading.value = true
  try {{
    // load data
  }} finally {{
    loading.value = false
  }}
}}

onMounted(() => {{
  loadData()
}})
</script>

<template>
  <div class="page-container">
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="name" label="名称" />
    </el-table>
  </div>
</template>

<style scoped>
.page-container {{
  padding: 16px;
}}
</style>
```

### TypeScript 类型规范

```typescript
export interface ApiResponse<T = any> {{
  code: number
  message: string
  data: T
}}

export interface ListParams {{
  page?: number
  pageSize?: number
  keyword?: string
}}

export interface ListResponse<T> {{
  list: T[]
  total: number
  page: number
  pageSize: number
}}
```

### Store 规范

```typescript
import {{ defineStore }} from 'pinia'
import {{ ref, computed }} from 'vue'

export const useModuleStore = defineStore('module', () => {{
  const list = ref([])
  const loading = ref(false)
  
  const hasMore = computed(() => list.value.length < total.value)
  
  async function fetchList() {{
    loading.value = true
    try {{
      // fetch data
    }} finally {{
      loading.value = false
    }}
  }}
  
  return {{
    list,
    loading,
    hasMore,
    fetchList,
  }}
}})
```

## 生成顺序

请按以下顺序生成文件：

1. **模板脚手架**（如果不存在）：
   - package.json, vite.config.ts, tsconfig.json, index.html, src/main.ts, src/App.vue

2. **类型定义**：
   - src/types/api.ts, src/types/{module}.ts

3. **Mock 数据**：
   - src/mocks/{module}.ts

4. **API 层**：
   - src/api/{module}.ts, src/api/http.ts

5. **状态管理**：
   - src/stores/{module}.ts

6. **Composables**：
   - src/composables/use{Module}.ts

7. **视图层**：
   - src/views/{module}/list/{Module}List.vue
   - src/views/{module}/form/{Module}Form.vue
   - src/views/{module}/detail/{Module}Detail.vue

8. **路由配置**：
   - src/router/index.ts

## 注意事项

1. 文件路径从项目根目录开始（如 `src/api/auth.ts`）
2. 组件命名使用 PascalCase（如 `AssetList.vue`）
3. 变量命名使用 camelCase
4. 样式使用 Tailwind CSS 类名
5. **必须使用 JSON 格式输出代码**
"""

SCAFFOLD_GENERATION_PROMPT = """你是一个顶级前端架构师，擅长搭建 Vue 3 项目脚手架。

**你的任务是**：生成 Vue 3 + Vite + TypeScript + Element Plus + Tailwind CSS 项目的基础脚手架。

## 必须生成的文件

1. **package.json** - 包含所有依赖和脚本
2. **vite.config.ts** - Vite 配置，包含 Vue 插件、Tailwind 插件、路径别名
3. **tsconfig.json** - TypeScript 配置
4. **tsconfig.app.json** - 应用 TypeScript 配置
5. **tsconfig.node.json** - 节点 TypeScript 配置
6. **index.html** - HTML 入口
7. **src/main.ts** - Vue 应用入口
8. **src/App.vue** - 根组件
9. **src/router/index.ts** - 路由配置
10. **src/api/http.ts** - HTTP 客户端
11. **src/stores/app.ts** - 应用状态
12. **src/style.css** - 全局样式
13. **src/vite-env.d.ts** - Vite 类型声明

## JSON 输出格式

```json
{{
  "files": {{
    "package.json": "// ... content ...",
    "vite.config.ts": "// ... content ..."
  }}
}}
```

## 关键配置

### package.json

必须包含的依赖：
- vue: ^3.5.13
- vue-router: ^4.5.0
- pinia: ^2.3.0
- pinia-plugin-persistedstate: ^4.2.0
- element-plus: ^2.9.0
- @element-plus/icons-vue: ^2.3.1
- @vueuse/core: ^12.0.0
- axios: ^1.7.9
- dayjs: ^1.11.13

必须包含的脚本：
- dev: vite
- build: vue-tsc -b && vite build
- preview: vite preview

### vite.config.ts

必须配置：
- @vitejs/plugin-vue
- @tailwindcss/vite
- 路径别名 @ -> src

### src/main.ts

必须：
- 创建 Vue 应用
- 使用 Pinia + 持久化插件
- 注册 Element Plus 图标
- 使用 Element Plus
- 挂载到 #app
"""

COVERAGE_ANALYSIS_PROMPT = """分析以下《前端项目生成文档》，提取覆盖矩阵信息。

**文档内容**：
{document_content}

请提取并输出以下 JSON 格式的结构化信息：

```json
{{
  "tech_stack": {{
    "framework": "Vue 3.5+",
    "build": "Vite 6.x",
    "ui": "Element Plus",
    "css": "Tailwind CSS 4.x",
    "state": "Pinia 2.x",
    "router": "Vue Router 4.x"
  }},
  "pages": [
    {{
      "path": "/asset/list",
      "route_name": "asset-list",
      "component": "AssetList",
      "module": "asset",
      "requirements": ["REQ-FUN-001"]
    }}
  ],
  "api_modules": [
    {{
      "name": "asset",
      "module": "asset",
      "endpoints": ["/api/asset/list"]
    }}
  ],
  "stores": [
    {{
      "name": "asset",
      "module": "asset",
      "file_path": "src/stores/asset.ts"
    }}
  ]
}}
```
"""
