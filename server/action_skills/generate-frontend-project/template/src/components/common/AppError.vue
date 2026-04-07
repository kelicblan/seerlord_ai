<script setup lang="ts">
import { CircleCloseFilled, Link, Lock, WarningFilled } from '@element-plus/icons-vue'
import { computed } from 'vue'

type ErrorType = 'network' | 'server' | 'permission' | '404'

interface ErrorConfig {
  icon: typeof WarningFilled
  title: string
  description: string
  showRetry: boolean
}

interface Props {
  type?: ErrorType
  message?: string
  showRetry?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'server',
  message: '',
  showRetry: true,
})

const emit = defineEmits<{
  retry: []
}>()

const errorConfigMap: Record<ErrorType, Omit<ErrorConfig, 'showRetry'>> = {
  network: {
    icon: Link,
    title: '网络异常',
    description: '网络连接失败，请检查您的网络设置后重试',
  },
  server: {
    icon: WarningFilled,
    title: '服务器错误',
    description: '服务器暂时无法响应，请稍后重试',
  },
  permission: {
    icon: Lock,
    title: '权限不足',
    description: '您没有访问该资源的权限，请联系管理员',
  },
  '404': {
    icon: CircleCloseFilled,
    title: '页面不存在',
    description: '您访问的页面可能已被删除或转移',
  },
}

const config = computed<ErrorConfig>(() => ({
  ...errorConfigMap[props.type],
  showRetry: props.showRetry,
}))

const displayTitle = computed(() => props.message || config.value.title)
</script>

<template>
  <div class="flex flex-col items-center justify-center px-4 py-12">
    <slot name="image">
      <el-icon :size="80" class="text-[var(--el-color-danger)]">
        <component :is="config.icon" />
      </el-icon>
    </slot>

    <div class="mt-5 text-center">
      <slot>
        <h3 class="text-lg font-medium text-[var(--app-text)]">{{ displayTitle }}</h3>
        <p class="mt-2 text-sm text-[var(--app-text-secondary)]">{{ config.description }}</p>
      </slot>
    </div>

    <div v-if="config.showRetry" class="mt-6">
      <slot name="action">
        <el-button type="primary" @click="emit('retry')">重试</el-button>
      </slot>
    </div>
  </div>
</template>
