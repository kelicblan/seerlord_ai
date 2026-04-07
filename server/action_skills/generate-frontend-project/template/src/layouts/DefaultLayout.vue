<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMenu, ElMenuItem, ElSubMenu, ElIcon, ElBreadcrumb, ElBreadcrumbItem, ElDropdown, ElDropdownMenu, ElDropdownItem, ElAvatar, ElSwitch, ElConfigProvider } from 'element-plus'
import { 
  HomeFilled, 
  User, 
  Setting, 
  SwitchButton, 
  Fold, 
  Expand, 
  Sunny, 
  Moon 
} from '@element-plus/icons-vue'

interface MenuItem {
  index: string
  title: string
  icon?: string
  children?: MenuItem[]
}

const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)
const isMobile = ref(false)
const isDark = ref(false)

const menuItems: MenuItem[] = [
  {
    index: '/',
    title: '首页',
    icon: 'HomeFilled'
  },
  {
    index: '/dashboard',
    title: '仪表盘',
    icon: 'DataBoard'
  },
  {
    index: '2',
    title: '系统管理',
    icon: 'Setting',
    children: [
      { index: '/users', title: '用户管理' },
      { index: '/roles', title: '角色管理' },
      { index: '/permissions', title: '权限管理' }
    ]
  },
  {
    index: '3',
    title: '业务模块',
    icon: 'Goods',
    children: [
      { index: '/orders', title: '订单管理' },
      { index: '/products', title: '产品管理' }
    ]
  }
]

const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta?.title)
  return matched.map(item => ({
    path: item.path,
    title: item.meta?.title || item.name
  }))
})

const userInfo = ref({
  name: '管理员',
  avatar: ''
})

const handleMenuSelect = (index: string) => {
  if (index.startsWith('/')) {
    router.push(index)
  }
}

const handleLogout = () => {
  router.push('/login')
}

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

const toggleTheme = (val: string | number | boolean) => {
  const isDarkMode = Boolean(val)
  isDark.value = isDarkMode
  document.documentElement.classList.toggle('dark', isDarkMode)
}

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value && !isCollapsed.value) {
    isCollapsed.value = true
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  isDark.value = document.documentElement.classList.contains('dark')
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<template>
  <el-config-provider :locale="{ name: 'zhCn', el: {} }">
    <div class="flex h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      <!-- Sidebar -->
      <aside 
        :class="[
          'fixed lg:static inset-y-0 left-0 z-30 bg-white dark:bg-gray-800 shadow-lg transition-all duration-300 ease-in-out',
          isCollapsed ? 'w-16' : 'w-64',
          isMobile && isCollapsed ? '-translate-x-full' : 'translate-x-0'
        ]"
      >
        <div class="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-700">
          <div v-if="!isCollapsed" class="flex items-center">
            <el-avatar :size="32" class="mr-2 bg-blue-500">
              <el-icon><User /></el-icon>
            </el-avatar>
            <span class="text-lg font-semibold text-gray-800 dark:text-white">管理系统</span>
          </div>
          <el-button 
            v-if="!isMobile" 
            text 
            class="ml-auto"
            @click="toggleSidebar"
          >
            <el-icon size="20">
              <Fold v-if="!isCollapsed" />
              <Expand v-else />
            </el-icon>
          </el-button>
        </div>

        <el-menu
          :default-active="route.path"
          :collapse="isCollapsed"
          :collapse-transition="false"
          class="h-[calc(100vh-4rem)] border-none bg-transparent dark:bg-transparent"
          @select="handleMenuSelect"
        >
          <template v-for="item in menuItems" :key="item.index">
            <el-sub-menu v-if="item.children" :index="item.index">
              <template #title>
                <el-icon><component :is="item.icon" /></el-icon>
                <span>{{ item.title }}</span>
              </template>
              <el-menu-item 
                v-for="child in item.children" 
                :key="child.index" 
                :index="child.index"
              >
                {{ child.title }}
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="item.index">
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.title }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </aside>

      <!-- Mobile Overlay -->
      <div 
        v-if="isMobile && !isCollapsed" 
        class="fixed inset-0 bg-black bg-opacity-50 z-20 lg:hidden"
        @click="toggleSidebar"
      />

      <!-- Main Content -->
      <div class="flex-1 flex flex-col min-w-0">
        <!-- Header -->
        <header class="h-16 bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 flex items-center px-4 lg:px-6">
          <el-button 
            v-if="isMobile" 
            text 
            class="mr-2"
            @click="toggleSidebar"
          >
            <el-icon size="20"><Fold /></el-icon>
          </el-button>

          <!-- Breadcrumb -->
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">
              <el-icon class="mr-1"><HomeFilled /></el-icon>
              首页
            </el-breadcrumb-item>
            <el-breadcrumb-item 
              v-for="crumb in breadcrumbs.slice(1)" 
              :key="crumb.path"
              :to="crumb.path"
            >
              {{ crumb.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>

          <div class="ml-auto flex items-center space-x-4">
            <!-- Theme Toggle -->
            <div class="flex items-center space-x-2">
              <el-icon><Sunny /></el-icon>
              <el-switch
                v-model="isDark"
                inline-prompt
                active-text=""
                inactive-text=""
                @change="toggleTheme"
              />
              <el-icon><Moon /></el-icon>
            </div>

            <!-- User Dropdown -->
            <el-dropdown trigger="click">
              <div class="flex items-center cursor-pointer">
                <el-avatar :size="32" class="mr-2">
                  <el-icon><User /></el-icon>
                </el-avatar>
                <span class="hidden md:inline text-gray-700 dark:text-gray-200">
                  {{ userInfo.name }}
                </span>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item>
                    <el-icon class="mr-2"><User /></el-icon>
                    个人中心
                  </el-dropdown-item>
                  <el-dropdown-item>
                    <el-icon class="mr-2"><Setting /></el-icon>
                    设置
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="handleLogout">
                    <el-icon class="mr-2"><SwitchButton /></el-icon>
                    退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </header>

        <!-- Page Content -->
        <main class="flex-1 p-4 lg:p-6 overflow-auto bg-gray-50 dark:bg-gray-900">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </main>
      </div>
    </div>
  </el-config-provider>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
