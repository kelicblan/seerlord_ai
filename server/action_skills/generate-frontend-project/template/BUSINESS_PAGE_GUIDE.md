# 业务页面接入规范

本文档定义了在项目中新增业务页面的标准流程，确保 AI 和开发者遵循统一的规范。

---

## 一、涉及位置总览

新增一个业务页面需要修改以下 **5 个文件/目录**：

| 序号 | 位置 | 说明 |
|------|------|------|
| 1 | `src/views/模块名/` | 创建页面文件 |
| 2 | `src/api/modules/模块名.ts` | 定义接口 |
| 3 | `mock/index.ts` | 添加 Mock 接口 |
| 4 | `src/router/routes/模块名.ts` | 配置路由 |
| 5 | `src/router/routes/menu.ts` | 添加菜单 |

---

## 二、详细步骤

### 1. 创建页面文件

**目录结构**：
```
src/views/模块名/
├── 列表页面.vue          # 必选：列表页面
├── components/           # 组件目录
│   └── FormDialog.vue   # 必选：新增/编辑表单弹窗
└── index.ts              # 可选：统一导出
```

**示例**：新增「部门管理」页面

```
src/views/system/dept/
├── DeptList.vue          # 部门列表页面
└── components/
    └── FormDialog.vue   # 部门表单弹窗
```

**图标导入**（在对应 .ts 文件顶部）：
```typescript
import { OfficeBuilding } from '@element-plus/icons-vue'
```

**列表页面规范**（参考 [ListTemplate.vue](src/views/examples/ListTemplate.vue)）：

```vue
<template>
  <div class="dept-list-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>部门管理</span>
          <el-button type="primary" @click="handleCreate">新增</el-button>
        </div>
      </template>

      <!-- 搜索区域 -->
      <div class="search-bar">
        <el-form :inline="true" :model="searchForm">
          <el-form-item label="部门名称">
            <el-input v-model="searchForm.name" placeholder="请输入" clearable />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 表格组件 -->
      <el-table :data="tableData" v-loading="loading">
        <el-table-column prop="name" label="部门名称" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 表单弹窗 -->
    <FormDialog
      v-model="dialogVisible"
      :mode="formMode"
      :data="currentRowData"
      @success="handleFormSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FormDialog from './components/FormDialog.vue'
import {
  deptListApi,
  deptDetailApi,
  deptDeleteApi,
  type DeptItem
} from '@/api/modules/dept'

const loading = ref(false)
const dialogVisible = ref(false)
const formMode = ref<'create' | 'edit' | 'view'>('create')
const currentRowData = ref<Partial<DeptItem>>({})

const searchForm = reactive({ name: '' })
const tableData = ref<DeptItem[]>([])
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

// 获取数据
const fetchData = async () => {
  loading.value = true
  try {
    const res = await deptListApi({
      page: pagination.page,
      pageSize: pagination.pageSize,
      name: searchForm.name
    })
    // request.ts 拦截器已返回 payload.data，所以 res 已经是 { list, total, page, pageSize }
    tableData.value = res.list
    pagination.total = res.total
  } catch {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

// 查看详情
const handleView = async (row: DeptItem) => {
  formMode.value = 'view'
  try {
    const res = await deptDetailApi(row.id)
    currentRowData.value = res
  } catch {
    ElMessage.error('获取详情失败')
  }
  dialogVisible.value = true
}

// 新增
const handleCreate = () => {
  formMode.value = 'create'
  currentRowData.value = {}
  dialogVisible.value = true
}

// 编辑
const handleEdit = async (row: DeptItem) => {
  formMode.value = 'edit'
  try {
    const res = await deptDetailApi(row.id)
    currentRowData.value = res
  } catch {
    ElMessage.error('获取详情失败')
  }
  dialogVisible.value = true
}

// 删除
const handleDelete = (row: DeptItem) => {
  ElMessageBox.confirm(`确定删除 "${row.name}" 吗?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    await deptDeleteApi(row.id)
    ElMessage.success('删除成功')
    fetchData()
  }).catch(() => {})
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

// 重置
const handleReset = () => {
  searchForm.name = ''
  pagination.page = 1
  fetchData()
}

