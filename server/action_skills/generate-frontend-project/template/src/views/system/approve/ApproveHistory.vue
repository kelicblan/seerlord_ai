<template>
  <div class="approve-history-container">
    <el-card shadow="never">
      <template #header>
        <span>审批历史</span>
      </template>

      <div class="search-bar">
        <el-form :inline="true" :model="searchForm">
          <el-form-item label="审批类型">
            <el-select v-model="searchForm.type" placeholder="请选择" clearable>
              <el-option label="请假申请" value="leave" />
              <el-option label="加班申请" value="overtime" />
              <el-option label="报销申请" value="expense" />
              <el-option label="采购申请" value="purchase" />
            </el-select>
          </el-form-item>
          <el-form-item label="审批状态">
            <el-select v-model="searchForm.status" placeholder="请选择" clearable>
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
          </el-form-item>
          <el-form-item label="审批时间">
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
        <el-table-column prop="type" label="审批类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ getTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="applicant" label="申请人" width="120" />
        <el-table-column prop="status" label="审批状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'approved' ? 'success' : 'danger'">
              {{ row.status === 'approved' ? '已通过' : '已拒绝' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="approver" label="审批人" width="120" />
        <el-table-column prop="comment" label="审批意见" min-width="200" show-overflow-tooltip />
        <el-table-column prop="approveTime" label="审批时间" width="180" />
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
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="审批详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="审批类型">
          <el-tag>{{ getTypeText(currentRecord?.type || '') }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="审批状态">
          <el-tag :type="currentRecord?.status === 'approved' ? 'success' : 'danger'">
            {{ currentRecord?.status === 'approved' ? '已通过' : '已拒绝' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ currentRecord?.title }}</el-descriptions-item>
        <el-descriptions-item label="申请人">{{ currentRecord?.applicant }}</el-descriptions-item>
        <el-descriptions-item label="审批人">{{ currentRecord?.approver }}</el-descriptions-item>
        <el-descriptions-item label="申请时间">{{ currentRecord?.createTime }}</el-descriptions-item>
        <el-descriptions-item label="审批时间">{{ currentRecord?.approveTime }}</el-descriptions-item>
        <el-descriptions-item label="申请理由" :span="2">{{ currentRecord?.reason }}</el-descriptions-item>
        <el-descriptions-item label="审批意见" :span="2">{{ currentRecord?.comment }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

interface ApproveHistory {
  id: number
  type: string
  title: string
  applicant: string
  status: string
  approver: string
  comment: string
  createTime: string
  approveTime: string
  reason: string
}

const loading = ref(false)
const detailVisible = ref(false)
const currentRecord = ref<ApproveHistory | null>(null)

const searchForm = reactive({
  type: '',
  status: '',
  dateRange: [] as string[]
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref<ApproveHistory[]>([])

const getTypeText = (type: string) => {
  const texts: Record<string, string> = {
    leave: '请假申请',
    overtime: '加班申请',
    expense: '报销申请',
    purchase: '采购申请'
  }
  return texts[type] || type
}

const fetchData = async () => {
  loading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    tableData.value = [
      {
        id: 1,
        type: 'leave',
        title: '年假申请',
        applicant: '张三',
        status: 'approved',
        approver: '管理员',
        comment: '同意年假申请',
        createTime: '2024-01-10 10:00:00',
        approveTime: '2024-01-10 14:30:00',
        reason: '因个人原因需要请假3天'
      },
      {
        id: 2,
        type: 'expense',
        title: '出差报销',
        applicant: '李四',
        status: 'rejected',
        approver: '管理员',
        comment: '报销金额过高，需重新评估',
        createTime: '2024-01-08 09:00:00',
        approveTime: '2024-01-08 11:00:00',
        reason: '北京出差费用报销'
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
  searchForm.type = ''
  searchForm.status = ''
  searchForm.dateRange = []
  handleSearch()
}

const handleView = (row: ApproveHistory) => {
  currentRecord.value = { ...row }
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
.approve-history-container {
  padding: 0px;
}


.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
