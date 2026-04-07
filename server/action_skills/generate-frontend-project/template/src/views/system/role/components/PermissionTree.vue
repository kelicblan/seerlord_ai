<template>
  <div class="permission-tree-container">
    <el-tree
      ref="treeRef"
      :data="treeData"
      :props="treeProps"
      node-key="id"
      :default-expand-all="true"
      :check-strictly="false"
      :expand-on-click-node="false"
      show-checkbox
      :disabled="disabled"
      @check="handleCheck"
    >
      <template #default="{ data }">
        <span class="tree-node">
          <span class="node-icon">
            <el-icon v-if="data.type === 'menu'"><Menu /></el-icon>
            <el-icon v-else-if="data.type === 'button'"><Operation /></el-icon>
            <el-icon v-else><Folder /></el-icon>
          </span>
          <span class="node-label">{{ data.label }}</span>
          <span class="node-code">{{ data.code }}</span>
        </span>
      </template>
    </el-tree>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Menu, Operation, Folder } from '@element-plus/icons-vue'

interface TreeNode {
  id: number
  label: string
  code: string
  type: 'dir' | 'menu' | 'button'
  children?: TreeNode[]
}

interface Props {
  modelValue?: number[]
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  disabled: false
})

const emit = defineEmits<{
  'update:modelValue': [value: number[]]
}>()

const treeRef = ref()

const treeProps = {
  children: 'children',
  label: 'label'
}

const treeData = ref<TreeNode[]>([
  {
    id: 1,
    label: '系统管理',
    code: 'system',
    type: 'dir',
    children: [
      {
        id: 11,
        label: '用户管理',
        code: 'system:user',
        type: 'menu',
        children: [
          { id: 111, label: '查看用户', code: 'system:user:list', type: 'button' },
          { id: 112, label: '新增用户', code: 'system:user:add', type: 'button' },
          { id: 113, label: '编辑用户', code: 'system:user:edit', type: 'button' },
          { id: 114, label: '删除用户', code: 'system:user:delete', type: 'button' }
        ]
      },
      {
        id: 12,
        label: '角色管理',
        code: 'system:role',
        type: 'menu',
        children: [
          { id: 121, label: '查看角色', code: 'system:role:list', type: 'button' },
          { id: 122, label: '新增角色', code: 'system:role:add', type: 'button' },
          { id: 123, label: '编辑角色', code: 'system:role:edit', type: 'button' }
        ]
      },
      {
        id: 13,
        label: '部门管理',
        code: 'system:dept',
        type: 'menu',
        children: [
          { id: 131, label: '查看部门', code: 'system:dept:list', type: 'button' },
          { id: 132, label: '新增部门', code: 'system:dept:add', type: 'button' }
        ]
      }
    ]
  },
  {
    id: 2,
    label: '订单管理',
    code: 'order',
    type: 'dir',
    children: [
      {
        id: 21,
        label: '订单列表',
        code: 'order:list',
        type: 'menu',
        children: [
          { id: 211, label: '查看订单', code: 'order:list:view', type: 'button' },
          { id: 212, label: '导出订单', code: 'order:list:export', type: 'button' }
        ]
      }
    ]
  }
])

watch(() => props.modelValue, (val) => {
  if (treeRef.value && val) {
    treeRef.value.setCheckedKeys(val, false)
  }
}, { immediate: true })

const handleCheck = () => {
  const checkedKeys = treeRef.value.getCheckedKeys()
  emit('update:modelValue', checkedKeys)
}
</script>

<style scoped>
.permission-tree-container {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  padding: 10px;
  max-height: 400px;
  overflow-y: auto;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-icon {
  display: flex;
  align-items: center;
}

.node-label {
  flex: 1;
}

.node-code {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