// 分页
const handleSizeChange = () => fetchData()
const handlePageChange = () => fetchData()

// 表单提交成功
const handleFormSuccess = () => {
  fetchData()
}

onMounted(() => fetchData())
</script>

<style scoped>
.dept-list-container {
  padding: 0px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-bar {
  margin-bottom: 16px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
```

---

### 2. 定义接口

**文件位置**：`src/api/modules/模块名.ts`

**示例**：`src/api/modules/dept.ts`

```typescript
import { get, post } from '@/api/request'

// ============ 类型定义 ============
export interface DeptItem {
  id: number
  name: string
  parentId: number
  sort: number
  status: number
  createTime: string
}

export interface DeptDetail extends DeptItem {
  children?: DeptItem[]
}

export interface DeptListParams {
  page?: number
  pageSize?: number
  name?: string
}

export interface DeptListResponse {
  list: DeptItem[]
  total: number
  page: number
  pageSize: number
}

export interface DeptFormData {
  id?: number
  name: string
  parentId?: number
  sort?: number
  status?: boolean
}

// ============ API 接口 ============

// 部门列表
export const deptListApi = (params: DeptListParams) =>
  get<DeptListResponse>('/dept/list', { params })

// 部门详情
export const deptDetailApi = (id: number) =>
  get<DeptDetail>('/dept/detail', { params: { id } })

// 新增部门
export const deptCreateApi = (data: DeptFormData) =>
  post<{ id: number }>('/dept/create', data)

// 更新部门
export const deptUpdateApi = (data: DeptFormData) =>
  post('/dept/update', data)

// 删除部门
export const deptDeleteApi = (id: number) =>
  post('/dept/delete', { id })
```

---

### 3. 配置路由

**文件位置**：`src/router/routes/模块名.ts`

**示例**：`src/router/routes/system.ts` 中添加

```typescript
{
  path: 'system/dept',
  name: 'system-dept',
  component: () => import('@/views/system/dept/DeptList.vue'),
  meta: {
    title: '部门管理',
    description: '组织部门管理',
    requiresAuth: true,
    permissions: ['system:dept:view'],  // 可选：权限标识
  },
},
```

**注意**：
- `path` 相对于父路由，避免重复
- `name` 保持唯一性，格式：`模块-页面`
- `permissions` 用于权限控制，可选

---

### 4. 添加菜单

**文件位置**：`src/router/routes/menu.ts`

```typescript
{
  title: '系统管理',
  items: [
    // ... 其他菜单
    {
      icon: OfficeBuilding,  // Element Plus 图标
      label: '部门管理',     // 菜单名称
      path: '/system/dept', // 路由路径
      permission: 'system:dept:view',  // 可选：对应路由权限
    },
  ],
},
```

**图标规范**：使用 `@element-plus/icons-vue` 中的图标
- `User` - 用户
- `Setting` - 设置
- `Key` - 权限
- `OfficeBuilding` - 部门
- `Document` - 文档
- `Clock` - 时间
- `Bell` - 通知
- `Tools` - 工具
- `FolderOpened` - 文件夹
- `Connection` - 连接
- `Warning` - 警告
- `Refresh` - 刷新
- `Odometer` - 仪表
- `DocumentDelete` - 删除文档

---

## 三、完整示例

### 新增「设备管理」页面

#### 1. 创建页面文件

```
src/views/device/
├── DeviceList.vue         # 列表页面
└── components/
    └── FormDialog.vue    # 表单弹窗
```

**DeviceList.vue**：
```vue
<template>
  <div class="device-list-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>设备管理</span>
          <el-button type="primary" @click="handleCreate">新增设备</el-button>
        </div>
      </template>

      <el-table :data="tableData" v-loading="loading">
        <el-table-column prop="name" label="设备名称" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
const loading = ref(false)
const tableData = ref([])

const fetchData = async () => {
  loading.value = true
  try {
    const res = await deviceListApi({ page: 1, pageSize: 10 })
    tableData.value = res.list
  } finally {
    loading.value = false
  }
}

const handleCreate = () => { /* 打开表单 */ }
const handleEdit = (row: any) => { /* 打开表单 */ }
const handleDelete = async (row: any) => { /* 删除确认 */ }

onMounted(() => fetchData())
</script>

<style scoped>
.device-list-container {
  padding: 0px;
}
</style>
```

#### 2. 创建接口文件

**src/api/modules/device.ts**：
```typescript
import { post, get } from '@/api/request'

export const deviceListApi = (params: any) =>
  get('/device/list', params)

export const deviceDetailApi = (id: number) =>
  get('/device/detail', { id })

export const deviceCreateApi = (data: any) =>
  post('/device/create', data)

export const deviceUpdateApi = (data: any) =>
  post('/device/update', data)

export const deviceDeleteApi = (id: number) =>
  post('/device/delete', { id })
```

#### 3. 添加路由

**在 `src/router/routes/` 的路由文件中添加**：

```typescript
{
  path: 'device',
  name: 'device',
  component: () => import('@/views/device/DeviceList.vue'),
  meta: {
    title: '设备管理',
    description: '设备信息管理',
    requiresAuth: true,
    permissions: ['device:view'],
  },
},
```

#### 4. 添加菜单

**src/router/routes/menu.ts**：

```typescript
// 需要先导入图标
import { Connection } from '@element-plus/icons-vue'

{
  title: '设备管理',
  items: [
    {
      icon: Connection,
      label: '设备列表',
      path: '/device',
      permission: 'device:view',
    },
  ],
},
```

#### 5. 添加 Mock 接口

**mock/index.ts** 中添加：

```typescript
{
  url: '/api/device/list',
  method: 'get',
  timeout: 500,
  response: ({ query }: { query: { page?: number; pageSize?: number } }) => {
    const page = Number(query?.page) || 1
    const pageSize = Number(query?.pageSize) || 10
    const allData = [
      { id: 1, name: '设备A', status: 1, location: '北京', createTime: '2024-01-15' },
      { id: 2, name: '设备B', status: 0, location: '上海', createTime: '2024-01-14' },
    ]
    const start = (page - 1) * pageSize
    return {
      code: 200,
      message: 'success',
      data: { list: allData.slice(start, start + pageSize), total: allData.length, page, pageSize },
    }
  },
},
{
  url: '/api/device/detail',
  method: 'get',
  response: ({ query }: { query: { id: number } }) => ({
    code: 200,
    message: 'success',
    data: { id: Number(query?.id), name: '设备A', status: 1, location: '北京', createTime: '2024-01-15' },
  }),
},
{
  url: '/api/device/create',
  method: 'post',
  response: ({ body }: { body: any }) => ({
    code: 200,
    message: '创建成功',
    data: { id: Math.floor(Math.random() * 10000), ...body },
  }),
},
{
  url: '/api/device/update',
  method: 'post',
  response: () => ({ code: 200, message: '更新成功', data: {} }),
},
{
  url: '/api/device/delete',
  method: 'post',
  response: () => ({ code: 200, message: '删除成功', data: {} }),
},
```

---

## 四、权限系统

### 用户角色

| 角色 | 说明 | 权限范围 |
|------|------|---------|
| `admin` | 管理员 | 所有权限 |
| `guest` | 访客 | 无需权限的页面 |

### 权限标识命名规范

格式：`模块:资源:操作`

示例：
- `system:user:view` - 查看用户
- `system:role:edit` - 编辑角色
- `device:manage` - 设备管理

### 无权限菜单隐藏

菜单项不设置 `permission` 字段表示无需权限，所有用户可见。

---

## 五、注意事项

1. **不要嵌套路由**：业务页面直接作为路由组件，不要套用额外的布局组件
2. **卡片样式**：使用 `<el-card shadow="never">` 并依赖全局样式
3. **列表页面**：参考 `examples/ListTemplate.vue` 的结构
4. **表单弹窗**：如需新增/编辑功能，参考 `examples/components/FormDialog.vue`
5. **图标选择**：使用 `@element-plus/icons-vue` 官方图标
6. **API 命名**：使用 `模块名 + 操作 + Api` 格式

---

## 六、Mock 接口规范

### 1. Mock 数据文件位置

**文件结构**：
```
mock/
├── index.ts          # 主入口，导出所有 mock 配置
└── data/             # Mock 数据目录（数据量大时拆分）
    ├── examples.ts   # 示例模块数据
    ├── device.ts    # 设备模块数据
    └── ...
```

**小型项目**：所有 mock 数据直接写在 `mock/index.ts` 中

**大型项目**：将数据拆分到 `mock/data/` 目录，按模块命名

### 2. 主入口文件

**文件位置**：`mock/index.ts`

**类型导入**：
```typescript
import type { MockMethod } from 'vite-plugin-mock'
import { examplesData } from './data/examples'
```

**导出格式**：
```typescript
export default [
  // auth 接口
  { url: '/api/auth/login', method: 'post', ... },
  // 导入模块数据
  ...examplesData,
] as MockMethod[]
```

### 3. 数据文件示例

**文件位置**：`mock/data/模块名.ts`

```typescript
import type { MockMethod } from 'vite-plugin-mock'

const allData = [
  { id: 1, name: '设备A', status: 1, location: '北京', createTime: '2024-01-15' },
  { id: 2, name: '设备B', status: 0, location: '上海', createTime: '2024-01-14' },
  { id: 3, name: '设备C', status: 1, location: '广州', createTime: '2024-01-13' },
]

export const deviceData: MockMethod[] = [
  {
    url: '/api/device/list',
    method: 'get',
    timeout: 500,
    response: ({ query }: { query: { page?: number; pageSize?: number } }) => {
      const page = Number(query?.page) || 1
      const pageSize = Number(query?.pageSize) || 10
      const start = (page - 1) * pageSize
      const data = allData.slice(start, start + pageSize)
      return {
        code: 200,
        message: 'success',
        data: { list: data, total: allData.length, page, pageSize },
      }
    },
  },
  {
    url: '/api/device/detail',
    method: 'get',
    response: ({ query }: { query: { id: number } }) => ({
      code: 200,
      message: 'success',
      data: allData.find(d => d.id === Number(query?.id)) || allData[0],
    }),
  },
]
```

### 4. vite 配置

确保 `vite.config.ts` 中已启用 mock：

```typescript
import { viteMockServe } from 'vite-plugin-mock'

export default defineConfig({
  plugins: [
    viteMockServe({
      mockPath: './mock',
      enable: true,
      localEnabled: true,
    }),
  ],
})
```

### 5. Mock 接口命名规范

| 接口类型 | URL 格式 | Method |
|---------|---------|--------|
| 列表 | `/api/模块/list` | GET |
| 详情 | `/api/模块/detail` | GET |
| 新增 | `/api/模块/create` | POST |
| 更新 | `/api/模块/update` | POST |
| 删除 | `/api/模块/delete` | POST |

### 6. 响应格式

```typescript
{
  code: 200,           // 状态码
  message: 'success',   // 消息
  data: { ... }         // 数据
}
```

### 7. 完整示例

**示例**：为「设备管理」添加 mock 接口

```typescript
import type { MockMethod } from 'vite-plugin-mock'

export default [
  {
    url: '/api/device/list',
    method: 'get',
    timeout: 500,
    response: ({ query }: { query: { page?: number; pageSize?: number; keyword?: string } }) => {
      const page = Number(query?.page) || 1
      const pageSize = Number(query?.pageSize) || 10

      const allData = [
        { id: 1, name: '设备A', status: 1, location: '北京', createTime: '2024-01-15' },
        { id: 2, name: '设备B', status: 0, location: '上海', createTime: '2024-01-14' },
        { id: 3, name: '设备C', status: 1, location: '广州', createTime: '2024-01-13' },
      ]

      // 支持关键字搜索
      let filteredData = allData
      if (query?.keyword) {
        filteredData = filteredData.filter(item => item.name.includes(query.keyword!))
      }

      // 分页
      const start = (page - 1) * pageSize
      const data = filteredData.slice(start, start + pageSize)

      return {
        code: 200,
        message: 'success',
        data: {
          list: data,
          total: filteredData.length,
          page,
          pageSize,
        },
      }
    },
  },
  {
    url: '/api/device/detail',
    method: 'get',
    timeout: 500,
    response: ({ query }: { query: { id: number } }) => {
      const detailData: Record<number, any> = {
        1: { id: 1, name: '设备A', status: 1, location: '北京', createTime: '2024-01-15', remark: '备注信息' },
        2: { id: 2, name: '设备B', status: 0, location: '上海', createTime: '2024-01-14', remark: '备注信息' },
      }
      const id = Number(query?.id)
      return {
        code: 200,
        message: 'success',
        data: detailData[id] || detailData[1],
      }
    },
  },
  {
    url: '/api/device/create',
    method: 'post',
    timeout: 500,
    response: ({ body }: { body: any }) => {
      return {
        code: 200,
        message: '创建成功',
        data: { id: Math.floor(Math.random() * 10000), ...body },
      }
    },
  },
  {
    url: '/api/device/update',
    method: 'post',
    timeout: 500,
    response: ({ body }: { body: any }) => {
      return {
        code: 200,
        message: '更新成功',
        data: body,
      }
    },
  },
  {
    url: '/api/device/delete',
    method: 'post',
    timeout: 500,
    response: ({ body }: { body: { id: number } }) => {
      return {
        code: 200,
        message: '删除成功',
        data: { id: body.id },
      }
    },
  },
] as MockMethod[]
```

### 8. Mock 数据特点

- **支持分页**：自动根据 page 和 pageSize 返回对应数据
- **支持搜索**：根据 keyword 参数过滤数据
- **模拟延迟**：设置 timeout 模拟真实网络请求
- **响应格式统一**：code、message、data 三字段

---

## 七、文件路径速查

| 用途 | 路径 |
|------|------|
| 页面文件 | `src/views/模块名/` |
| 接口定义 | `src/api/modules/模块名.ts` |
| Mock 接口入口 | `mock/index.ts` |
| Mock 数据文件 | `mock/data/模块名.ts` |
| 路由配置 | `src/router/routes/system.ts` |
| 菜单配置 | `src/router/routes/menu.ts` |
| 样式变量 | `src/style.css` |
| 全局样式 | `src/assets/styles/global.css` |
| 列表模板参考 | `src/views/examples/ListTemplate.vue` |
| 表单弹窗参考 | `src/views/examples/components/FormDialog.vue` |

---

## 八、常见问题

### 1. 修改 Mock 后不生效

修改 `mock/index.ts` 后需要**重启开发服务器**：
```bash
# Ctrl+C 停止
npm run dev
```

### 2. 切换到真实后端

修改 `.env` 文件：
```env
# 开发环境（使用 mock）
VITE_API_BASE_URL=/api

# 生产环境（使用真实后端）
VITE_API_BASE_URL=https://api.example.com
```

然后删除或注释 `vite.config.ts` 中的 mock 插件配置。

### 3. FormDialog.vue 表单组件模板

**文件位置**：`src/views/模块名/components/FormDialog.vue`

```vue
<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="600px"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px">
      <el-form-item label="名称" prop="name">
        <el-input v-model="formData.name" placeholder="请输入" />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-switch v-model="formData.status" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { deviceCreateApi, deviceUpdateApi } from '@/api/modules/device'

const props = defineProps<{
  visible: boolean
  mode: 'create' | 'edit' | 'view'
  data: Record<string, any>
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'success': []
}>()

const formRef = ref()
const submitting = ref(false)
const formData = ref({
  id: undefined as number | undefined,
  name: '',
  status: true,
})

const title = computed(() => ({
  create: '新增',
  edit: '编辑',
  view: '查看',
}[props.mode]))

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

watch(() => props.visible, (val) => {
  if (val && props.data) {
    formData.value = {
      id: props.data.id,
      name: props.data.name || '',
      status: props.data.status ?? true,
    }
  }
})

const handleClose = () => {
  emit('update:visible', false)
  formRef.value?.resetFields()
}

const handleSubmit = async () => {
  await formRef.value?.validate()
  submitting.value = true
  try {
    if (props.mode === 'create') {
      await deviceCreateApi(formData.value)
      ElMessage.success('创建成功')
    } else {
      await deviceUpdateApi(formData.value)
      ElMessage.success('更新成功')
    }
    emit('success')
    handleClose()
  } catch {
    // error
  } finally {
    submitting.value = false
  }
}
</script>
```

### 4. API 模块导入

在页面中使用 API 模块：

```typescript
import {
  deviceListApi,
  deviceDetailApi,
  deviceDeleteApi,
  type DeviceItem
} from '@/api/modules/device'
```

### 5. 数据流说明

```
用户操作 → 页面组件 → API 模块 → axios 请求 → Mock 拦截 → 返回数据
                                ↓
                          切换 baseURL → 真实后端接口
```

---

## 九、命名规范（重要！）

生成代码时必须严格遵循以下命名规范，**违反将导致 TypeScript 编译失败**！

### 9.1 文件命名

| 类型 | 规范 | ✅ 正确 | ❌ 错误 |
|------|------|---------|---------|
| Vue 页面 | PascalCase | `RateLimit.vue` | `rate-limit.vue` |
| 目录 | camelCase | `rateLimit/` | `rate-limit/` |
| API 模块 | camelCase | `rateLimit.ts` | `rate-limit.ts` |
| 类型定义 | PascalCase | `RateLimitItem` | `Rate-Limit-Item` |
| Mock 数据 | PascalCase | `rateLimitMock.ts` | `rate-limit-mock.ts` |

### 9.2 变量/函数命名

| 类型 | 规范 | ✅ 正确 | ❌ 错误 |
|------|------|---------|---------|
| 变量 | camelCase | `rateLimitList` | `rate-limit-list` |
| 函数 | camelCase | `getRateLimit` | `get-rate-limit` |
| 常量 | UPPER_SNAKE | `API_BASE_URL` | `api-base-url` |
| 类/接口 | PascalCase | `RateLimitItem` | `Rate-Limit-Item` |

### 9.3 路由和菜单

| 类型 | 规范 | ✅ 正确 | ❌ 错误 |
|------|------|---------|---------|
| 路由路径 | kebab-case（URL） | `/security/rate-limit` | - |
| 路由名称 | kebab-case | `security-rate-limit` | `security_rate_limit` |
| 菜单名称 | 中文或 camelCase | `rateLimit` 或 `限流配置` | `rate-limit` |

### 9.4 常见错误示例

**❌ 错误示例**：
```typescript
// 目录名包含连字符
src/views/security/rate-limit/

// 类型名包含连字符
export interface Rate-Limit-Item {
  id: number
}

// 变量名包含连字符
export const rate-limit-api = {}

// 导入包含连字符
import { Rate-Limit-Item } from '@/types/rate-limit'
```

**✅ 正确示例**：
```typescript
// 目录名使用 camelCase
src/views/security/rateLimit/

// 类型名使用 PascalCase
export interface RateLimitItem {
  id: number
}

// 变量名使用 camelCase
export const rateLimitApi = {}

// 导入使用 camelCase
import { RateLimitItem } from '@/types/rateLimit'
```

### 9.5 自动修复工具

如果代码中意外使用了连字符命名，系统会自动尝试修复：

1. **目录重命名**：`rate-limit/` → `rateLimit/`
2. **文件重命名**：`rateLimit.ts` → `rateLimit.ts`（无需修改）
3. **类型名修复**：`Rate-Limit-Item` → `RateLimitItem`
4. **导入路径修复**：更新所有引用路径

### 9.6 验证方法

构建前可以运行以下命令检查是否有连字符命名：

```bash
# 检查 views 目录
find src/views -name "*-*" -type d

# 检查 types 目录
find src/types -name "*-*" -type f

# 检查代码中的连字符标识符
grep -r "export const.*-.*" src/
grep -r "interface.*-.*" src/
```

---

## 十、vite.config.ts 配置说明

确保 mock 插件配置正确：

```typescript
import { viteMockServe } from 'vite-plugin-mock'

export default defineConfig({
  plugins: [
    viteMockServe({
      mockPath: './mock',
      enable: true,
      // 注意：vite-plugin-mock 3.x 版本已移除 localEnabled 参数
      // 如需控制 mock 开关，请使用 enable 参数
    }),
  ],
})
```

**⚠️ 重要**：`vite-plugin-mock` 版本 3.x 已移除 `localEnabled` 参数，使用 `enable` 参数来控制 mock 是否启用。
