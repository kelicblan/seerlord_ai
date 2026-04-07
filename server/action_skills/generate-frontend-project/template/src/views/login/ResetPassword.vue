<script setup lang="ts">
import { Lock, Message, Phone, User } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, ref, watch, reactive } from 'vue'
import { useRouter } from 'vue-router'

type StepType = 'verify' | 'reset' | 'complete'

const router = useRouter()
const currentStep = ref<StepType>('verify')
const verifyType = ref<'email' | 'phone'>('email')
const loading = ref(false)
const formRef = ref<FormInstance>()
const resetFormRef = ref<FormInstance>()

const verifyForm = reactive({
  account: '',
  verifyCode: '',
})

const resetForm = reactive({
  password: '',
  confirmPassword: '',
})

const verifyRules: FormRules<typeof verifyForm> = {
  account: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (verifyType.value === 'email') {
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
          if (!emailRegex.test(value)) {
            callback(new Error('请输入有效的邮箱地址'))
          } else {
            callback()
          }
        } else {
          const phoneRegex = /^1[3-9]\d{9}$/
          if (!phoneRegex.test(value)) {
            callback(new Error('请输入有效的手机号码'))
          } else {
            callback()
          }
        }
      },
      trigger: 'blur',
    },
  ],
  verifyCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' },
  ],
}

const resetRules: FormRules<typeof resetForm> = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== resetForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

const stepIndex = computed(() => {
  const steps: StepType[] = ['verify', 'reset', 'complete']
  return steps.indexOf(currentStep.value)
})

const handleSendCode = async () => {
  const isValid = await formRef.value?.validateField('account').catch(() => false)

  if (!isValid) {
    return
  }

  loading.value = true

  try {
    await new Promise((resolve) => setTimeout(resolve, 1000))

    ElMessage.success(
      verifyType.value === 'email'
        ? `验证码已发送至邮箱 ${verifyForm.account}`
        : `验证码已发送至手机 ${verifyForm.account}`,
    )
  } catch {
    ElMessage.error('发送验证码失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const handleVerify = async () => {
  const isValid = await formRef.value?.validate().catch(() => false)

  if (!isValid) {
    return
  }

  loading.value = true

  try {
    await new Promise((resolve) => setTimeout(resolve, 1000))
    currentStep.value = 'reset'
  } catch {
    ElMessage.error('验证失败，请检查输入信息')
  } finally {
    loading.value = false
  }
}

const handleResetPassword = async () => {
  const isValid = await resetFormRef.value?.validate().catch(() => false)

  if (!isValid) {
    return
  }

  loading.value = true

  try {
    await new Promise((resolve) => setTimeout(resolve, 1000))
    currentStep.value = 'complete'
  } catch {
    ElMessage.error('重置密码失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const handleBackToLogin = () => {
  router.push('/login')
}

watch(verifyType, () => {
  verifyForm.verifyCode = ''
})
</script>

<template>
  <div class="surface-card mx-auto w-full max-w-md rounded-2xl p-8 shadow-lg">
    <div class="text-center">
      <h2 class="text-2xl font-semibold">重置密码</h2>
      <p class="mt-2 text-sm text-[var(--app-text-secondary)]">
        通过验证身份来找回您的账号
      </p>
    </div>

    <el-steps :active="stepIndex" class="mt-8" finish-status="success">
      <el-step title="验证身份" />
      <el-step title="重置密码" />
      <el-step title="完成" />
    </el-steps>

    <div class="mt-8">
      <div v-if="currentStep === 'verify'">
        <el-form
          ref="formRef"
          :model="verifyForm"
          :rules="verifyRules"
          label-position="top"
          @keyup.enter="handleVerify"
        >
          <el-form-item label="验证方式" prop="type">
            <el-radio-group v-model="verifyType" class="w-full">
              <el-radio-button value="email" class="flex-1 text-center">
                <el-icon class="el-icon--left"><Message /></el-icon>
                邮箱验证
              </el-radio-button>
              <el-radio-button value="phone" class="flex-1 text-center">
                <el-icon class="el-icon--left"><Phone /></el-icon>
                手机验证
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="账号" prop="account">
            <el-input
              v-model="verifyForm.account"
              :prefix-icon="User"
              :placeholder="verifyType === 'email' ? '请输入邮箱地址' : '请输入手机号码'"
              size="large"
            />
          </el-form-item>

          <el-form-item label="验证码" prop="verifyCode">
            <div class="flex gap-3">
              <el-input
                v-model="verifyForm.verifyCode"
                :prefix-icon="Lock"
                placeholder="请输入6位验证码"
                size="large"
                maxlength="6"
              />
              <el-button
                size="large"
                :loading="loading"
                @click="handleSendCode"
              >
                {{ loading ? '发送中...' : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            class="w-full"
            :loading="loading"
            @click="handleVerify"
          >
            验证身份
          </el-button>
        </el-form>
      </div>

      <div v-if="currentStep === 'reset'">
        <el-form
          ref="resetFormRef"
          :model="resetForm"
          :rules="resetRules"
          label-position="top"
          @keyup.enter="handleResetPassword"
        >
          <el-form-item label="新密码" prop="password">
            <el-input
              v-model="resetForm.password"
              :prefix-icon="Lock"
              show-password
              placeholder="请输入新密码"
              size="large"
            />
          </el-form-item>

          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="resetForm.confirmPassword"
              :prefix-icon="Lock"
              show-password
              placeholder="请再次输入新密码"
              size="large"
            />
          </el-form-item>

          <div class="flex gap-3">
            <el-button size="large" class="flex-1" @click="currentStep = 'verify'">
              上一步
            </el-button>
            <el-button
              type="primary"
              size="large"
              class="flex-1"
              :loading="loading"
              @click="handleResetPassword"
            >
              重置密码
            </el-button>
          </div>
        </el-form>
      </div>

      <div v-if="currentStep === 'complete'" class="text-center">
        <div class="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-[var(--app-success)]/10">
          <el-icon :size="40" class="text-[var(--app-success)]">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </el-icon>
        </div>

        <h3 class="text-xl font-semibold">密码重置成功</h3>
        <p class="mt-2 text-sm text-[var(--app-text-secondary)]">
          您的密码已成功重置，请使用新密码登录
        </p>

        <el-button
          type="primary"
          size="large"
          class="mt-6 w-full"
          @click="handleBackToLogin"
        >
          返回登录
        </el-button>
      </div>
    </div>

    <div class="mt-6 text-center">
      <span class="text-sm text-[var(--app-text-secondary)]">想起密码了？</span>
      <router-link
        to="/login"
        class="ml-1 text-sm text-[var(--app-primary)] hover:text-[var(--app-primary-hover)]"
      >
        返回登录
      </router-link>
    </div>
  </div>
</template>
