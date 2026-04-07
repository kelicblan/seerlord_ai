<template>
  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    :width="dialogWidth"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="120px"
      :disabled="isViewMode"
    >
      <el-form-item label="用户名" prop="username">
        <el-input v-model="formData.username" placeholder="请输入用户名" />
      </el-form-item>

      <el-form-item label="昵称" prop="nickname">
        <el-input v-model="formData.nickname" placeholder="请输入昵称" />
      </el-form-item>

      <el-form-item label="邮箱" prop="email">
        <el-input v-model="formData.email" placeholder="请输入邮箱" />
      </el-form-item>

      <el-form-item label="手机号" prop="phone">
        <el-input v-model="formData.phone" placeholder="请输入手机号" />
      </el-form-item>

      <el-form-item v-if="!isEditMode" label="密码" prop="password">
        <el-input
          v-model="formData.password"
          type="password"
          placeholder="请输入密码"
          show-password
        />
      </el-form-item>

      <el-form-item v-if="!isEditMode" label="确认密码" prop="confirmPassword">
        <el-input
          v-model="formData.confirmPassword"
          type="password"
          placeholder="请确认密码"
          show-password
        />
      </el-form-item>

      <el-form-item label="性别" prop="gender">
        <el-radio-group v-model="formData.gender">
          <el-radio label="male">男</el-radio>
          <el-radio label="female">女</el-radio>
          <el-radio label="other">未知</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="年龄" prop="age">
        <el-input-number v-model="formData.age" :min="1" :max="150" />
      </el-form-item>

      <el-form-item label="生日" prop="birthday">
        <el-date-picker
          v-model="formData.birthday"
          type="date"
          placeholder="选择日期"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="省份" prop="province">
        <el-select v-model="formData.province" placeholder="请选择省份" style="width: 100%">
          <el-option label="北京" value="beijing" />
          <el-option label="上海" value="shanghai" />
          <el-option label="广东" value="guangdong" />
          <el-option label="浙江" value="zhejiang" />
          <el-option label="江苏" value="jiangsu" />
        </el-select>
      </el-form-item>

      <el-form-item label="城市" prop="city">
        <el-select v-model="formData.city" placeholder="请选择城市" style="width: 100%">
          <el-option label="北京市" value="beijing" />
          <el-option label="上海市" value="shanghai" />
          <el-option label="广州市" value="guangzhou" />
          <el-option label="深圳市" value="shenzhen" />
          <el-option label="杭州市" value="hangzhou" />
        </el-select>
      </el-form-item>

      <el-form-item label="爱好" prop="hobbies">
        <el-checkbox-group v-model="formData.hobbies">
          <el-checkbox label="reading">阅读</el-checkbox>
          <el-checkbox label="travel">旅行</el-checkbox>
          <el-checkbox label="sports">运动</el-checkbox>
          <el-checkbox label="music">音乐</el-checkbox>
          <el-checkbox label="coding">编程</el-checkbox>
        </el-checkbox-group>
      </el-form-item>

      <el-form-item label="个人网站" prop="website">
        <el-input v-model="formData.website" placeholder="请输入个人网站" />
      </el-form-item>

      <el-form-item label="简介" prop="bio">
        <el-input
          v-model="formData.bio"
          type="textarea"
          :rows="4"
          placeholder="请输入简介"
        />
      </el-form-item>

      <el-form-item label="状态" prop="status">
        <el-switch v-model="formData.status" />
      </el-form-item>

      <el-form-item label="头像" prop="avatar">
        <el-upload
          class="avatar-uploader"
          action="#"
          :show-file-list="false"
          :auto-upload="false"
          :disabled="isViewMode"
        >
          <img v-if="formData.avatar" :src="formData.avatar" class="avatar" />
          <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
        </el-upload>
      </el-form-item>
    </el-form>

    <template #footer v-if="!isViewMode">
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

export type FormMode = 'create' | 'view' | 'edit'

export interface FormData {
  id?: number
  username: string
  nickname: string
  email: string
  phone: string
  password: string
  confirmPassword: string
  gender: string
  age: number
  birthday: string
  province: string
  city: string
  hobbies: string[]
  website: string
  bio: string
  status: boolean
  avatar: string
}

export interface Props {
  visible: boolean
  mode: FormMode
  data?: FormData
}

export interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'success'): void
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  mode: 'create',
  data: () => ({})
})

const emit = defineEmits<Emits>()

const formRef = ref<FormInstance>()

const formData = reactive<FormData>({
  id: undefined,
  username: '',
  nickname: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
  gender: 'male',
  age: 25,
  birthday: '',
  province: '',
  city: '',
  hobbies: [],
  website: '',
  bio: '',
  status: true,
  avatar: ''
})

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const isViewMode = computed(() => props.mode === 'view')
const isEditMode = computed(() => props.mode === 'edit' || props.mode === 'view')

const dialogTitle = computed(() => {
  const titles = {
    create: '新增',
    view: '查看',
    edit: '编辑'
  }
  return titles[props.mode]
})

const dialogWidth = computed(() => {
  return props.mode === 'view' ? '700px' : '600px'
})

watch(
  () => props.visible,
  (val) => {
    if (val) {
      resetForm()
      if (props.data && (props.mode === 'view' || props.mode === 'edit')) {
        Object.assign(formData, props.data)
      }
    }
  }
)

const validateConfirmPassword = (_rule: any, value: any, callback: any) => {
  if (value !== formData.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' }
  ],
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为6-20个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate((valid) => {
    if (valid) {
      ElMessage.success(props.mode === 'create' ? '创建成功' : '更新成功')
      console.log('表单数据:', formData)
      emit('success')
      handleClose()
    } else {
      ElMessage.error('请检查表单填写')
    }
  })
}

const handleClose = () => {
  formRef.value?.resetFields()
  dialogVisible.value = false
}

const resetForm = () => {
  if (!formRef.value) return
  formRef.value.resetFields()
  Object.assign(formData, {
    id: undefined,
    username: '',
    nickname: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    gender: 'male',
    age: 25,
    birthday: '',
    province: '',
    city: '',
    hobbies: [],
    website: '',
    bio: '',
    status: true,
    avatar: ''
  })
}
</script>

<style scoped>
:deep(.el-dialog) {
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

:deep(.el-dialog__body) {
  flex: 1;
  overflow-y: auto;
  padding: 0px;
}

.avatar-uploader {
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: border-color 0.3s;
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-uploader:hover {
  border-color: #409eff;
}

.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar {
  width: 100px;
  height: 100px;
  display: block;
}
</style>
