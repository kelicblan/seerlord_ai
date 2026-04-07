# Generate Frontend Project Skill

## 描述

根据《前端项目生成文档》生成完整的 Vue 3 前端项目。

## 输入

- `document_content`: 《前端项目生成文档》内容
- `project_name`: 项目名称
- `options`: 生成选项

## 输出

- `project_path`: 生成的项目路径
- `summary`: 生成摘要

## 工作流程

1. **分析文档**: 解析《前端项目生成文档》，提取技术栈、覆盖矩阵、业务模块
2. **制定计划**: 分析模块依赖，生成按依赖排序的模块计划
3. **生成基础设施**: 复制项目模板，生成 package.json、vite.config.ts、tsconfig.json 等
4. **生成类型定义**: 生成 API 类型契约和模块专用类型
5. **生成 Mock 数据**: 生成模拟数据文件
6. **生成 API 层**: 生成 src/api/ 模块文件
7. **生成业务逻辑**: 生成 Composables 和 Stores
8. **生成视图层**: 生成页面组件和路由
9. **验证检查**: 验证项目结构和可运行性
10. **返回结果**: 返回项目路径和生成摘要

## 代码生成规范

- 使用 **JSON 结构化输出**（不使用 XML）
- 遵循 Vue 3 Composition API (`<script setup lang="ts">`)
- 使用 TypeScript
- 使用 Element Plus 组件
- 使用 Tailwind CSS 进行样式

## JSON 输出格式

```json
{
  "files": {
    "src/api/auth.ts": "...",
    "src/views/Login.vue": "..."
  },
  "metadata": {
    "generated_by": "llm",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## 代码规范

### Vue 组件规范

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const list = ref([])

async function loadData() {
  loading.value = true
  try {
    // load data
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="page-container">
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="name" label="名称" />
    </el-table>
  </div>
</template>

<style scoped>
.page-container {
  padding: 16px;
}
</style>
```

### TypeScript 类型规范

```typescript
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface ListParams {
  page?: number
  pageSize?: number
  keyword?: string
}

export interface ListResponse<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}
```

### Store 规范

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useModuleStore = defineStore('module', () => {
  const list = ref([])
  const loading = ref(false)
  
  const hasMore = computed(() => list.value.length < total.value)
  
  async function fetchList() {
    loading.value = true
    try {
      // fetch data
    } finally {
      loading.value = false
    }
  }
  
  return {
    list,
    loading,
    hasMore,
    fetchList,
  }
})
```

## 错误处理

遇到错误时，返回结构化的错误信息：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid document format",
    "details": {
      "missing_fields": ["tech_stack", "coverage_matrix"]
    }
  }
}
```

## 知识库

生成过程中可查询知识库获取：
- 相似错误的已知解决方案
- 匹配技术栈的项目模板
- 特定任务类型的生成技巧

## 注意事项

1. 始终使用 JSON 结构化输出，不要使用 XML
2. 文件路径从项目根目录开始（如 `src/api/auth.ts`）
3. 遵循 Vue 3 Composition API 规范
4. 组件命名使用 PascalCase（如 `AssetList.vue`）
5. 变量命名使用 camelCase
6. 样式使用 Tailwind CSS 类名
