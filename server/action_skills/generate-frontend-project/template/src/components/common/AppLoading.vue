<script setup lang="ts">
import { computed } from 'vue'

type LoadingSize = 'small' | 'default' | 'large'

interface Props {
  size?: LoadingSize
  color?: string
  fullscreen?: boolean
  text?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'default',
  color: '',
  fullscreen: false,
  text: '',
})

const sizeMap: Record<LoadingSize, number> = {
  small: 18,
  default: 32,
  large: 48,
}

const spinnerSize = computed(() => sizeMap[props.size])
const spinnerColor = computed(() => props.color || 'var(--el-color-primary)')
</script>

<template>
  <Teleport to="body">
    <div
      v-if="fullscreen"
      class="fixed inset-0 z-[2000] flex items-center justify-center bg-[var(--app-muted-surface)]/80 backdrop-blur-sm"
    >
      <div class="flex flex-col items-center gap-4">
        <el-icon class="is-loading" :size="spinnerSize" :color="spinnerColor">
          <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
            <path
              fill="currentColor"
              d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32zm0 640a32 32 0 0 1 32 32v192a32 32 0 1 1-64 0V736a32 32 0 0 1 32-32zm448-471a32 32 0 0 1-32 32H736a32 32 0 1 1 0-64h192a32 32 0 0 1 32 32zm-640 0a32 32 0 0 1-32 32H96a32 32 0 0 1 0-64h192a32 32 0 0 1 32 32zM195 195a32 32 0 0 1 45-45l141 141a32 32 0 0 1-45 45L195 195zm452 452l-141 141a32 32 0 0 1-45-45l141-141a32 32 0 1 1 45 45zM142 829a32 32 0 0 1-45-45l141-141a32 32 0 1 1 45 45l-141 141zm634 0l-141-141a32 32 0 1 1 45-45l141 141a32 32 0 0 1-45 45z"
            />
          </svg>
        </el-icon>
        <span v-if="text" class="text-sm text-[var(--app-text-secondary)]">{{ text }}</span>
      </div>
    </div>

    <div v-else class="flex flex-col items-center gap-3">
      <slot>
        <el-icon class="is-loading" :size="spinnerSize" :color="spinnerColor">
          <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
            <path
              fill="currentColor"
              d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32zm0 640a32 32 0 0 1 32 32v192a32 32 0 1 1-64 0V736a32 32 0 0 1 32-32zm448-471a32 32 0 0 1-32 32H736a32 32 0 1 1 0-64h192a32 32 0 0 1 32 32zm-640 0a32 32 0 0 1-32 32H96a32 32 0 0 1 0-64h192a32 32 0 0 1 32 32zM195 195a32 32 0 0 1 45-45l141 141a32 32 0 0 1-45 45L195 195zm452 452l-141 141a32 32 0 0 1-45-45l141-141a32 32 0 1 1 45 45zM142 829a32 32 0 0 1-45-45l141-141a32 32 0 1 1 45 45l-141 141zm634 0l-141-141a32 32 0 1 1 45-45l141 141a32 32 0 0 1-45 45z"
            />
          </svg>
        </el-icon>
      </slot>
      <span v-if="text" class="text-sm text-[var(--app-text-secondary)]">{{ text }}</span>
    </div>
  </Teleport>
</template>
