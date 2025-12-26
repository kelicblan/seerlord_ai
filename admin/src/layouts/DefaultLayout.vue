<script setup lang="ts">
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  LayoutDashboard,
  Users,
  Bot,
  Server,
  MessageSquare,
  Zap,
  Settings,
  CircleHelp,
  MoreHorizontal,
  Library,
  FileText,
  Code,
  Share2
} from 'lucide-vue-next'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import { useAuth } from '@/composables/useAuth'
import { useMediaQuery } from '@vueuse/core'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { user, logout, fetchUser } = useAuth()
const isLg = useMediaQuery('(min-width: 1024px)')
const splitterLayout = computed(() => (isLg.value ? 'horizontal' : 'vertical'))
const leftPanelSize = ref<string | number>('234px')
const rightPanelSize = ref<string | number>('75%')
onMounted(() => {
  fetchUser()
})

const navItems = computed(() => [
  { name: t('common.nav_agent'), path: '/', icon: LayoutDashboard },
  { name: t('common.nav_user_mgmt'), path: '/users', icon: Users },
  { name: t('common.nav_agent_mgmt'), path: '/agents', icon: Bot },
  { name: t('common.nav_mcp_mgmt'), path: '/mcp', icon: Server },
  { name: t('common.nav_history'), path: '/history', icon: MessageSquare },
  { name: t('common.nav_skills'), path: '/skills', icon: Zap },
  { name: t('common.nav_knowledge'), path: '/knowledge', icon: Library },
  { name: t('common.nav_knowledge_graph'), path: '/knowledge-graph', icon: Share2 },
  { name: t('common.nav_content_plaza'), path: '/content-plaza', icon: FileText },
  { name: t('common.nav_api_platform'), path: '/api-platform', icon: Code },
])

const handleAccountCommand = (command: string) => {
  if (command === 'logout') logout()
}
</script>

<template>
  <div class="flex h-screen bg-background text-foreground">
    <ElSplitter class="h-full" :layout="splitterLayout" lazy>
      <ElSplitterPanel class="overflow-hidden h-full" v-model:size="leftPanelSize" collapsible min="155">
        <!-- Sidebar -->
        <aside class="w-64 border-r border-border bg-card flex flex-col  h-full overflow-hidden">
          <div class="p-4">
            <h3 class="text-base font-bold text-primary">SEERLORD AI ADMIN</h3>
          </div>
          <nav class="space-y-1 px-2 flex-1" style="font-size: 14px;">
            <RouterLink v-for="item in navItems" :key="item.path" :to="item.path"
              class="flex items-center gap-3 px-4 py-3 rounded-lg transition-colors" :class="[
                route.path === item.path
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              ]">
              <component :is="item.icon" class="w-5 h-5" />
              <span>{{ item.name }}</span>
            </RouterLink>
          </nav>

          <div class="px-2 pb-3 pt-2">
            <div class="h-px bg-border my-2" />

            <div class="space-y-1">
              <div
                class="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors cursor-pointer"
                :class="[
                  route.path === '/settings'
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                ]"
                role="button"
                @click="router.push('/settings')">
                <Settings class="w-5 h-5" />
                <span class="flex-1 text-left">{{ t('common.settings') }}</span>
                <div class="shrink-0 -mr-2" @click.stop>
                  <LanguageSwitcher />
                </div>
              </div>

              <RouterLink to="/help"
                class="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors"
                :class="[
                  route.path === '/help'
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                ]">
                <CircleHelp class="w-5 h-5" />
                <span class="text-left">{{ t('common.get_help') }}</span>
              </RouterLink>

              <!-- <button type="button"
                class="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors hover:bg-muted text-muted-foreground hover:text-foreground">
                <Search class="w-5 h-5" />
                <span class="text-left">{{ t('common.search') }}</span>
              </button> -->
            </div>

            <div class="mt-2  w-full">
              <ElDropdown class="w-full" v-if="user" trigger="click" @command="handleAccountCommand">
                <div class="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors hover:bg-muted">
                  <div
                    class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold border border-primary/20 shrink-0">
                    {{ user.username?.charAt(0).toUpperCase() }}
                  </div>
                  <div class="min-w-0 flex-1 text-left">
                    <div class="text-sm font-medium text-foreground truncate">{{ user.username }}</div>
                    <div class="text-xs text-muted-foreground truncate">
                      {{ user.is_superuser ? t('user_mgmt.role_admin') : t('user_mgmt.role_user') }}
                    </div>
                  </div>
                  <MoreHorizontal class="w-4 h-4 text-muted-foreground" />
                </div>
                <template #dropdown>
                  <ElDropdownMenu class="w-44">
                    <div class="px-2 py-1.5 text-sm font-semibold opacity-50">My Account</div>
                    <div class="h-px bg-border my-1" />
                    <ElDropdownItem command="logout" class="text-red-500">
                      Log out
                    </ElDropdownItem>
                  </ElDropdownMenu>
                </template>
              </ElDropdown>
            </div>
          </div>
        </aside>
      </ElSplitterPanel>

      <ElSplitterPanel class="overflow-hidden h-full" v-model:size="rightPanelSize" collapsible min="320">
        <!-- Main Content -->
        <main class="flex-1 flex flex-col overflow-hidden">
          <header class="border-b border-border bg-card p-4 flex items-center justify-between shrink-0">
            <h2 class="text-base font-semibold">{{ t(route.meta.title as string) }}</h2>
          </header>
          <div class="flex-1 overflow-auto p-2">
            <RouterView />
          </div>
        </main>
      </ElSplitterPanel>
    </ElSplitter>
  </div>
</template>
<style scoped>
:deep(.overflow-hidden) {
  overflow: hidden !important;
}
</style>
