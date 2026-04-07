<template>
  <div class="approve-pending-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>待审批列表</span>
          <el-tag type="warning">{{ pagination.total }} 条待审批</el-tag>
        </div>
      </template>

      <el-table v-loading="loading" :data="tableData" stripe>
        <el-table-column type="selection" width="55" />
        <el-table-column prop="type" label="审批类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ getTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="applicant" label="申请人" width="120" />
        <el-table-column prop="dept" label="所属部门" width="150" />
        <el-table-column prop="createTime" label="申请时间" width="180" />
        <el-table-column prop="priority" label="优先级" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getPriorityType(row.priority)">
              {{ getPriorityText(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleApprove(row)">审批</el-button>
            <el-button link type="info" @click="handleView(row)">详情</el-button>
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

    <el-dialog v-model="dialogVisible" title="审批" width="600px">
      <el-form :model="approveForm" label-width="100px">
        <el-form-item label="审批结果">
          <el-radio-group v-model="approveForm.result">
            <el-radio label="approve">通过</el-radio>
            <el-radio label="reject">拒绝</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="审批意见">
          <el-input
            v-model="approveForm.comment"
            type="textarea"
            :rows="4"
            placeholder="请输入审批意见"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="申请详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="审批类型">
          <el-tag>{{ getTypeText(currentRecord?.type || '') }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="优先级">
          <el-tag :type="getPriorityType(currentRecord?.priority || '')">
            {{ getPriorityText(currentRecord?.priority || '') }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ currentRecord?.title }}</el-descriptions-item>
        <el-descriptions-item label="申请人">{{ currentRecord?.applicant }}</el-descriptions-item>
        <el-descriptions-item label="所属部门">{{ currentRecord?.dept }}</el-descriptions-item>
        <el-descriptions-item label="申请时间" :span="2">{{ currentRecord?.createTime }}</el-descriptions-item>
        <el-descriptions-item label="申请理由" :span="2">{{ currentRecord?.reason }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

interface ApproveRecord {
  id: number
  type: string
  title: string
  applicant: string
  dept: string
  createTime: string
  priority: string
  reason: string
}

const loading = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentRecord = ref<ApproveRecord | null>(null)

const approveForm = reactive({
  result: 'approve',
  comment: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref<ApproveRecord[]>([])

const getTypeText = (type: string) => {
  const texts: Record<string, string> = {
    leave: '请假申请',
    overtime: '加班申请',
    expense: '报销申请',
    purchase: '采购申请'
  }
  return texts[type] || type
}

const getPriorityType = (priority: string) => {
  const types: Record<string, string> = {
    low: 'info',
    normal: '',
    high: 'warning',
    urgent: 'danger'
  }
  return types[priority] || ''
}

const getPriorityText = (priority: string) => {
  const texts: Record<string, string> = {
    low: '低',
    normal: '普通',
    high: '高',
    urgent: '紧急'
  }
  return texts[priority] || priority
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
        dept: '技术部',
        createTime: '2024-01-15 10:30:00',
        priority: 'normal',
        reason: '因个人原因需要请假3天'
      },
      {
        id: 2,
        type: 'overtime',
        title: '周末加班申请',
        applicant: '李四',
        dept: '运营部',
        createTime: '2024-01-15 09:00:00',
        priority: 'high',
        reason: '项目紧急需要周末加班'
      },
      {
        id: 3,
        type: 'expense',
        title: '出差报销',
        applicant: '王五',
        dept: '销售部',
        createTime: '2024-01-14 15:30:00',
        priority: 'urgent',
        reason: '北京出差费用报销'
      }
    ]
    pagination.total = 3
  } finally {
    loading.value = false
  }
}

const handleApprove = (row: ApproveRecord) => {
  currentRecord.value = { ...row }
  approveForm.result = 'approve'
  approveForm.comment = ''
  dialogVisible.value = true
}

const handleView = (row: ApproveRecord) => {
  currentRecord.value = { ...row }
  detailVisible.value = true
}

const handleSubmit = () => {
  ElMessage.success('审批提交成功')
  dialogVisible.value = false
  fetchData()
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
.approve-pending-container {
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
