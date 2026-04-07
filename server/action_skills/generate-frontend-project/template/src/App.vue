<template>
  <RouterView />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const appStore = useAppStore()
const authStore = useAuthStore()

onMounted(() => {
  appStore.initializeTheme()
  authStore.ensureSession()
})
</script>
