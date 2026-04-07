<template>
  <div class="error-container">
    <div class="error-content">
      <div class="error-icon">
        <el-icon :size="120" color="#909399"><DocumentDelete /></el-icon>
      </div>
      <h1 class="error-code">404</h1>
      <h2 class="error-title">抱歉，页面不存在</h2>
      <p class="error-description">
        您访问的页面可能已被删除或不存在，请检查URL是否正确。
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
import { DocumentDelete } from '@element-plus/icons-vue'
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
