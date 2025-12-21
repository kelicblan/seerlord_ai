<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Loader2, Apple, Chrome } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useAuth } from '@/composables/useAuth'
import barVideo from '@/assets/images/bar.mp4'
import barPoster from '@/assets/images/bar.jpg'

const router = useRouter()
const { login } = useAuth()
const { t } = useI18n()

const username = ref('')
const password = ref('')
const error = ref('')
const isLoading = ref(false)
const rememberMe = ref(true)
const currentYear = new Date().getFullYear()

// 执行登录：成功后跳转到首页；失败时展示错误提示
const handleLogin = async () => {
  isLoading.value = true
  error.value = ''
  try {
    await login(username.value, password.value, rememberMe.value)
    router.push('/')
  } catch (e) {
    error.value = t('login.error_invalid')
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

// 忘记密码：当前后台未接入找回流程，先引导联系管理员
const handleForgotPassword = () => {
  ElMessage.info(t('login.toast_help_desc'))
}

// 三方登录：仅展示入口样式，未接入后端 OAuth 流程
const handleSocialLogin = (provider: 'google' | 'apple') => {
  ElMessage.info(t('login.toast_coming_desc', { provider: provider === 'google' ? t('login.provider_google') : t('login.provider_apple') }))
}

// 创建账号：当前后台未开放注册，先给出提示
const handleCreateAccount = () => {
  ElMessage.info(t('login.toast_signup_desc'))
}
</script>

<template>
  <div class="min-h-screen bg-muted/30 text-foreground flex items-center justify-center p-6">
    <div class="w-full max-w-[1120px] overflow-hidden rounded-3xl border bg-card shadow-xl lg:h-[680px]">
      <div class="grid h-full grid-cols-1 lg:grid-cols-2">
        <div class="relative overflow-hidden border-b border-border min-h-[340px] lg:min-h-0 lg:border-b-0 lg:border-r">
        <div class="absolute inset-0">
          <video
            class="absolute inset-0 h-full w-full object-cover opacity-90"
            :src="barVideo"
            :poster="barPoster"
            autoplay
            muted
            loop
            playsinline
            preload="auto"
          ></video>
          <div class="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-primary/30 blur-3xl" />
          <div class="absolute -bottom-28 -right-28 h-80 w-80 rounded-full bg-secondary/40 blur-3xl" />
          <div class="absolute inset-0 bg-gradient-to-b from-black/0 via-black/10 to-black/60" />
        </div>

        <div class="relative flex h-full flex-col justify-between p-10">
          <div class="inline-flex items-center gap-2">
            <div class="h-9 w-9 rounded-lg bg-primary/15 ring-1 ring-primary/25" />
            <div class="text-base font-semibold tracking-wide">SEERLORD AI</div>
          </div>

          <div class="space-y-4">
            <div class="text-4xl font-semibold leading-tight">
              {{ t('login.hero_title') }}
            </div>
            <div class="max-w-sm text-sm/6 text-white/70">
              {{ t('login.hero_desc') }}
            </div>
          </div>

          <div class="text-xs text-white/60">
            © {{ currentYear }} SeerLord AI
          </div>
        </div>
        </div>

        <div class="flex items-center justify-center p-8 lg:p-12">
          <div class="w-full max-w-md space-y-7">
            <div class="space-y-2">
              <div class="text-3xl font-semibold tracking-tight">{{ t('login.title') }}</div>
              <div class="text-sm text-muted-foreground">{{ t('login.subtitle') }}</div>
            </div>

            <form @submit.prevent="handleLogin" class="space-y-5">
              <div class="space-y-2">
                <label for="username" class="text-sm font-medium">{{ t('login.username_label') }}</label>
                <ElInput
                  id="username"
                  v-model="username"
                  size="large"
                  :placeholder="t('login.username_placeholder')"
                  autocomplete="username"
                  required
                />
              </div>

              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <label for="password" class="text-sm font-medium">{{ t('login.password_label') }}</label>
                  <ElButton
                    type="primary"
                    native-type="button"
                    link
                    class="h-auto p-0 text-xs"
                    @click="handleForgotPassword"
                  >
                    {{ t('login.forgot_password') }}
                  </ElButton>
                </div>
                <ElInput
                  id="password"
                  v-model="password"
                  type="password"
                  show-password
                  size="large"
                  :placeholder="t('login.password_placeholder')"
                  autocomplete="current-password"
                  required
                />
              </div>

              <div class="flex items-center justify-between">
                <label class="flex items-center gap-2 text-sm text-muted-foreground select-none">
                  <ElCheckbox v-model="rememberMe" />
                  <span>{{ t('login.remember_me') }}</span>
                </label>
              </div>

              <div v-if="error" class="text-sm text-destructive">{{ error }}</div>

              <ElButton type="primary" native-type="submit" class="w-full h-11" :loading="isLoading">
                <template #loading>
                  <Loader2 class="mr-2 h-4 w-4 animate-spin" />
                </template>
                {{ isLoading ? t('login.btn_loading') : t('login.btn_submit') }}
              </ElButton>
            </form>

            <div class="relative">
              <div class="h-px w-full bg-border" />
              <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-2 text-xs text-muted-foreground">
                {{ t('login.or') }}
              </div>
            </div>

            <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <ElButton type="default" class="w-full h-11" @click="handleSocialLogin('google')">
                <Chrome class="mr-2 h-4 w-4" />
                {{ t('login.continue_google') }}
              </ElButton>
              <ElButton type="default" class="w-full h-11" @click="handleSocialLogin('apple')">
                <Apple class="mr-2 h-4 w-4" />
                {{ t('login.continue_apple') }}
              </ElButton>
            </div>

            <div class="text-center text-sm text-muted-foreground">
              {{ t('login.no_account') }}
              <ElButton type="primary" link class="h-auto p-0 text-sm" @click="handleCreateAccount">
                {{ t('login.create_account') }}
              </ElButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
