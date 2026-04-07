<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElConfigProvider } from 'element-plus'

const isDark = ref(false)

onMounted(() => {
  isDark.value = document.documentElement.classList.contains('dark')
})
</script>

<template>
  <el-config-provider :locale="{ name: 'zhCn', el: {} }">
    <div 
      class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors duration-300 relative overflow-hidden"
    >
      <!-- Background decoration -->
      <div class="absolute inset-0 overflow-hidden">
        <div class="absolute -top-40 -right-40 w-80 h-80 bg-blue-400 rounded-full opacity-10 blur-3xl" />
        <div class="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-400 rounded-full opacity-10 blur-3xl" />
        <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-green-400 rounded-full opacity-5 blur-3xl" />
      </div>

      <!-- Grid pattern overlay -->
      <div class="absolute inset-0 bg-grid-pattern opacity-5" />

      <!-- Content -->
      <div class="relative z-10 w-full max-w-md px-4">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>

      <!-- Footer -->
      <div class="absolute bottom-4 left-0 right-0 text-center">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          © 2024 管理系统. All rights reserved.
        </p>
      </div>
    </div>
  </el-config-provider>
</template>

<style scoped>
.bg-grid-pattern {
  background-image: 
    linear-gradient(to right, rgba(156, 163, 175, 0.1) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(156, 163, 175, 0.1) 1px, transparent 1px);
  background-size: 24px 24px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
