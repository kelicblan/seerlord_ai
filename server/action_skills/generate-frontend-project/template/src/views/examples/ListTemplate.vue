<template>
  <div class="list-template-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>列表模板</span>
          <el-button type="primary" @click="handleCreate">新增</el-button>
        </div>
      </template>

      <div class="search-bar">
        <el-form :inline="true" :model="searchForm">
          <el-form-item label="关键词">
            <el-input v-model="searchForm.keyword" placeholder="请输入关键词" clearable />
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

      <el-table :data="tableData" :loading="loading" stripe>
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="views" label="浏览量" width="100" />
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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

    <FormDialog
      v-model:visible="formDialogVisible"
      :mode="formMode"
      :data="currentRowData"
      @success="handleFormSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FormDialog, { type FormMode, type FormData } from './components/FormDialog.vue'
import {
  examplesListApi,
  examplesDetailApi,
  examplesDeleteApi,
  type ExampleItem
} from '@/api/modules/examples'

const loading = ref(false)

const searchForm = reactive({
  keyword: '',
  status: null as number | null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref<ExampleItem[]>([])

const formDialogVisible = ref(false)
const formMode = ref<FormMode>('create')
const currentRowData = ref<FormData>({
  username: '',
  nickname: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
  gender: 'male',
  age: 25,
  birthday: '',
  province: '',
  city: '',
  hobbies: [],
  website: '',
  bio: '',
  status: true,
  avatar: ''
})

const fetchData = async () => {
  loading.value = true
  try {
    const res = await examplesListApi({
      page: pagination.page,
      pageSize: pagination.pageSize,
      keyword: searchForm.keyword,
      status: searchForm.status
    })
    tableData.value = res.list
    pagination.total = res.total
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  searchForm.keyword = ''
  searchForm.status = null
  handleSearch()
}

const handleCreate = () => {
  formMode.value = 'create'
  currentRowData.value = {
    username: '',
    nickname: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    gender: 'male',
    age: 25,
    birthday: '',
    province: '',
    city: '',
    hobbies: [],
    website: '',
    bio: '',
    status: true,
    avatar: ''
  }
  formDialogVisible.value = true
}

const handleView = async (row: ExampleItem) => {
  formMode.value = 'view'
  try {
    const res = await examplesDetailApi(row.id)
    currentRowData.value = {
      id: res.id,
      username: 'testuser',
      nickname: '测试用户',
      email: 'test@example.com',
      phone: '13800138000',
      password: '',
      confirmPassword: '',
      gender: 'male',
      age: 25,
      birthday: '1999-01-01',
      province: 'beijing',
      city: 'beijing',
      hobbies: ['reading', 'coding'],
      website: 'https://example.com',
      bio: res.content || '这是一条测试数据',
      status: res.status === 1,
      avatar: ''
    }
  } catch {
    ElMessage.error('获取详情失败')
  }
  formDialogVisible.value = true
}

const handleEdit = (row: ExampleItem) => {
  formMode.value = 'edit'
  currentRowData.value = {
    id: row.id,
    username: 'testuser',
    nickname: '测试用户',
    email: 'test@example.com',
    phone: '13800138000',
    password: '',
    confirmPassword: '',
    gender: 'male',
    age: 25,
    birthday: '1999-01-01',
    province: 'beijing',
    city: 'beijing',
    hobbies: ['reading', 'coding'],
    website: 'https://example.com',
    bio: '这是一条测试数据',
    status: row.status === 1,
    avatar: ''
  }
  formDialogVisible.value = true
}

const handleFormSuccess = () => {
  fetchData()
}

const handleDelete = (row: ExampleItem) => {
  ElMessageBox.confirm(`确定删除 "${row.title}" 吗?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    await examplesDeleteApi(row.id)
    ElMessage.success('删除成功')
    fetchData()
  }).catch(() => {})
}

const handleSizeChange = () => {
  fetchData()
}

const handleCurrentChange = () => {
  fetchData()
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.list-template-container {
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
