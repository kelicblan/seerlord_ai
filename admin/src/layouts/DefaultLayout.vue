<script setup lang="ts">
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { computed, onMounted, ref, reactive } from 'vue'
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
  Share2,
  Clock
} from 'lucide-vue-next'
import { ElMessage, type FormInstance } from 'element-plus'
import type { FormRules } from 'element-plus'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import { useAuth } from '@/composables/useAuth'
import { updatePassword } from '@/api/user'
import { useMediaQuery } from '@vueuse/core'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { user, fetchUser, logout } = useAuth()

// Responsive layout check
// 响应式布局检测
const isLg = useMediaQuery('(min-width: 1024px)')
const splitterLayout = computed(() => (isLg.value ? 'horizontal' : 'vertical'))
const leftPanelSize = ref<string | number>('234px')
const rightPanelSize = ref<string | number>('75%')

// Password Change State
// 密码修改状态
const passwordDialogVisible = ref(false)
const passwordFormRef = ref<FormInstance>()
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

/**
 * Validator for confirming password
 * 确认密码校验器
 */
const validatePass2 = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error(t('common.please_input_password')))
  } else if (value !== passwordForm.new_password) {
    callback(new Error(t('common.password_mismatch')))
  } else {
    callback()
  }
}

// Form Validation Rules
// 表单验证规则
const passwordRules = computed<FormRules>(() => ({
  old_password: [{ required: true, message: t('common.please_input_password'), trigger: 'blur' }],
  new_password: [{ required: true, message: t('common.please_input_password'), trigger: 'blur' }],
  confirm_password: [{ validator: validatePass2, trigger: 'blur' }]
}))

/**
 * Handle account dropdown commands
 * 处理账户下拉菜单命令
 */
const handleAccountCommand = (command: string) => {
  if (command === 'logout') {
    logout()
    router.push('/login')
  } else if (command === 'change_password') {
    passwordDialogVisible.value = true
  }
}

/**
 * Submit password change
 * 提交密码修改
 */
const submitPasswordChange = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  await formEl.validate(async (valid) => {
    if (valid) {
      try {
        await updatePassword({
          old_password: passwordForm.old_password,
          new_password: passwordForm.new_password
        })
        ElMessage.success(t('common.password_updated'))
        passwordDialogVisible.value = false
        // Reset form
        formEl.resetFields()
      } catch (error: any) {
        console.error(error)
        // Ideally error message should come from backend
        if (error.response?.data?.detail) {
             ElMessage.error(error.response.data.detail)
        } else {
             ElMessage.error(t('common.operation_failed')) // Fallback or generic error
        }
      }
    }
  })
}

onMounted(() => {
  fetchUser()
})

// Navigation Items Configuration
// 导航项配置
const navItems = computed(() => [
  { name: t('help.nav_agent'), path: '/chat', icon: MessageSquare },
  { name: t('help.nav_user_mgmt'), path: '/users', icon: Users, adminOnly: true },
  { name: t('help.nav_agent_mgmt'), path: '/agents', icon: Bot },
  { name: t('help.nav_automation'), path: '/automation', icon: Zap },
  { name: t('help.nav_mcp_mgmt'), path: '/mcp', icon: Server },
  { name: t('help.nav_history'), path: '/history', icon: Clock },
  { name: t('help.nav_skills'), path: '/skills', icon: Code },
  { name: t('help.nav_knowledge'), path: '/knowledge', icon: Library },
  { name: t('help.nav_knowledge_graph'), path: '/kl-graph', icon: Share2 },
  { name: t('help.nav_content_plaza'), path: '/plaza', icon: LayoutDashboard },
  { name: t('help.nav_api_platform'), path: '/api-platform', icon: FileText },
])
</script>

