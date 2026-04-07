<script setup lang="ts">
import { FolderOpened } from '@element-plus/icons-vue'

interface Props {
  description?: string
  showButton?: boolean
}

withDefaults(defineProps<Props>(), {
  description: '暂无数据',
  showButton: false,
})

defineEmits<{
  click: []
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center px-4 py-12">
    <slot name="image">
      <el-icon :size="80" class="text-[var(--app-text-disabled)]">
        <FolderOpened />
      </el-icon>
    </slot>

    <div class="mt-5 text-center">
      <slot>
        <p class="text-base text-[var(--app-text-secondary)]">{{ description }}</p>
      </slot>
    </div>

    <div v-if="showButton" class="mt-6">
      <slot name="button">
        <el-button type="primary" @click="$emit('click')">
          {{ $slots.button ? undefined : '刷新页面' }}
        </el-button>
      </slot>
    </div>
  </div>
</template>
