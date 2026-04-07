<script setup lang="ts">
import { Lock, User } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { reactive, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Captcha from './Captcha.vue'

const emit = defineEmits<{
  success: []
}>()

const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const captchaKey = ref('')

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
  captcha: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

const handleCaptchaChange = (key: string) => {
  captchaKey.value = key
}

const handleSubmit = async () => {
  const isValid = await formRef.value?.validate().catch(() => false)

  if (!isValid) {
    return
  }

  try {
    await authStore.login({
      account: formModel.account,
      password: formModel.password,
      remember: formModel.remember,
    })
    emit('success')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败，请稍后重试')
  }
}
</script>

<template>
  <div class="surface-card mx-auto w-full max-w-md rounded-2xl p-8 shadow-lg">
    <div class="text-center">
      <h2 class="text-2xl font-semibold">用户登录</h2>
      <p class="mt-2 text-sm text-[var(--app-text-secondary)]">
        欢迎使用管理系统，请登录您的账号
      </p>
    </div>

    <el-form
      ref="formRef"
      :model="formModel"
      :rules="rules"
      label-position="top"
      class="mt-6"
      @keyup.enter="handleSubmit"
    >
      <el-form-item label="账号" prop="account">
        <el-input
          v-model="formModel.account"
          :prefix-icon="User"
          placeholder="请输入账号"
          size="large"
        />
      </el-form-item>

      <el-form-item label="密码" prop="password">
        <el-input
          v-model="formModel.password"
          :prefix-icon="Lock"
          show-password
          placeholder="请输入密码"
          size="large"
        />
      </el-form-item>

      <el-form-item label="验证码" prop="captcha">
        <Captcha @change="handleCaptchaChange" />
      </el-form-item>

      <div class="mb-4 flex items-center justify-between text-sm">
        <el-checkbox v-model="formModel.remember">记住我</el-checkbox>
        <router-link
          to="/reset-password"
          class="text-[var(--app-primary)] hover:text-[var(--app-primary-hover)]"
        >
          忘记密码？
        </router-link>
      </div>

      <el-button
        type="primary"
        size="large"
        class="w-full"
        :loading="authStore.loading"
        @click="handleSubmit"
      >
        登录
      </el-button>
    </el-form>
  </div>
</template>
