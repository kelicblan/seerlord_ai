import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { usePreferredDark } from '@vueuse/core'

export type ThemeMode = 'light' | 'dark' | 'system'

export const useAppStore = defineStore(
  'app',
  () => {
    const themeMode = ref<ThemeMode>('system')
    const sidebarCollapsed = ref(false)
    const preferredDark = usePreferredDark()

    const resolvedTheme = computed<'light' | 'dark'>(() => {
      if (themeMode.value === 'system') {
        return preferredDark.value ? 'dark' : 'light'
      }

      return themeMode.value
    })

    const applyTheme = (theme: 'light' | 'dark') => {
      const rootElement = document.documentElement
      rootElement.classList.toggle('dark', theme === 'dark')
      rootElement.dataset.theme = theme
    }

    const initializeTheme = () => {
      applyTheme(resolvedTheme.value)
    }

    watch(resolvedTheme, applyTheme, { immediate: true })

    return {
      themeMode,
      sidebarCollapsed,
      resolvedTheme,
      initializeTheme,
    }
  },
  {
    persist: {
      key: 'app-preferences',
      pick: ['themeMode', 'sidebarCollapsed'],
    },
  },
)
