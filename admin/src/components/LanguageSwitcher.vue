<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Languages } from 'lucide-vue-next'

const { locale } = useI18n()

const languages = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁体中文' },
  { value: 'en', label: 'English' },
]

const setLanguage = (lang: string) => {
  locale.value = lang as any
  localStorage.setItem('user-locale', lang)
}

const handleCommand = (lang: string) => {
  setLanguage(lang)
}
</script>

<template>
  <ElDropdown trigger="click" @command="handleCommand">
    <ElButton type="primary" text circle class="h-8 w-8">
      <Languages class="h-4 w-4" />
      <span class="sr-only">Toggle language</span>
    </ElButton>
    <template #dropdown>
      <ElDropdownMenu>
        <ElDropdownItem
          v-for="lang in languages"
          :key="lang.value"
          :command="lang.value"
          :class="{ 'bg-slate-100': locale === lang.value }"
        >
          {{ lang.label }}
        </ElDropdownItem>
      </ElDropdownMenu>
    </template>
  </ElDropdown>
</template>
