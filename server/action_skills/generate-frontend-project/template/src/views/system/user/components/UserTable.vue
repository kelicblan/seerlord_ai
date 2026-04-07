<template>
  <el-table v-loading="loading" :data="data" stripe>
    <el-table-column type="selection" width="55" />
    <el-table-column prop="username" label="用户名" min-width="120" />
    <el-table-column prop="nickname" label="昵称" min-width="120" />
    <el-table-column prop="phone" label="手机号" min-width="130" />
    <el-table-column prop="email" label="邮箱" min-width="180" />
    <el-table-column prop="status" label="状态" width="100" align="center">
      <template #default="{ row }">
        <el-tag :type="row.status === 1 ? 'success' : 'danger'">
          {{ row.status === 1 ? '启用' : '禁用' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="createTime" label="创建时间" min-width="180" />
    <el-table-column label="操作" width="200" fixed="right">
      <template #default="{ row }">
        <el-button link type="primary" @click="emit('view', row)">查看</el-button>
        <el-button link type="primary" @click="emit('edit', row)">编辑</el-button>
        <el-button link type="danger" @click="emit('delete', row)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
interface User {
  id: number
  username: string
  nickname: string
  phone: string
  email: string
  status: number
  createTime: string
}

defineProps<{
  data: User[]
  loading: boolean
}>()

const emit = defineEmits<{
  edit: [row: User]
  delete: [row: User]
  view: [row: User]
}>()
</script>

<style scoped>
</style>
