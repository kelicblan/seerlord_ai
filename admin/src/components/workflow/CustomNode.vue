<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
import { computed } from 'vue'
import { VideoPlay, CircleCheck, CircleClose, Loading } from '@element-plus/icons-vue'

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  selected: {
    type: Boolean,
    default: false,
  },
})

const statusColor = computed(() => {
  switch (props.data.status) {
    case 'running': return '#409EFF'
    case 'success': return '#67C23A'
    case 'error': return '#F56C6C'
    default: return '#909399'
  }
})

const statusIcon = computed(() => {
  switch (props.data.status) {
    case 'running': return Loading
    case 'success': return CircleCheck
    case 'error': return CircleClose
    default: return VideoPlay
  }
})
</script>

<template>
  <div class="custom-node" :class="{ selected: selected, running: data.status === 'running' }">
    <Handle type="target" :position="Position.Left" class="handle" />
    
    <div class="node-content">
      <div class="node-header">
        <el-icon class="node-icon" :style="{ color: statusColor }">
          <component :is="statusIcon" :class="{ 'is-loading': data.status === 'running' }" />
        </el-icon>
        <span class="node-label">{{ data.label }}</span>
      </div>
      <div v-if="data.description" class="node-desc">
        {{ data.description }}
      </div>
    </div>

    <Handle type="source" :position="Position.Right" class="handle" />
  </div>
</template>

<style scoped>
.custom-node {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  min-width: 180px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
}

.custom-node:hover {
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.custom-node.selected {
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.custom-node.running {
  border-color: #409EFF;
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.4);
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.node-label {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.node-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.handle {
  width: 10px;
  height: 10px;
  background: #909399;
}

.handle:hover {
  background: #409EFF;
}
</style>
