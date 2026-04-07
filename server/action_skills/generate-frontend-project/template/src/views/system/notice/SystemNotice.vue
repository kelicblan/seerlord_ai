<template>
  <div class="system-notice-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>系统公告</span>
          <el-button type="primary" @click="handleCreate">发布公告</el-button>
        </div>
      </template>

      <div class="search-bar">
        <el-form :inline="true" :model="searchForm">
          <el-form-item label="标题">
            <el-input v-model="searchForm.title" placeholder="请输入标题" clearable />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="searchForm.status" placeholder="请选择" clearable>
              <el-option label="已发布" :value="1" />
              <el-option label="草稿" :value="0" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table v-loading="loading" :data="tableData" stripe>
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.type)">{{ getTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'">
              {{ row.status === 1 ? '已发布' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="author" label="发布人" width="120" />
        <el-table-column prop="publishTime" label="发布时间" width="180" />
        <el-table-column prop="views" label="浏览量" width="100" align="right" />
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
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="公告详情" width="700px">
      <div class="notice-detail">
        <h2 class="notice-title">{{ currentNotice?.title }}</h2>
        <div class="notice-meta">
          <el-tag :type="getTypeTag(currentNotice?.type || '')">{{ getTypeText(currentNotice?.type || '') }}</el-tag>
          <span class="meta-item">发布人：{{ currentNotice?.author }}</span>
          <span class="meta-item">发布时间：{{ currentNotice?.publishTime }}</span>
          <span class="meta-item">浏览量：{{ currentNotice?.views }}</span>
        </div>
        <el-divider />
        <div class="notice-content">{{ currentNotice?.content }}</div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="formVisible" :title="formTitle" width="700px" @close="handleClose">
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="formData.title" placeholder="请输入标题" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="formData.type" placeholder="请选择类型">
            <el-option label="系统通知" value="system" />
            <el-option label="功能更新" value="feature" />
            <el-option label="维护公告" value="maintenance" />
            <el-option label="活动通知" value="activity" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="formData.status">
            <el-radio :label="1">发布</el-radio>
            <el-radio :label="0">草稿</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="formData.content" type="textarea" :rows="8" placeholder="请输入内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

interface Notice {
  id: number
  title: string
  type: string
  content: string
  status: number
  author: string
  publishTime: string
  views: number
}

const loading = ref(false)
const detailVisible = ref(false)
const formVisible = ref(false)
const formMode = ref<'create' | 'edit'>('create')
const currentNotice = ref<Notice | null>(null)
const formRef = ref<FormInstance>()

const searchForm = reactive({
  title: '',
  status: null as number | null
})

const formData = reactive<Notice>({
  id: 0,
  title: '',
  type: 'system',
  content: '',
  status: 0,
  author: '管理员',
  publishTime: '',
  views: 0
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }]
}

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref<Notice[]>([])

const formTitle = computed(() => formMode.value === 'create' ? '发布公告' : '编辑公告')

const getTypeText = (type: string) => {
  const texts: Record<string, string> = {
    system: '系统通知',
    feature: '功能更新',
    maintenance: '维护公告',
    activity: '活动通知'
  }
  return texts[type] || type
}

const getTypeTag = (type: string) => {
  const tags: Record<string, string> = {
    system: '',
    feature: 'success',
    maintenance: 'warning',
    activity: 'danger'
  }
  return tags[type] || ''
}

const fetchData = async () => {
  loading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    tableData.value = [
      {
        id: 1,
        title: '系统升级通知',
        type: 'system',
        content: '系统将于本周日凌晨2:00-6:00进行升级维护...',
        status: 1,
        author: '管理员',
        publishTime: '2024-01-15 10:00:00',
        views: 1256
      },
      {
        id: 2,
        title: '新功能上线',
        type: 'feature',
        content: '新增数据导出功能，支持Excel和CSV格式...',
        status: 1,
        author: '管理员',
        publishTime: '2024-01-14 09:00:00',
        views: 890
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
  searchForm.title = ''
  searchForm.status = null
  handleSearch()
}

const handleCreate = () => {
  formMode.value = 'create'
  Object.assign(formData, {
    id: 0,
    title: '',
    type: 'system',
    content: '',
    status: 0,
    author: '管理员',
    publishTime: '',
    views: 0
  })
  formVisible.value = true
}

const handleEdit = (row: Notice) => {
  formMode.value = 'edit'
  Object.assign(formData, { ...row })
  formVisible.value = true
}

const handleView = (row: Notice) => {
  currentNotice.value = { ...row }
  detailVisible.value = true
}

const handleDelete = async (_row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该公告吗？', '提示', { type: 'warning' })
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    // User cancelled
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate((valid) => {
    if (valid) {
      ElMessage.success(formMode.value === 'create' ? '发布成功' : '保存成功')
      formVisible.value = false
      fetchData()
    }
  })
}

const handleClose = () => {
  formRef.value?.resetFields()
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
.system-notice-container {
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

.notice-detail {
  padding: 10px;
}

.notice-title {
  text-align: center;
  margin-bottom: 15px;
}

.notice-meta {
  display: flex;
  align-items: center;
  gap: 20px;
  justify-content: center;
}

.meta-item {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.notice-content {
  line-height: 1.8;
  white-space: pre-wrap;
}
</style>
