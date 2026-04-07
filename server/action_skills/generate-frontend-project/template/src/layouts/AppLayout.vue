<script setup lang="ts">
import { Expand, Fold, SwitchButton } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import appLogo from '@/assets/logo.png'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { menuConfig, type MenuGroup } from '@/router/routes/menu'

const APP_TITLE = import.meta.env.VITE_APP_TITLE as string
const APP_SUBTITLE = import.meta.env.VITE_APP_SUBTITLE as string

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()
const sidebarVisible = ref(false)
const userMenuExpanded = ref(false)
const { sidebarCollapsed } = storeToRefs(appStore)

const filteredMenuConfig = computed<MenuGroup[]>(() => {
  return menuConfig
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) => !item.permission || authStore.permissions.includes(item.permission)
      ),
    }))
    .filter((group) => group.items.length > 0)
})

const pageTitle = computed(() => route.meta.title || '首页')
const desktopSidebarClass = computed(() =>
  sidebarCollapsed.value ? 'w-[64px]' : 'w-[240px]',
)
const desktopContentClass = computed(() =>
  sidebarCollapsed.value ? 'lg:pl-[64px]' : 'lg:pl-[240px]',
)

const isActivePath = (path: string) => {
  if (path === '/') {
    return route.path === path
  }

  return route.path.startsWith(path)
}

const handleNavigate = async (path: string) => {
  if (route.path !== path) {
    await router.push(path)
  }
}

const handleCommand = async (command: string | number | object) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
      await authStore.logout()
    } catch {
      // 用户取消
    }
  }
}

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

watch(
  () => route.fullPath,
  () => {
    sidebarVisible.value = false
  },
)
</script>

