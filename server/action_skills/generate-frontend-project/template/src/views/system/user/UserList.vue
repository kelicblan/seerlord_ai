<template>
  <div class="user-list-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="handleCreate">新增用户</el-button>
        </div>
      </template>

      <div class="search-bar">
        <el-form :inline="true" :model="searchForm">
          <el-form-item label="用户名">
            <el-input v-model="searchForm.username" placeholder="请输入用户名" clearable />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input v-model="searchForm.phone" placeholder="请输入手机号" clearable />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="searchForm.status" placeholder="请选择状态" clearable>
              <el-option label="启用" :value="1" />
              <el-option label="禁用" :value="0" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <user-table
        :data="tableData"
        :loading="loading"
        @edit="handleEdit"
        @delete="handleDelete"
        @view="handleView"
      />

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

    <user-form
      v-model="dialogVisible"
      :data="currentUser"
      :mode="dialogMode"
      @submit="handleSubmit"
      @cancel="handleCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import UserTable from './components/UserTable.vue'
import UserForm from './UserForm.vue'

interface User {
  id: number
  username: string
  nickname: string
  phone: string
  email: string
  status: number
  createTime: string
}

const loading = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit' | 'view'>('create')
const currentUser = ref<User | null>(null)

const searchForm = reactive({
  username: '',
  phone: '',
  status: null as number | null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref<User[]>([])

const fetchData = async () => {
  loading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    tableData.value = [
      {
        id: 1,
        username: 'admin',
        nickname: '管理员',
        phone: '13800138000',
        email: 'admin@example.com',
        status: 1,
        createTime: '2024-01-01 10:00:00'
      },
      {
        id: 2,
        username: 'user01',
        nickname: '用户01',
        phone: '13800138001',
        email: 'user01@example.com',
        status: 1,
        createTime: '2024-01-02 10:00:00'
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
  searchForm.username = ''
  searchForm.phone = ''
  searchForm.status = null
  handleSearch()
}

const handleCreate = () => {
  currentUser.value = null
  dialogMode.value = 'create'
  dialogVisible.value = true
}

const handleEdit = (row: User) => {
  currentUser.value = { ...row }
  dialogMode.value = 'edit'
  dialogVisible.value = true
}

const handleView = (row: User) => {
  currentUser.value = { ...row }
  dialogMode.value = 'view'
  dialogVisible.value = true
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确定要删除该用户吗？', '提示', {
      type: 'warning'
    })
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    // 用户取消
  }
}

const handleSubmit = () => {
  ElMessage.success('保存成功')
  dialogVisible.value = false
  fetchData()
}

const handleCancel = () => {
  dialogVisible.value = false
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
.user-list-container {
  padding: 0px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}


.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
