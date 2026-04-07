<script setup lang="ts">
import { Check, Monitor, MoonNight, Sunny } from '@element-plus/icons-vue'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import type { ThemeMode } from '@/stores/app'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const { themeMode } = storeToRefs(appStore)

const themeOptions: Array<{
  icon: typeof Sunny
  label: string
  value: ThemeMode
}> = [
  {
    icon: Sunny,
    label: '浅色',
    value: 'light',
  },
  {
    icon: MoonNight,
    label: '深色',
    value: 'dark',
  },
  {
    icon: Monitor,
    label: '跟随系统',
    value: 'system',
  },
]

const currentTheme = computed(
  () => themeOptions.find((option) => option.value === themeMode.value) ?? themeOptions[2],
)
</script>

<template>
  <el-dropdown trigger="click" placement="top-start">
    <button
      type="button"
      class="flex h-8 w-8 cursor-pointer items-center justify-center rounded bg-[var(--app-surface-strong)] text-[var(--app-text)] hover:bg-[var(--app-primary)]/10"
    >
      <el-icon class="text-xs"><component :is="currentTheme.icon" /></el-icon>
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="option in themeOptions"
          :key="option.value"
          @click="themeMode = option.value"
        >
          <div class="flex min-w-[132px] items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <el-icon><component :is="option.icon" /></el-icon>
              <span>{{ option.label }}</span>
            </div>
            <el-icon v-if="themeMode === option.value"><Check /></el-icon>
          </div>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>