<template>
  <div class="min-h-screen bg-[var(--app-bg)] text-[var(--app-text)]">
    <aside
      class="fixed inset-y-0 left-0 z-30 hidden overflow-hidden bg-[var(--app-surface)] shadow-lg backdrop-blur transition-[width] duration-200 lg:flex lg:flex-col"
      :class="desktopSidebarClass"
    >
      <div class="px-3 py-3" :class="sidebarCollapsed ? 'px-2' : 'px-3'">
        <div class="flex items-center gap-2" :class="sidebarCollapsed ? 'justify-center' : ''">
          <img :src="appLogo" alt="系统 Logo" class="h-9 w-9 rounded-lg object-cover">
          <div v-if="!sidebarCollapsed" class="min-w-0">
            <div class="truncate text-sm font-semibold">{{ APP_TITLE }}</div>
            <div class="mt-0.5 text-xs text-[var(--app-text-secondary)]">{{ APP_SUBTITLE }}</div>
          </div>
        </div>
      </div>

      <div class="sidebar-scroll flex-1 space-y-3 overflow-y-auto px-2 py-3">
        <section
          v-for="group in filteredMenuConfig"
          :key="group.title"
          class="rounded-lg bg-[var(--app-surface-strong)] p-2"
        >
          <div
            v-if="!sidebarCollapsed"
            class="px-1.5 text-[11px] font-medium uppercase tracking-[0.22em] text-[#999]"
          >
            {{ group.title }}
          </div>
          <div :class="sidebarCollapsed ? 'space-y-1.5' : 'mt-2 space-y-1'">
            <button
              v-for="item in group.items"
              :key="item.path"
              type="button"
              class="flex h-[38px] w-full cursor-pointer rounded-lg text-left transition-all duration-150"
              :class="
                isActivePath(item.path)
                  ? sidebarCollapsed
                    ? 'items-center justify-center bg-[var(--app-primary)] px-0 text-white'
                    : 'items-center gap-2 bg-[var(--app-primary)] px-2 text-white'
                  : sidebarCollapsed
                    ? 'items-center justify-center px-0 text-[var(--app-text)] hover:bg-[var(--app-primary)]/10 hover:text-[var(--app-primary)]'
                    : 'items-center gap-2 px-2 text-[var(--app-text)] hover:bg-[var(--app-primary)]/10 hover:text-[var(--app-primary)]'
              "
              :title="item.label"
              @click="handleNavigate(item.path)"
            >
              <span
                class="flex h-6 w-6 shrink-0 items-center justify-center rounded"
                :class="isActivePath(item.path) ? 'bg-white/20' : 'bg-[var(--app-muted-surface)]'"
              >
                <el-icon class="text-sm"><component :is="item.icon" /></el-icon>
              </span>
              <div v-if="!sidebarCollapsed" class="min-w-0 flex-1 self-center">
                <div class="truncate text-sm font-medium">{{ item.label }}</div>
              </div>
            </button>
          </div>
        </section>
      </div>

      <div class="px-2 py-3">
        <div v-if="sidebarCollapsed" class="flex flex-col items-center gap-2">
          <button
            type="button"
            class="flex h-8 w-8 cursor-pointer items-center justify-center rounded bg-[var(--app-surface)] hover:bg-[var(--app-primary)]/10"
            title="展开导航"
            @click="toggleSidebar"
          >
            <el-icon class="text-xs"><Expand /></el-icon>
          </button>
          <button
            type="button"
            class="flex h-8 w-8 cursor-pointer items-center justify-center rounded bg-[var(--app-surface-strong)] hover:bg-[var(--app-primary)]/10"
            title="退出登录"
            @click="handleCommand('logout')"
          >
            <el-icon class="text-xs"><SwitchButton /></el-icon>
          </button>
          <ThemeToggle />
        </div>
        <div v-else class="space-y-2">
          <div class="flex items-center justify-end gap-1">
            <button
              type="button"
              class="flex h-8 w-8 cursor-pointer items-center justify-center rounded bg-[var(--app-surface)] hover:bg-[var(--app-primary)]/10"
              title="收起导航"
              @click="toggleSidebar"
            >
              <el-icon class="text-xs"><Fold /></el-icon>
            </button>
            <ThemeToggle />
            <button
              type="button"
              class="flex h-8 w-8 cursor-pointer items-center justify-center rounded bg-[var(--app-surface-strong)] hover:bg-[var(--app-primary)]/10"
              title="账户操作"
              @click="handleCommand('logout')"
            >
              <el-icon class="text-xs"><SwitchButton /></el-icon>
            </button>
          </div>
          <div
            class="flex items-center rounded-lg bg-[var(--app-muted-surface)] p-2"
          >
            <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-[#999] text-sm font-semibold text-white">
              {{ authStore.userName.slice(0, 1) || 'A' }}
            </span>
            <div class="min-w-0 flex-1 pl-2">
              <div class="truncate text-sm font-medium">{{ authStore.userName || '系统管理员' }}</div>
              <div class="mt-0.5 text-xs text-[var(--app-text-secondary)]">演示账号：admin</div>
            </div>
          </div>
        </div>
        <div
          v-if="sidebarCollapsed && userMenuExpanded"
          class="fixed left-[68px] z-50 mt-2 w-48 rounded-lg bg-[var(--app-surface-strong)] p-2 shadow-lg"
        >
          <div class="mb-2 flex items-center gap-2 border-b border-[var(--app-border)] pb-2">
            <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-[#999] text-sm font-semibold text-white">
              {{ authStore.userName.slice(0, 1) || 'A' }}
            </span>
            <div class="min-w-0">
              <div class="truncate text-sm font-medium">{{ authStore.userName || '系统管理员' }}</div>
              <div class="truncate text-xs text-[var(--app-text-secondary)]">演示账号：admin</div>
            </div>
          </div>
          <div class="space-y-1">
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-[var(--app-primary)]/10 hover:text-[var(--app-primary)]"
              @click="handleCommand('logout')"
            >
              <el-icon class="text-xs"><SwitchButton /></el-icon>
              <span>退出登录</span>
            </button>
          </div>
        </div>
      </div>
    </aside>

    <div :class="desktopContentClass">
      <main class="bg-white p-2 min-h-screen">
        <div class="w-full">
          <div class="mb-2 flex items-center justify-between rounded-lg bg-[var(--app-surface)] px-3 py-2 lg:hidden">
            <div class="flex min-w-0 items-center gap-2">
              <button
                type="button"
                class="flex h-8 w-8 cursor-pointer items-center justify-center rounded bg-[var(--app-surface-strong)] hover:bg-[var(--app-primary)]/10"
                @click="sidebarVisible = true"
              >
                <el-icon class="text-xs"><Expand /></el-icon>
              </button>
              <div class="min-w-0">
                <div class="truncate text-sm font-semibold">{{ pageTitle }}</div>
                <div class="mt-0.5 text-xs text-[var(--app-text-secondary)]">
                  {{ APP_SUBTITLE }}
                </div>
              </div>
            </div>
            <img :src="appLogo" alt="系统 Logo" class="h-8 w-8 rounded object-cover">
          </div>
          <RouterView />
        </div>
      </main>
    </div>

    <el-drawer v-model="sidebarVisible" :with-header="false" direction="ltr" size="280px">
      <div class="flex h-full flex-col">
        <div class="flex items-center justify-between pb-3">
          <div>
            <div class="text-sm font-semibold">导航菜单</div>
            <div class="mt-0.5 text-xs text-[var(--app-text-secondary)]">选择模板页面</div>
          </div>
          <button
            type="button"
            class="flex h-8 w-8 cursor-pointer items-center justify-center rounded bg-[var(--app-surface-strong)]"
            @click="sidebarVisible = false"
          >
            <el-icon class="text-xs"><Fold /></el-icon>
          </button>
        </div>

        <div class="mt-3 flex-1 space-y-3">
          <section v-for="group in filteredMenuConfig" :key="`${group.title}-drawer`" class="space-y-1.5">
            <div class="px-1 text-[11px] font-medium uppercase tracking-[0.22em] text-[#999]">
              {{ group.title }}
            </div>
            <button
              v-for="item in group.items"
              :key="`${item.path}-drawer`"
              type="button"
              class="flex h-[38px] w-full cursor-pointer items-center gap-2 rounded-lg px-3 text-left transition-all duration-150"
              :class="
                isActivePath(item.path)
                  ? 'bg-[var(--app-primary)] text-white'
                  : 'text-[var(--app-text)] hover:bg-[var(--app-primary)]/10 hover:text-[var(--app-primary)]'
              "
              @click="handleNavigate(item.path)"
            >
              <el-icon class="text-xs"><component :is="item.icon" /></el-icon>
              <span class="text-sm font-medium">{{ item.label }}</span>
            </button>
          </section>
        </div>

        <div class="pt-3">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-xs uppercase tracking-[0.18em] text-[var(--app-text-tertiary)]">界面模式</div>
              <div class="mt-0.5 text-xs font-medium">主题切换</div>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>
