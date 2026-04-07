<template>
  <div class="role-list-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>角色管理</span>
          <el-button type="primary" @click="handleCreate">新增角色</el-button>
        </div>
      </template>

      <role-table
        :data="tableData"
        :loading="loading"
        @edit="handleEdit"
        @delete="handleDelete"
        @view="handleView"
      />
    </el-card>

    <role-form
      v-model="dialogVisible"
      :data="currentRole"
      :mode="dialogMode"
      @submit="handleSubmit"
      @cancel="handleCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import RoleTable from './components/RoleTable.vue'
import RoleForm from './RoleForm.vue'

interface Role {
  id: number
  name: string
  code: string
  description: string
  status: number
  createTime: string
}

const loading = ref(false)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit' | 'view'>('create')
const currentRole = ref<Role | null>(null)

const tableData = ref<Role[]>([])

const fetchData = async () => {
  loading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    tableData.value = [
      {
        id: 1,
        name: '超级管理员',
        code: 'super_admin',
        description: '拥有系统所有权限',
        status: 1,
        createTime: '2024-01-01 10:00:00'
      },
      {
        id: 2,
        name: '普通用户',
        code: 'user',
        description: '普通用户角色',
        status: 1,
        createTime: '2024-01-02 10:00:00'
      }
    ]
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  currentRole.value = null
  dialogMode.value = 'create'
  dialogVisible.value = true
}

const handleEdit = (row: Role) => {
  currentRole.value = { ...row }
  dialogMode.value = 'edit'
  dialogVisible.value = true
}

const handleView = (row: Role) => {
  currentRole.value = { ...row }
  dialogMode.value = 'view'
  dialogVisible.value = true
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确定要删除该角色吗？', '提示', {
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

fetchData()
</script>

<style scoped>
.role-list-container {
  padding: 0px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
