<template>
  <div class="system-backup-container">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>备份记录</span>
              <el-button type="primary" @click="handleBackup">立即备份</el-button>
            </div>
          </template>

          <el-table v-loading="loading" :data="tableData" stripe>
            <el-table-column prop="name" label="备份名称" min-width="200" />
            <el-table-column prop="type" label="备份类型" width="100" align="center">
              <template #default="{ row }">
                <el-tag>{{ row.type === 'full' ? '全量' : '增量' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="size" label="文件大小" width="120" align="right" />
            <el-table-column prop="status" label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
                  {{ row.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="createTime" label="备份时间" width="180" />
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleDownload(row)">下载</el-button>
                <el-button link type="primary" @click="handleRestore(row)">还原</el-button>
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
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="backup-stats">
          <template #header>
            <span>备份统计</span>
          </template>
          <el-statistic title="总备份数" :value="stats.total" />
          <el-divider direction="vertical" />
          <el-statistic title="成功" :value="stats.success" />
          <el-divider direction="vertical" />
          <el-statistic title="失败" :value="stats.failed" />
        </el-card>

        <el-card shadow="never" class="backup-config">
          <template #header>
            <span>备份配置</span>
          </template>
          <el-form label-width="100px" size="default">
            <el-form-item label="自动备份">
              <el-switch v-model="config.autoBackup" />
            </el-form-item>
            <el-form-item label="备份周期">
              <el-select v-model="config.cycle" :disabled="!config.autoBackup">
                <el-option label="每天" value="daily" />
                <el-option label="每周" value="weekly" />
                <el-option label="每月" value="monthly" />
              </el-select>
            </el-form-item>
            <el-form-item label="保留份数">
              <el-input-number v-model="config.keepCount" :min="1" :max="30" />
            </el-form-item>
            <el-form-item label="备份路径">
              <el-input v-model="config.path" readonly />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

interface BackupRecord {
  id: number
  name: string
  type: string
  size: string
  status: string
  createTime: string
}

const loading = ref(false)

const stats = reactive({
  total: 0,
  success: 0,
  failed: 0
})

const config = reactive({
  autoBackup: true,
  cycle: 'daily',
  keepCount: 7,
  path: '/data/backup'
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref<BackupRecord[]>([])

const fetchData = async () => {
  loading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    tableData.value = [
      {
        id: 1,
        name: 'backup_20240115_020000_full',
        type: 'full',
        size: '2.5 GB',
        status: 'success',
        createTime: '2024-01-15 02:00:00'
      },
      {
        id: 2,
        name: 'backup_20240114_020000_incr',
        type: 'incremental',
        size: '256 MB',
        status: 'success',
        createTime: '2024-01-14 02:00:00'
      },
      {
        id: 3,
        name: 'backup_20240113_020000_full',
        type: 'full',
        size: '2.4 GB',
        status: 'success',
        createTime: '2024-01-13 02:00:00'
      }
    ]
    stats.total = 3
    stats.success = 3
    stats.failed = 0
    pagination.total = 3
  } finally {
    loading.value = false
  }
}

const handleBackup = async () => {
  try {
    await ElMessageBox.confirm('确定要立即执行备份吗？', '提示', { type: 'info' })
    ElMessage.success('备份任务已创建，请稍候...')
  } catch {
    // User cancelled
  }
}

const handleDownload = (row: BackupRecord) => {
  ElMessage.info(`开始下载: ${row.name}`)
}

const handleRestore = async (row: BackupRecord) => {
  try {
    await ElMessageBox.confirm(
      `确定要还原到备份"${row.name}"吗？这将覆盖当前数据。`,
      '警告',
      { type: 'warning' }
    )
    ElMessage.success('还原任务已创建，请稍候...')
  } catch {
    // User cancelled
  }
}

const handleDelete = async (_row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该备份吗？', '提示', { type: 'warning' })
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    // User cancelled
  }
}

const handleSaveConfig = () => {
  ElMessage.success('配置保存成功')
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
.system-backup-container {
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

.backup-stats {
  margin-bottom: 20px;
}

.backup-config {
  margin-bottom: 20px;
}

:deep(.el-divider) {
  height: 40px;
  vertical-align: middle;
  margin: 0 20px;
}
</style>
