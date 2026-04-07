<script setup lang="ts">
import { ref, reactive } from 'vue'
import {
  ElCard,
  ElTabs,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElButton,
  ElTag,
  ElSwitch,
  ElMessage,
  ElMessageBox,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElTree,
} from 'element-plus'
import {
  Plus,
  Edit,
  Delete,
  Key,
} from '@element-plus/icons-vue'

interface Permission {
  id: string
  name: string
  code: string
  type: string
  description: string
  enabled: boolean
  createdAt: string
}

interface Role {
  id: string
  name: string
  code: string
  description: string
  permissionCount: number
  userCount: number
  enabled: boolean
  createdAt: string
}

const activeTab = ref('permissions')

const permissions = ref<Permission[]>([
  {
    id: '1',
    name: '查看权限',
    code: 'permission:view',
    type: 'button',
    description: '查看权限列表',
    enabled: true,
    createdAt: '2024-01-15',
  },
  {
    id: '2',
    name: '创建权限',
    code: 'permission:create',
    type: 'button',
    description: '创建新的权限',
    enabled: true,
    createdAt: '2024-01-15',
  },
  {
    id: '3',
    name: '编辑权限',
    code: 'permission:update',
    type: 'button',
    description: '编辑现有权限',
    enabled: true,
    createdAt: '2024-01-15',
  },
  {
    id: '4',
    name: '删除权限',
    code: 'permission:delete',
    type: 'button',
    description: '删除权限',
    enabled: true,
    createdAt: '2024-01-15',
  },
  {
    id: '5',
    name: '导出数据',
    code: 'data:export',
    type: 'button',
    description: '导出系统数据',
    enabled: false,
    createdAt: '2024-01-16',
  },
])

const roles = ref<Role[]>([
  {
    id: '1',
    name: '超级管理员',
    code: 'admin',
    description: '拥有系统所有权限',
    permissionCount: 45,
    userCount: 2,
    enabled: true,
    createdAt: '2024-01-01',
  },
  {
    id: '2',
    name: '普通管理员',
    code: 'manager',
    description: '拥有大部分管理权限',
    permissionCount: 28,
    userCount: 5,
    enabled: true,
    createdAt: '2024-01-02',
  },
  {
    id: '3',
    name: '普通用户',
    code: 'user',
    description: '基本操作权限',
    permissionCount: 12,
    userCount: 100,
    enabled: true,
    createdAt: '2024-01-03',
  },
])

const permissionTreeData = ref([
  {
    id: '1',
    label: '系统管理',
    children: [
      {
        id: '1-1',
        label: '用户管理',
        children: [
          { id: '1-1-1', label: '查看用户' },
          { id: '1-1-2', label: '创建用户' },
          { id: '1-1-3', label: '编辑用户' },
          { id: '1-1-4', label: '删除用户' },
        ],
      },
      {
        id: '1-2',
        label: '角色管理',
        children: [
          { id: '1-2-1', label: '查看角色' },
          { id: '1-2-2', label: '创建角色' },
          { id: '1-2-3', label: '编辑角色' },
          { id: '1-2-4', label: '删除角色' },
        ],
      },
    ],
  },
  {
    id: '2',
    label: '业务管理',
    children: [
      { id: '2-1', label: '订单管理' },
      { id: '2-2', label: '商品管理' },
      { id: '2-3', label: '会员管理' },
    ],
  },
])

const rolePermissionForm = reactive({
  roleId: '',
  permissions: [] as string[],
})

const permissionDialogVisible = ref(false)
const matrixDialogVisible = ref(false)

const getPermissionType = (type: string) => {
  const map: Record<string, 'warning' | 'primary' | 'success' | 'info'> = {
    menu: 'warning',
    button: 'primary',
    api: 'success',
  }
  return map[type] || 'info'
}

const handleTogglePermission = (row: Permission) => {
  row.enabled = !row.enabled
  ElMessage.success(`${row.enabled ? '启用' : '禁用'}权限成功`)
}

