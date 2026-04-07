<template>
  <div class="dept-tree-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>部门管理</span>
          <el-button type="primary" @click="handleAdd">新增部门</el-button>
        </div>
      </template>

      <div class="tree-wrapper">
        <el-tree
          ref="treeRef"
          :data="treeData"
          :props="treeProps"
          node-key="id"
          :expand-on-click-node="false"
          default-expand-all
        >
          <template #default="{ data }">
            <span class="tree-node">
              <span class="node-label">{{ data.name }}</span>
              <span class="node-actions">
                <el-button link type="primary" size="small" @click="handleAddChild(data)">
                  新增
                </el-button>
                <el-button link type="primary" size="small" @click="handleEdit(data)">
                  编辑
                </el-button>
                <el-button link type="danger" size="small" @click="handleDelete(data)">
                  删除
                </el-button>
              </span>
            </span>
          </template>
        </el-tree>
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      @close="handleClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="上级部门" prop="parentId">
          <el-tree-select
            v-model="formData.parentId"
            :data="treeData"
            :props="treeProps"
            check-strictly
            placeholder="请选择上级部门"
            clearable
          />
        </el-form-item>

        <el-form-item label="部门名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入部门名称" />
        </el-form-item>

        <el-form-item label="部门编码" prop="code">
          <el-input v-model="formData.code" placeholder="请输入部门编码" />
        </el-form-item>

        <el-form-item label="排序" prop="orderNum">
          <el-input-number v-model="formData.orderNum" :min="0" />
        </el-form-item>

        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="formData.status">
            <el-radio :label="1">启用</el-radio>
            <el-radio :label="0">禁用</el-radio>
          </el-radio-group>
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
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

interface Dept {
  id: number
  name: string
  code: string
  parentId: number | null
  orderNum: number
  status: number
  remark?: string
  children?: Dept[]
}

const treeRef = ref()
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const currentDept = ref<Dept | null>(null)

const formRef = ref<FormInstance>()

const formData = reactive<Dept>({
  id: 0,
  name: '',
  code: '',
  parentId: null,
  orderNum: 0,
  status: 1,
  remark: ''
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入部门名称', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入部门编码', trigger: 'blur' }
  ]
}

const treeProps = {
  children: 'children',
  label: 'name'
}

const treeData = ref<Dept[]>([
  {
    id: 1,
    name: '总公司',
    code: 'HQ',
    parentId: null,
    orderNum: 0,
    status: 1,
    children: [
      {
        id: 2,
        name: '技术部',
        code: 'TECH',
        parentId: 1,
        orderNum: 1,
        status: 1,
        children: [
          {
            id: 4,
            name: '研发组',
            code: 'TECH-DEV',
            parentId: 2,
            orderNum: 1,
            status: 1
          },
          {
            id: 5,
            name: '测试组',
            code: 'TECH-QA',
            parentId: 2,
            orderNum: 2,
            status: 1
          }
        ]
      },
      {
        id: 3,
        name: '运营部',
        code: 'OPS',
        parentId: 1,
        orderNum: 2,
        status: 1
      }
    ]
  }
])

const dialogTitle = computed(() => {
  return dialogMode.value === 'create' ? '新增部门' : '编辑部门'
})

const handleAdd = () => {
  dialogMode.value = 'create'
  currentDept.value = null
  Object.assign(formData, {
    id: 0,
    name: '',
    code: '',
    parentId: null,
    orderNum: 0,
    status: 1,
    remark: ''
  })
  dialogVisible.value = true
}

const handleAddChild = (data: Dept) => {
  dialogMode.value = 'create'
  currentDept.value = null
  Object.assign(formData, {
    id: 0,
    name: '',
    code: '',
    parentId: data.id,
    orderNum: 0,
    status: 1,
    remark: ''
  })
  dialogVisible.value = true
}

const handleEdit = (data: Dept) => {
  dialogMode.value = 'edit'
  currentDept.value = data
  Object.assign(formData, { ...data })
  dialogVisible.value = true
}

const handleDelete = async (data: Dept) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除部门"${data.name}"吗？${data.children?.length ? '该部门包含子部门，将一并删除。' : ''}`,
      '提示',
      { type: 'warning' }
    )
    ElMessage.success('删除成功')
  } catch {
    // 用户取消
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate((valid) => {
    if (valid) {
      ElMessage.success(dialogMode.value === 'create' ? '新增成功' : '编辑成功')
      dialogVisible.value = false
    }
  })
}

const handleClose = () => {
  formRef.value?.resetFields()
}
</script>

<style scoped>
.dept-tree-container {
  padding: 0px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tree-wrapper {
  padding: 10px 0;
}

.tree-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  padding-right: 20px;
}

.node-label {
  font-size: 14px;
}

.node-actions {
  display: flex;
  gap: 10px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
