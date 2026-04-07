<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import {
  ElCard,
  ElTable,
  ElTableColumn,
  ElButton,
  ElTag,
  ElMessage,
  ElMessageBox,
  ElSwitch,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElSelect,
  ElOption,
  ElInputNumber,
} from 'element-plus'
import {
  Plus,
  Edit,
  Delete,
} from '@element-plus/icons-vue'

interface RateLimitRule {
  id: string
  name: string
  endpoint: string
  method: string
  limitType: string
  limitCount: number
  windowSeconds: number
  enabled: boolean
  priority: number
  description: string
  createdAt: string
  hitCount: number
}

const tableData = ref<RateLimitRule[]>([])
const isLoading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')

const formData = reactive({
  name: '',
  endpoint: '',
  method: '',
  limitType: '',
  limitCount: 100,
  windowSeconds: 60,
  priority: 1,
  description: '',
})

const methodOptions = [
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
  { value: 'PUT', label: 'PUT' },
  { value: 'DELETE', label: 'DELETE' },
]

const limitTypeOptions = [
  { value: 'fixed', label: '固定窗口' },
  { value: 'sliding', label: '滑动窗口' },
  { value: 'token', label: '令牌桶' },
  { value: 'leaky', label: '漏桶' },
]

const fetchData = async () => {
  isLoading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    tableData.value = [
      {
        id: '1',
        name: '登录接口限流',
        endpoint: '/api/auth/login',
        method: 'POST',
        limitType: 'fixed',
        limitCount: 5,
        windowSeconds: 60,
        enabled: true,
        priority: 1,
        description: '登录接口每分钟最多5次',
        createdAt: '2024-01-15',
        hitCount: 1234,
      },
      {
        id: '2',
        name: '搜索接口限流',
        endpoint: '/api/search',
        method: 'GET',
        limitType: 'sliding',
        limitCount: 100,
        windowSeconds: 60,
        enabled: true,
        priority: 2,
        description: '搜索接口每分钟最多100次',
        createdAt: '2024-01-15',
        hitCount: 5678,
      },
      {
        id: '3',
        name: '文件上传限流',
        endpoint: '/api/upload',
        method: 'POST',
        limitType: 'token',
        limitCount: 10,
        windowSeconds: 60,
        enabled: false,
        priority: 3,
        description: '上传接口每分钟最多10次',
        createdAt: '2024-01-16',
        hitCount: 89,
      },
    ]
  } catch {
    ElMessage.error('获取数据失败')
  } finally {
    isLoading.value = false
  }
}

const handleAdd = () => {
  dialogTitle.value = '添加限流规则'
  Object.assign(formData, {
    name: '',
    endpoint: '',
    method: '',
    limitType: '',
    limitCount: 100,
    windowSeconds: 60,
    priority: 1,
    description: '',
  })
  dialogVisible.value = true
}

const handleEdit = (row: RateLimitRule) => {
  dialogTitle.value = '编辑限流规则'
  Object.assign(formData, row)
  dialogVisible.value = true
}

const handleDelete = async (row: RateLimitRule) => {
  try {
    await ElMessageBox.confirm(`确定要删除规则 "${row.name}" 吗？`, '提示', {
      type: 'warning',
    })
    ElMessage.success('删除成功')
    await fetchData()
  } catch {
    // User cancelled
  }
}

const handleToggle = (row: RateLimitRule) => {
  row.enabled = !row.enabled
  ElMessage.success(`${row.enabled ? '启用' : '禁用'}成功`)
}

const handleSave = async () => {
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await fetchData()
  } catch {
    ElMessage.error('保存失败')
  }
}

const getLimitTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    fixed: '固定窗口',
    sliding: '滑动窗口',
    token: '令牌桶',
    leaky: '漏桶',
  }
  return map[type] || type
}

const getMethodType = (method: string) => {
  const map: Record<string, 'success' | 'primary' | 'warning' | 'danger' | 'info'> = {
    GET: 'success',
    POST: 'primary',
    PUT: 'warning',
    DELETE: 'danger',
  }
  return map[method] || 'info'
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="rate-limit">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>接口访问限制</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon class="el-icon--left"><Plus /></el-icon>
            添加规则
          </el-button>
        </div>
      </template>

      <el-table v-loading="isLoading" :data="tableData" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="规则名称" min-width="150" />
        <el-table-column prop="endpoint" label="接口路径" min-width="180" />
        <el-table-column label="请求方法" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getMethodType(row.method)" size="small">
              {{ row.method }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="限流类型" width="120">
          <template #default="{ row }">
            {{ getLimitTypeLabel(row.limitType) }}
          </template>
        </el-table-column>
        <el-table-column label="限制次数" width="100" align="center">
          <template #default="{ row }">
            {{ row.limitCount }}/{{ row.windowSeconds }}秒
          </template>
        </el-table-column>
        <el-table-column prop="hitCount" label="命中次数" width="100" align="center" />
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="handleToggle(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="formData" label-width="100px">
        <el-form-item label="规则名称" required>
          <el-input v-model="formData.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="接口路径" required>
          <el-input v-model="formData.endpoint" placeholder="请输入接口路径" />
        </el-form-item>
        <el-form-item label="请求方法" required>
          <el-select v-model="formData.method" placeholder="请选择请求方法">
            <el-option
              v-for="item in methodOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="限流类型" required>
          <el-select v-model="formData.limitType" placeholder="请选择限流类型">
            <el-option
              v-for="item in limitTypeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="限制次数" required>
          <el-input-number v-model="formData.limitCount" :min="1" />
        </el-form-item>
        <el-form-item label="时间窗口(秒)" required>
          <el-input-number v-model="formData.windowSeconds" :min="1" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="formData.priority" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formData.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.rate-limit {
  padding: 0px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
