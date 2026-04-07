<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="700px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="角色名称" prop="name">
        <el-input v-model="formData.name" placeholder="请输入角色名称" />
      </el-form-item>

      <el-form-item label="角色编码" prop="code">
        <el-input
          v-model="formData.code"
          placeholder="请输入角色编码"
          :disabled="mode === 'edit'"
        />
      </el-form-item>

      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="formData.status">
          <el-radio :label="1">启用</el-radio>
          <el-radio :label="0">禁用</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="角色描述" prop="description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="3"
          placeholder="请输入角色描述"
        />
      </el-form-item>

      <el-form-item label="权限配置" prop="permissions">
        <permission-tree
          v-model="formData.permissions"
          :disabled="mode === 'view'"
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
import PermissionTree from './components/PermissionTree.vue'

interface Role {
  id?: number
  name: string
  code: string
  description: string
  status: number
  permissions?: number[]
}

const props = defineProps<{
  modelValue: boolean
  data?: Role | null
  mode: 'create' | 'edit' | 'view'
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: []
  cancel: []
}>()

const formRef = ref<FormInstance>()

const formData = ref<Role>({
  name: '',
  code: '',
  description: '',
  status: 1,
  permissions: []
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入角色名称', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入角色编码', trigger: 'blur' },
    { pattern: /^[a-z_]+$/, message: '角色编码只能包含小写字母和下划线', trigger: 'blur' }
  ]
}

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const dialogTitle = computed(() => {
  const titles = {
    create: '新增角色',
    edit: '编辑角色',
    view: '角色详情'
  }
  return titles[props.mode]
})

watch(() => props.data, (val) => {
  if (val) {
    formData.value = { ...val }
  } else {
    formData.value = {
      name: '',
      code: '',
      description: '',
      status: 1,
      permissions: []
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
