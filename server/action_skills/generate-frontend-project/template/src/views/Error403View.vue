<template>
  <div class="error-container">
    <div class="error-content">
      <div class="error-icon">
        <el-icon :size="120" color="#e6a23c"><Warning /></el-icon>
      </div>
      <h1 class="error-code">403</h1>
      <h2 class="error-title">抱歉，您没有访问权限</h2>
      <p class="error-description">
        您当前没有权限访问该页面，请联系管理员获取相应权限。
      </p>
      <div class="error-actions">
        <el-button type="primary" size="large" @click="goHome">
          返回首页
        </el-button>
        <el-button size="large" @click="goBack">
          返回上一页
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Warning } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/')
}

const goBack = () => {
  router.back()
}
</script>

<style scoped>
.error-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
