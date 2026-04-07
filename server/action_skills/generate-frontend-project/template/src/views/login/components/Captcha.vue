<script setup lang="ts">
import { ref, onMounted } from 'vue'

const emit = defineEmits<{
  change: [key: string]
}>()

const captchaUrl = ref('')
const captchaKey = ref('')
const loading = ref(false)
const errorCount = ref(0)
const maxRetries = 2

const generateCaptchaKey = () => {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

const fetchCaptcha = async () => {
  if (errorCount.value >= maxRetries) {
    return
  }

  loading.value = true

  try {
    captchaKey.value = generateCaptchaKey()
    captchaUrl.value = `/api/captcha?key=${captchaKey.value}&t=${Date.now()}`
    emit('change', captchaKey.value)
  } catch (error) {
    console.error('获取验证码失败:', error)
  } finally {
    loading.value = false
  }
}

const handleRefresh = () => {
  errorCount.value = 0
  fetchCaptcha()
}

const handleImageError = () => {
  errorCount.value++
  if (errorCount.value < maxRetries) {
    setTimeout(() => {
      captchaUrl.value = `/api/captcha?key=${captchaKey.value}&t=${Date.now()}`
    }, 500)
  }
}

onMounted(() => {
  fetchCaptcha()
})
</script>

<template>
  <div class="flex gap-3">
    <el-input
      v-model="captchaKey"
      placeholder="请输入验证码"
      size="large"
      class="flex-1"
      @input="emit('change', captchaKey)"
    />

    <div
      class="flex h-[40px] min-w-[100px] cursor-pointer items-center justify-center overflow-hidden rounded border border-[var(--app-border)] bg-[var(--app-muted-surface)] transition-all hover:border-[var(--app-primary)]"
      :class="{ 'opacity-50': loading }"
      @click="handleRefresh"
    >
      <el-image
        v-if="captchaUrl && errorCount < maxRetries"
        :src="captchaUrl"
        fit="contain"
        class="h-full w-full"
        @error="handleImageError"
      >
        <template #placeholder>
          <div class="flex h-full w-full items-center justify-center bg-[var(--app-muted-surface)]">
            <span class="text-xs text-[var(--app-text-tertiary)]">加载中...</span>
          </div>
        </template>
      </el-image>

      <div v-else class="flex h-full w-full flex-col items-center justify-center gap-1">
        <span class="text-xs text-[var(--app-text-tertiary)]">点击刷新</span>
        <span v-if="errorCount >= maxRetries" class="text-xs text-red-500">加载失败</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.el-image {
  display: block;
}

.el-image :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
