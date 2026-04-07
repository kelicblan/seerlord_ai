<template>
  <el-table v-loading="loading" :data="data" stripe>
    <el-table-column type="selection" width="55" />
    <el-table-column prop="name" label="角色名称" min-width="120" />
    <el-table-column prop="code" label="角色编码" min-width="150" />
    <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
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
interface Role {
  id: number
  name: string
  code: string
  description: string
  status: number
  createTime: string
}

defineProps<{
  data: Role[]
  loading: boolean
}>()

const emit = defineEmits<{
  edit: [row: Role]
  delete: [row: Role]
  view: [row: Role]
}>()
</script>

<style scoped>
</style>
