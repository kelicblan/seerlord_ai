<script setup lang="ts">
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'

defineProps<{
  modelValue: boolean
  nodeData: any
}>()

const emit = defineEmits(['update:modelValue'])

const MONACO_OPTIONS = {
  minimap: { enabled: false },
  readOnly: true,
  fontSize: 13,
  automaticLayout: true
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    title="节点详情"
    size="40%"
    destroy-on-close
  >
    <div v-if="nodeData" class="h-full flex flex-col gap-4">
      <div class="info-item">
        <span class="label">节点ID:</span>
        <span class="value">{{ nodeData.label }}</span>
      </div>
      <div class="info-item">
        <span class="label">状态:</span>
        <el-tag :type="nodeData.status === 'success' ? 'success' : nodeData.status === 'error' ? 'danger' : nodeData.status === 'running' ? 'primary' : 'info'">
          {{ nodeData.status || 'Idle' }}
        </el-tag>
      </div>

      <el-divider content-position="left">输入数据</el-divider>
      <div class="editor-container">
        <VueMonacoEditor
          :value="JSON.stringify(nodeData.input || {}, null, 2)"
          language="json"
          theme="vs"
          :options="MONACO_OPTIONS"
        />
      </div>

      <el-divider content-position="left">输出结果</el-divider>
      <div class="editor-container">
        <VueMonacoEditor
          :value="JSON.stringify(nodeData.output || {}, null, 2)"
          language="json"
          theme="vs"
          :options="MONACO_OPTIONS"
        />
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.info-item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.label {
  font-weight: bold;
  color: #606266;
}
.editor-container {
  height: 300px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}
</style>