<template>
  <div class="h-screen w-screen bg-background flex flex-col overflow-hidden">
    <ElSplitter v-model="splitterLayout" class="flex-1 overflow-hidden">
      <ElSplitterPanel class="flex flex-col overflow-hidden bg-muted/30" v-model:size="leftPanelSize" min="234">
        <!-- Sidebar -->
        <aside class="flex flex-col h-full">
            <!-- Logo area -->
            <div class="p-4 flex items-center gap-2 font-bold text-xl text-primary shrink-0">
                <div class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground">
                    <Bot class="w-5 h-5" />
                </div>
                <span>SeerLord AI</span>
            </div>

            <!-- Navigation -->
            <nav class="flex-1 overflow-y-auto px-2 py-2 space-y-1">
                 <template v-for="item in navItems" :key="item.path">
                    <RouterLink 
                        v-if="!item.adminOnly || (user?.is_superuser)"
                        :to="item.path"
                        class="flex items-center gap-3 px-4 py-3 rounded-lg transition-colors"
                        :class="[
                            route.path.startsWith(item.path)
                            ? 'bg-primary text-primary-foreground'
                            : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                        ]"
                    >
                        <component :is="item.icon" class="w-5 h-5" />
                        <span class="text-sm font-medium">{{ item.name }}</span>
                    </RouterLink>
                 </template>
            </nav>

            <!-- Bottom actions -->
            <div class="p-4 border-t border-border shrink-0 space-y-2">
                <div class="flex items-center justify-between px-2">
                     <LanguageSwitcher />
                </div>

                <RouterLink to="/settings"
                    class="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors"
                    :class="[
                    route.path === '/settings'
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                    ]">
                    <Settings class="w-5 h-5" />
                    <span class="text-sm font-medium">{{ t('common.settings') }}</span>
                </RouterLink>

                <RouterLink to="/help"
                    class="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors"
                    :class="[
                    route.path === '/help'
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                    ]">
                    <CircleHelp class="w-5 h-5" />
                    <span class="text-sm font-medium">{{ t('common.get_help') }}</span>
                </RouterLink>

                <!-- User Profile -->
                <div class="pt-2">
                    <ElDropdown class="w-full" v-if="user" trigger="click" @command="handleAccountCommand">
                        <div class="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors hover:bg-muted cursor-pointer">
                            <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold border border-primary/20 shrink-0">
                                {{ user.username?.charAt(0).toUpperCase() }}
                            </div>
                            <div class="min-w-0 flex-1 text-left">
                                <div class="text-sm font-medium text-foreground truncate">{{ user.username }}</div>
                                <div class="text-xs text-muted-foreground truncate">
                                    {{ user.is_superuser ? 'Admin' : 'User' }}
                                </div>
                            </div>
                            <MoreHorizontal class="w-4 h-4 text-muted-foreground" />
                        </div>
                        <template #dropdown>
                            <ElDropdownMenu class="w-44">
                                <div class="px-4 py-2 text-xs font-semibold text-muted-foreground">{{ t('common.my_account') }}</div>
                                <div class="h-px bg-border my-1" />
                                <ElDropdownItem command="change_password">
                                    {{ t('common.change_password') }}
                                </ElDropdownItem>
                                <ElDropdownItem command="logout" class="text-red-500">
                                    {{ t('common.log_out') }}
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

    <!-- Password Change Dialog -->
    <ElDialog v-model="passwordDialogVisible" :title="t('common.change_password')" width="400px">
      <ElForm ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-position="top">
        <ElFormItem :label="t('common.old_password')" prop="old_password">
          <ElInput v-model="passwordForm.old_password" type="password" show-password />
        </ElFormItem>
        <ElFormItem :label="t('common.new_password')" prop="new_password">
          <ElInput v-model="passwordForm.new_password" type="password" show-password />
        </ElFormItem>
        <ElFormItem :label="t('common.confirm_password')" prop="confirm_password">
          <ElInput v-model="passwordForm.confirm_password" type="password" show-password />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <span class="dialog-footer">
          <ElButton @click="passwordDialogVisible = false">{{ t('common.cancel') }}</ElButton>
          <ElButton type="primary" @click="submitPasswordChange(passwordFormRef)">
            {{ t('common.confirm') }}
          </ElButton>
        </span>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
:deep(.el-splitter__resizer) {
    background-color: hsl(var(--border));
}
:deep(.overflow-hidden) {
  overflow: hidden !important;
}
</style>
