<template>
  <div class="login-log-container">
    <el-card shadow="never">
      <template #header>
        <span>登录日志</span>
      </template>

      <div class="search-bar">
        <el-form :inline="true" :model="searchForm">
          <el-form-item label="用户名">
            <el-input v-model="searchForm.username" placeholder="请输入用户名" clearable />
          </el-form-item>
          <el-form-item label="登录状态">
            <el-select v-model="searchForm.status" placeholder="请选择" clearable>
              <el-option label="成功" :value="1" />
              <el-option label="失败" :value="0" />
            </el-select>
          </el-form-item>
          <el-form-item label="登录时间">
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
        <el-table-column type="selection" width="55" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="status" label="登录状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP地址" min-width="140" />
        <el-table-column prop="location" label="登录地点" min-width="150" />
        <el-table-column prop="browser" label="浏览器" min-width="150" />
        <el-table-column prop="os" label="操作系统" min-width="150" />
        <el-table-column prop="message" label="消息" min-width="200" show-overflow-tooltip />
        <el-table-column prop="loginTime" label="登录时间" min-width="180" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

interface LoginLog {
  id: number
  username: string
  status: number
  ip: string
  location: string
  browser: string
  os: string
  message: string
  loginTime: string
}

const loading = ref(false)

const searchForm = reactive({
  username: '',
  status: null as number | null,
  dateRange: [] as string[]
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref<LoginLog[]>([])

const fetchData = async () => {
  loading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    tableData.value = [
      {
        id: 1,
        username: 'admin',
        status: 1,
        ip: '192.168.1.100',
        location: '广东省深圳市',
        browser: 'Chrome 120.0',
        os: 'Windows 10',
        message: '登录成功',
        loginTime: '2024-01-15 10:30:00'
      },
      {
        id: 2,
        username: 'admin',
        status: 0,
        ip: '192.168.1.101',
        location: '广东省广州市',
        browser: 'Firefox 121.0',
        os: 'macOS',
        message: '密码错误',
        loginTime: '2024-01-15 09:15:00'
      },
      {
        id: 3,
        username: 'user01',
        status: 1,
        ip: '192.168.1.102',
        location: '北京市海淀区',
        browser: 'Safari 17.0',
        os: 'iOS 17.0',
        message: '登录成功',
        loginTime: '2024-01-15 08:00:00'
      }
    ]
    pagination.total = 3
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
  searchForm.status = null
  searchForm.dateRange = []
  handleSearch()
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
.login-log-container {
  padding: 0px;
}


.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
