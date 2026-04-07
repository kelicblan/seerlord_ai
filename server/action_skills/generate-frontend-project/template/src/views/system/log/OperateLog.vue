<template>
  <div class="operate-log-container">
    <el-card shadow="never">
      <template #header>
        <span>操作日志</span>
      </template>

      <div class="search-bar">
        <el-form :inline="true" :model="searchForm">
          <el-form-item label="操作人">
            <el-input v-model="searchForm.operator" placeholder="请输入操作人" clearable />
          </el-form-item>
          <el-form-item label="操作类型">
            <el-select v-model="searchForm.action" placeholder="请选择" clearable>
              <el-option label="新增" value="create" />
              <el-option label="编辑" value="update" />
              <el-option label="删除" value="delete" />
              <el-option label="查询" value="query" />
            </el-select>
          </el-form-item>
          <el-form-item label="操作时间">
            <el-date-picker
              v-model="searchForm.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table v-loading="loading" :data="tableData" stripe>
        <el-table-column type="selection" width="55" />
        <el-table-column prop="operator" label="操作人" min-width="120" />
        <el-table-column prop="action" label="操作类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getActionType(row.action)">
              {{ getActionText(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" min-width="120" />
        <el-table-column prop="description" label="操作描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP地址" min-width="140" />
        <el-table-column prop="method" label="请求方法" width="100" />
        <el-table-column prop="duration" label="耗时(ms)" width="100" align="right" />
        <el-table-column prop="createTime" label="操作时间" min-width="180" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="操作详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="操作人">{{ currentLog?.operator }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">
          <el-tag :type="getActionType(currentLog?.action || '')">
            {{ getActionText(currentLog?.action || '') }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="模块">{{ currentLog?.module }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentLog?.ip }}</el-descriptions-item>
        <el-descriptions-item label="请求方法">{{ currentLog?.method }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ currentLog?.duration }}ms</el-descriptions-item>
        <el-descriptions-item label="操作时间" :span="2">{{ currentLog?.createTime }}</el-descriptions-item>
        <el-descriptions-item label="操作描述" :span="2">{{ currentLog?.description }}</el-descriptions-item>
        <el-descriptions-item label="请求参数" :span="2">
          <pre class="json-pre">{{ currentLog?.params }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="响应结果" :span="2">
          <pre class="json-pre">{{ currentLog?.result }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

interface OperateLog {
  id: number
  operator: string
  action: string
  module: string
  description: string
  ip: string
  method: string
  duration: number
  params: string
  result: string
  createTime: string
}

const loading = ref(false)
const detailVisible = ref(false)
const currentLog = ref<OperateLog | null>(null)

const searchForm = reactive({
  operator: '',
  action: '',
  dateRange: [] as string[]
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref<OperateLog[]>([])

const getActionType = (action: string) => {
  const types: Record<string, string> = {
    create: 'success',
    update: 'warning',
    delete: 'danger',
    query: 'info'
  }
  return types[action] || 'info'
}

const getActionText = (action: string) => {
  const texts: Record<string, string> = {
    create: '新增',
    update: '编辑',
    delete: '删除',
    query: '查询'
  }
  return texts[action] || action
}

const fetchData = async () => {
  loading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    tableData.value = [
      {
        id: 1,
        operator: 'admin',
        action: 'create',
        module: '用户管理',
        description: '新增用户test',
        ip: '192.168.1.100',
        method: 'POST',
        duration: 125,
        params: '{"username":"test","nickname":"测试用户"}',
        result: '{"code":200,"message":"success"}',
        createTime: '2024-01-15 10:30:00'
      },
      {
        id: 2,
        operator: 'admin',
        action: 'update',
        module: '角色管理',
        description: '编辑角色权限',
        ip: '192.168.1.100',
        method: 'PUT',
        duration: 89,
        params: '{"id":1,"permissions":[1,2,3]}',
        result: '{"code":200,"message":"success"}',
        createTime: '2024-01-15 10:25:00'
      }
    ]
    pagination.total = 2
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  searchForm.operator = ''
  searchForm.action = ''
  searchForm.dateRange = []
  handleSearch()
}

const handleView = (row: OperateLog) => {
  currentLog.value = { ...row }
  detailVisible.value = true
}

const handleSizeChange = (val: number) => {
  pagination.pageSize = val
  fetchData()
}

const handleCurrentChange = (val: number) => {
  pagination.page = val
  fetchData()
}

fetchData()
</script>

<style scoped>
.operate-log-container {
  padding: 0px;
}


.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.json-pre {
  background-color: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 0;
  font-size: 12px;
}
</style>
