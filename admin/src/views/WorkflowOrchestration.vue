<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import dagre from 'dagre'
import axios from 'axios'
import CustomNode from '@/components/workflow/CustomNode.vue'
import NodeDrawer from '@/components/workflow/NodeDrawer.vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { getPlugins } from '@/api/agent'

// Styles
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const pluginId = route.params.id as string

const { fitView } = useVueFlow()

const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const drawerVisible = ref(false)
const selectedNodeData = ref<any>(null)
const isRunning = ref(false)
const pluginName = ref(pluginId) // Default to ID

// Fetch agent details to get display name
const fetchAgentDetails = async () => {
    try {
        if (pluginId === 'master') {
            pluginName.value = '主流程'
            return
        }
        const res = await getPlugins()
        const agent = res.data.find(a => a.id === pluginId || a.name === pluginId)
        if (agent) {
            pluginName.value = agent.name_zh || agent.name
        }
    } catch (e) {
        console.warn('Failed to fetch agent details', e)
    }
}

// Layout Graph using Dagre
const layoutGraph = (nodes: any[], edges: any[], direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))

  dagreGraph.setGraph({ rankdir: direction })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 200, height: 80 })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  return nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      ...node,
      position: { x: nodeWithPosition.x, y: nodeWithPosition.y },
    }
  })
}

const fetchGraph = async () => {
  try {
    const res = await axios.get(`/api/v1/agent/${pluginId}/graph/json`)
    const rawNodes = res.data.nodes
    const rawEdges = res.data.edges

    // Format nodes
    const formattedNodes = rawNodes.map((n: any) => ({
      ...n,
      type: 'custom', // Use our CustomNode
      data: { ...n.data, status: 'idle' }
    }))

    nodes.value = layoutGraph(formattedNodes, rawEdges)
    edges.value = rawEdges
    
    // Log for debugging
    console.log('Graph loaded:', { nodes: nodes.value, edges: edges.value })

    nextTick(() => {
        fitView()
    })
  } catch (e) {
    console.error('Failed to load graph', e)
    ElMessage.error('加载图表失败')
  }
}

const handleNodeClick = (event: any) => {
  selectedNodeData.value = event.node.data
  drawerVisible.value = true
}

// Custom SSE implementation to ensure control
const startExecution = async () => {
  if (isRunning.value) return
  isRunning.value = true
  
  // Reset
  nodes.value.forEach(n => {
    n.data.status = 'idle'
    n.data.input = null
    n.data.output = null
  })

  const ctrl = new AbortController()
  
  try {
    const response = await fetch('/api/v1/agent/stream_events', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({
        input: {
          messages: [{ type: 'human', content: 'Start workflow' }],
          target_plugin: pluginId === 'master' ? 'auto' : pluginId
        },
        config: { configurable: { thread_id: `run_${Date.now()}` } }
      }),
      signal: ctrl.signal
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader!.read()
      if (done) break
      
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
            try {
                const data = JSON.parse(line.slice(6))
                handleEvent(data)
            } catch (e) {
                // Ignore parse errors
            }
        }
      }
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('执行出错')
  } finally {
    isRunning.value = false
  }
}

const handleEvent = (event: any) => {
    const name = event.name
    const type = event.event
    
    // Find node by label/id
    const node = nodes.value.find(n => n.id === name || n.data.label === name)
    
    if (node) {
        if (type === 'on_chain_start' || type === 'on_tool_start' || type === 'on_chat_model_start') {
            node.data.status = 'running'
            if (event.data && event.data.input) {
                 node.data.input = event.data.input
            }
        } else if (type === 'on_chain_end' || type === 'on_tool_end' || type === 'on_chat_model_end') {
            node.data.status = 'success'
            if (event.data && event.data.output) {
                node.data.output = event.data.output
            }
        }
    }
}

onMounted(() => {
  fetchGraph()
  fetchAgentDetails()
})
</script>

<template>
  <div class="workflow-container">
    <div class="header">
      <div class="flex items-center gap-4">
          <el-button link :icon="ArrowLeft" @click="router.push('/agents')">
            返回
          </el-button>
          <h2 class="text-lg font-bold">{{ pluginName }} 编排视图</h2>
          <el-tag type="info">只读模式</el-tag>
      </div>
      <el-button type="primary" :loading="isRunning" @click="startExecution">
        运行测试
      </el-button>
    </div>
    
    <div class="canvas-wrapper">
      <VueFlow
        v-model="nodes"
        :edges="edges"
        :default-viewport="{ zoom: 1 }"
        :min-zoom="0.2"
        :max-zoom="4"
        @node-click="handleNodeClick"
      >
        <template #node-custom="props">
          <CustomNode v-bind="props" />
        </template>
        
        <Background pattern-color="#aaa" :gap="18" />
        <Controls />
        <MiniMap />
      </VueFlow>
    </div>

    <NodeDrawer v-model="drawerVisible" :node-data="selectedNodeData" />
  </div>
</template>

<style scoped>
.workflow-container {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  height: 60px;
  padding: 0 16px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.canvas-wrapper {
  flex: 1;
  width: 100%;
  height: calc(100vh - 60px);
  background: #f5f7fa;
  position: relative;
}
</style>
