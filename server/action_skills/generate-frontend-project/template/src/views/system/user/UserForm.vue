<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="600px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="formData.username"
          placeholder="请输入用户名"
          :disabled="mode === 'edit'"
        />
      </el-form-item>

      <el-form-item label="昵称" prop="nickname">
        <el-input v-model="formData.nickname" placeholder="请输入昵称" />
      </el-form-item>

      <el-form-item label="手机号" prop="phone">
        <el-input v-model="formData.phone" placeholder="请输入手机号" />
      </el-form-item>

      <el-form-item label="邮箱" prop="email">
        <el-input v-model="formData.email" placeholder="请输入邮箱" />
      </el-form-item>

      <el-form-item v-if="mode === 'create'" label="密码" prop="password">
        <el-input
          v-model="formData.password"
          type="password"
          placeholder="请输入密码"
          show-password
        />
      </el-form-item>

      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="formData.status">
          <el-radio :label="1">启用</el-radio>
          <el-radio :label="0">禁用</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="角色" prop="roles">
        <el-select v-model="formData.roles" multiple placeholder="请选择角色">
          <el-option label="超级管理员" :value="1" />
          <el-option label="普通用户" :value="2" />
          <el-option label="访客" :value="3" />
        </el-select>
      </el-form-item>

      <el-form-item label="备注" prop="remark">
        <el-input
          v-model="formData.remark"
          type="textarea"
          :rows="3"
          placeholder="请输入备注"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button v-if="mode !== 'view'" type="primary" @click="handleSubmit">
          确定
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

interface User {
  id?: number
  username: string
  nickname: string
  phone: string
  email: string
  password?: string
  status: number
  roles?: number[]
  remark?: string
}

const props = defineProps<{
  modelValue: boolean
  data?: User | null
  mode: 'create' | 'edit' | 'view'
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: []
  cancel: []
}>()

const formRef = ref<FormInstance>()

const formData = ref<User>({
  username: '',
  nickname: '',
  phone: '',
  email: '',
  password: '',
  status: 1,
  roles: [],
  remark: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' }
  ],
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为6-20个字符', trigger: 'blur' }
  ]
}

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const dialogTitle = computed(() => {
  const titles = {
    create: '新增用户',
    edit: '编辑用户',
    view: '用户详情'
  }
  return titles[props.mode]
})

watch(() => props.data, (val) => {
  if (val) {
    formData.value = { ...val }
  } else {
    formData.value = {
      username: '',
      nickname: '',
      phone: '',
      email: '',
      password: '',
      status: 1,
      roles: [],
      remark: ''
    }
  }
}, { immediate: true })

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate((valid) => {
    if (valid) {
      emit('submit')
    }
  })
}

const handleClose = () => {
  formRef.value?.resetFields()
  emit('cancel')
}
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
