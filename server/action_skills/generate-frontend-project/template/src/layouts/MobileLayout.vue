<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElConfigProvider, ElIcon, ElAvatar } from 'element-plus'
import { 
  User, 
  Search 
} from '@element-plus/icons-vue'

interface TabItem {
  index: string
  title: string
  icon: string
  badge?: number
}

const route = useRoute()
const router = useRouter()

const isDark = ref(false)
const showHeader = ref(true)
const lastScrollY = ref(0)

const tabItems: TabItem[] = [
  { index: '/', title: '首页', icon: 'HomeFilled' },
  { index: '/discover', title: '发现', icon: 'Search' },
  { index: '/cart', title: '购物车', icon: 'ShoppingCart', badge: 0 },
  { index: '/notifications', title: '消息', icon: 'Bell', badge: 3 },
  { index: '/profile', title: '我的', icon: 'User' }
]

const activeTab = computed(() => {
  const current = tabItems.find(item => item.index === route.path)
  return current?.index || '/'
})

const handleTabClick = (index: string) => {
  router.push(index)
}

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
}

const handleScroll = (event: Event) => {
  const target = event.target as HTMLElement
  const currentScrollY = target.scrollTop

  if (currentScrollY > lastScrollY.value && currentScrollY > 60) {
    showHeader.value = false
  } else {
    showHeader.value = true
  }

  lastScrollY.value = currentScrollY
}
</script>

<template>
  <el-config-provider :locale="{ name: 'zhCn', el: {} }">
    <div
      class="flex flex-col h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300"
    >
      <!-- Header -->
      <header
        class="fixed top-0 left-0 right-0 z-50 bg-white dark:bg-gray-800 shadow-sm transition-transform duration-300"
        :class="{ '-translate-y-full': !showHeader }"
      >
        <div class="flex items-center justify-between h-14 px-4">
          <div class="flex items-center flex-1">
            <el-avatar :size="32" class="mr-3 bg-blue-500">
              <el-icon><User /></el-icon>
            </el-avatar>
            <div class="text-lg font-semibold text-gray-800 dark:text-white">
              Logo
            </div>
          </div>

          <div class="flex items-center space-x-3">
            <el-button text circle class="touch-manipulation" @click="toggleTheme">
              <el-icon size="20">
                <span v-if="isDark">☀️</span>
                <span v-else>🌙</span>
              </el-icon>
            </el-button>
            <el-button text circle class="touch-manipulation">
              <el-icon size="20"><Search /></el-icon>
            </el-button>
          </div>
        </div>
      </header>

      <!-- Main Content Area -->
      <main
        class="flex-1 overflow-y-auto pt-14 pb-20"
        @scroll="handleScroll"
      >
        <RouterView />
      </main>

      <!-- Bottom Tab Bar -->
      <nav class="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 z-50">
        <div class="flex justify-around items-center h-16">
          <button
            v-for="item in tabItems"
            :key="item.index"
            class="flex flex-col items-center justify-center flex-1 h-full touch-manipulation transition-colors"
            :class="activeTab === item.index ? 'text-blue-500' : 'text-gray-500'"
            @click="handleTabClick(item.index)"
          >
            <div class="relative">
              <el-icon :size="22">
                <User v-if="item.icon === 'User'" />
                <Search v-else-if="item.icon === 'Search'" />
              </el-icon>
              <span
                v-if="item.badge"
                class="absolute -top-1 -right-1 min-w-[16px] h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center px-1"
              >
                {{ item.badge > 99 ? '99+' : item.badge }}
              </span>
            </div>
            <span class="text-xs mt-1">{{ item.title }}</span>
          </button>
        </div>
      </nav>

      <!-- FAB Button -->
      <el-button
        class="fixed bottom-20 right-4 w-12 h-12 rounded-full bg-blue-500 text-white shadow-lg"
        circle
      >
        <el-icon size="24"><Search /></el-icon>
      </el-button>
    </div>
  </el-config-provider>
</template>