const handleEditPermission = (row: Permission) => {
  ElMessage.info(`编辑权限: ${row.name}`)
}

const handleDeletePermission = async (row: Permission) => {
  try {
    await ElMessageBox.confirm(`确定要删除权限 "${row.name}" 吗？`, '提示', {
      type: 'warning',
    })
    ElMessage.success('删除成功')
  } catch {
    // User cancelled
  }
}

const handleAddPermission = () => {
  ElMessage.info('添加权限')
}

const handleAddRole = () => {
  ElMessage.info('添加角色')
}

const handleEditRole = (row: Role) => {
  ElMessage.info(`编辑角色: ${row.name}`)
}

const handleDeleteRole = async (row: Role) => {
  try {
    await ElMessageBox.confirm(`确定要删除角色 "${row.name}" 吗？`, '提示', {
      type: 'warning',
    })
    ElMessage.success('删除成功')
  } catch {
    // User cancelled
  }
}

const handleAssignPermissions = (row: Role) => {
  rolePermissionForm.roleId = row.id
  rolePermissionForm.permissions = []
  permissionDialogVisible.value = true
}

const handleViewMatrix = () => {
  matrixDialogVisible.value = true
}

const handleSavePermissions = () => {
  ElMessage.success('权限分配成功')
  permissionDialogVisible.value = false
}
</script>

<template>
  <div class="permission-control">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>操作访问限制</span>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="权限列表" name="permissions">
          <div class="mb-4">
            <el-button type="primary" @click="handleAddPermission">
              <el-icon class="el-icon--left"><Plus /></el-icon>
              添加权限
            </el-button>
            <el-button @click="handleViewMatrix">
              <el-icon class="el-icon--left"><Key /></el-icon>
              权限矩阵
            </el-button>
          </div>

          <el-table :data="permissions" stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="name" label="权限名称" min-width="120" />
            <el-table-column prop="code" label="权限代码" min-width="150" />
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="getPermissionType(row.type)" size="small">
                  {{ row.type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="150" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" @change="handleTogglePermission(row)" />
              </template>
            </el-table-column>
            <el-table-column prop="createdAt" label="创建时间" width="120" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="handleEditPermission(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button type="danger" size="small" @click="handleDeletePermission(row)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="角色权限" name="roles">
          <div class="mb-4">
            <el-button type="primary" @click="handleAddRole">
              <el-icon class="el-icon--left"><Plus /></el-icon>
              添加角色
            </el-button>
          </div>

          <el-table :data="roles" stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="name" label="角色名称" min-width="120" />
            <el-table-column prop="code" label="角色代码" min-width="120" />
            <el-table-column prop="description" label="描述" min-width="150" />
            <el-table-column prop="permissionCount" label="权限数" width="100" align="center" />
            <el-table-column prop="userCount" label="用户数" width="100" align="center" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
                  {{ row.enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="handleEditRole(row)">
                  编辑
                </el-button>
                <el-button size="small" @click="handleAssignPermissions(row)">
                  分配权限
                </el-button>
                <el-button type="danger" size="small" @click="handleDeleteRole(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="权限树" name="tree">
          <el-tree :data="permissionTreeData" :props="{ children: 'children', label: 'label' }" default-expand-all />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="permissionDialogVisible" title="分配权限" width="600px">
      <el-form :model="rolePermissionForm" label-width="100px">
        <el-form-item label="角色">
          <el-input v-model="rolePermissionForm.roleId" disabled />
        </el-form-item>
        <el-form-item label="权限">
          <el-tree
            :data="permissionTreeData"
            :props="{ children: 'children', label: 'label' }"
            show-checkbox
            default-expand-all
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="permissionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSavePermissions">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="matrixDialogVisible" title="权限矩阵" width="80%">
      <el-alert
        title="权限矩阵说明"
        type="info"
        description="查看角色与权限的对应关系矩阵"
        :closable="false"
      />
    </el-dialog>
  </div>
</template>

<style scoped>
.permission-control {
  padding: 0px;
}

.card-header {
  font-weight: 600;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>
