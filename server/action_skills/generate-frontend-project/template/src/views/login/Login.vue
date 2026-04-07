<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Lock, User } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Captcha from './components/Captcha.vue'

const route = useRoute()
const authStore = useAuthStore()

const APP_TITLE = import.meta.env.VITE_APP_TITLE as string
const APP_SUBTITLE = import.meta.env.VITE_APP_SUBTITLE as string
const CAPTCHA_ENABLED = import.meta.env.VITE_CAPTCHA_ENABLED === 'true'

const formRef = ref<FormInstance>()
const captchaKey = ref('')
const loading = ref(false)

const formModel = reactive({
  account: '',
  password: '',
  captcha: '',
  remember: false,
})

const rules: FormRules<typeof formModel> = {
  account: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
  ],
  ...(CAPTCHA_ENABLED && {
    captcha: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
  }),
}

const handleCaptchaChange = (key: string) => {
  captchaKey.value = key
}

const handleSubmit = async () => {
  const isValid = await formRef.value?.validate().catch(() => false)

  if (!isValid) {
    return
  }

  loading.value = true

  try {
    const loginPayload = {
      account: formModel.account,
      password: formModel.password,
      remember: formModel.remember,
      ...(CAPTCHA_ENABLED && {
        captcha: formModel.captcha,
        captchaKey: captchaKey.value,
      }),
    }

    await authStore.login(loginPayload)
    ElMessage.success('登录成功')
    const redirect = route.query.redirect?.toString()
    await authStore.redirectAfterLogin(redirect)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen">
    <div class="hidden w-1/2 flex-col justify-between bg-[var(--app-primary)] p-12 text-white lg:flex">
      <div>
        <div class="text-2xl font-bold">{{ APP_TITLE }}</div>
        <div class="mt-1 text-sm text-white/70">{{ APP_SUBTITLE }}</div>
      </div>

      <div class="space-y-8">
        <h1 class="text-4xl font-bold leading-tight">
          高效、简洁的<br>
          业务管理系统
        </h1>
        <p class="text-lg text-white/80">
          基于 Vue 3 + TypeScript 构建，提供完善的权限管理、数据可视化和工作流支持
        </p>
      </div>

      <div class="space-y-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-full bg-white/10">
            <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
          </div>
          <span class="text-sm text-white/80">开箱即用的功能组件</span>
        </div>
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-full bg-white/10">
            <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
          </div>
          <span class="text-sm text-white/80">响应式设计，适配多端</span>
        </div>
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-full bg-white/10">
            <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
          </div>
          <span class="text-sm text-white/80">灵活的权限控制体系</span>
        </div>
      </div>

      <div class="text-sm text-white/50">
        © 2024 {{ APP_TITLE }}. All rights reserved.
      </div>
    </div>

    <div class="flex w-full items-center justify-center bg-[var(--app-bg)] p-6 lg:w-1/2">
      <div class="w-full max-w-md">
        <div class="mb-8 lg:hidden">
          <div class="text-2xl font-bold text-[var(--app-text)]">{{ APP_TITLE }}</div>
          <div class="mt-1 text-sm text-[var(--app-text-secondary)]">{{ APP_SUBTITLE }}</div>
        </div>

        <div class="mb-8">
          <h2 class="text-2xl font-bold text-[var(--app-text)]">欢迎回来</h2>
          <p class="mt-2 text-sm text-[var(--app-text-secondary)]">
            请登录您的账号以继续使用系统
          </p>
        </div>

        <el-form
          ref="formRef"
          :model="formModel"
          :rules="rules"
          label-position="top"
          class="space-y-5"
          @keyup.enter="handleSubmit"
        >
          <el-form-item label="账号" prop="account">
            <el-input
              v-model="formModel.account"
              :prefix-icon="User"
              placeholder="请输入账号"
              size="large"
              class="h-12"
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="formModel.password"
              :prefix-icon="Lock"
              show-password
              placeholder="请输入密码"
              size="large"
              class="h-12"
            />
          </el-form-item>

          <el-form-item v-if="CAPTCHA_ENABLED" label="验证码" prop="captcha">
            <Captcha @change="handleCaptchaChange" />
          </el-form-item>

          <div class="flex items-center justify-between">
            <el-checkbox v-model="formModel.remember" class="text-sm">
              <span class="text-[var(--app-text-secondary)]">记住我</span>
            </el-checkbox>
            <router-link
              to="/reset-password"
              class="text-sm text-[var(--app-primary)] hover:text-[var(--app-primary-hover)]"
            >
              忘记密码？
            </router-link>
          </div>

          <el-button
            type="primary"
            size="large"
            class="h-12 w-full text-base font-medium"
            :loading="loading"
            @click="handleSubmit"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form>

        <div class="mt-6 text-center text-sm text-[var(--app-text-secondary)]">
          还没有账号？
          <router-link
            to="/register"
            class="font-medium text-[var(--app-primary)] hover:text-[var(--app-primary-hover)]"
          >
            立即注册
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
