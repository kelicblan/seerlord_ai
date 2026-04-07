<template>
  <div class="error-container">
    <div class="error-content">
      <div class="error-icon">
        <el-icon :size="120" color="#f56c6c"><CircleClose /></el-icon>
      </div>
      <h1 class="error-code">500</h1>
      <h2 class="error-title">服务器内部错误</h2>
      <p class="error-description">
        抱歉，服务器遇到了一个意外情况，无法完成您的请求。请稍后再试。
      </p>
      <div class="error-actions">
        <el-button type="primary" size="large" @click="reloadPage">
          刷新页面
        </el-button>
        <el-button size="large" @click="goHome">
          返回首页
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CircleClose } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const reloadPage = () => {
  window.location.reload()
}

const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
.error-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.error-content {
  text-align: center;
  color: white;
}

.error-icon {
  margin-bottom: 2rem;
  opacity: 0.9;
}

.error-code {
  font-size: 8rem;
  font-weight: 700;
  margin: 0;
  text-shadow: 2px 4px 8px rgba(0, 0, 0, 0.3);
}

.error-title {
  font-size: 2.5rem;
  margin: 1rem 0;
  font-weight: 600;
}

.error-description {
  font-size: 1.1rem;
  margin: 1.5rem 0 2.5rem;
  opacity: 0.9;
  max-width: 500px;
  line-height: 1.6;
}

.error-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}
</style>
