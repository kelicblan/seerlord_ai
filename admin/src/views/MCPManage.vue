<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { 
  Server, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  XCircle, 
  Wrench
} from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import api from '@/api/axios'

interface MCPTool {
  name: string
  description: string
  args_schema: Record<string, any>
}

interface MCPServer {
  name: string
  status: 'connected' | 'disconnected' | 'error'
  tool_count: number
  tools: MCPTool[]
  error?: string
  config?: any
}

const { t } = useI18n()

const servers = ref<MCPServer[]>([])
const loading = ref(false)
const selectedServer = ref<MCPServer | null>(null)

// Fetch MCP status
const fetchStatus = async () => {
  loading.value = true
  try {
    const response = await api.get('/api/v1/mcp/status')
    console.log('MCP API Response:', response)
    
    // Universal data extraction
    let payload: any = response.data || response
    
    // Handle potential double wrapping or direct return
    if (payload.data && payload.data.servers) {
        payload = payload.data
    }
    
    if (payload && Array.isArray(payload.servers)) {
      servers.value = payload.servers
    } else {
       console.error('Unexpected API response structure:', payload)
       ElMessage.warning('Received unexpected data structure from API')
    }
    
    console.log('Parsed servers:', servers.value)

    // Auto select first connected server if none selected
    if (!selectedServer.value && servers.value.length > 0) {
      // Try to find first connected one
      const connected = servers.value.find(s => s.status === 'connected')
      if (connected) {
        selectedServer.value = connected
      }
    } else if (selectedServer.value) {
      // Refresh selected server data
      const updated = servers.value.find(s => s.name === selectedServer.value?.name)
      if (updated) {
        selectedServer.value = updated
      }
    }
  } catch (error) {
    console.error('Failed to fetch MCP status:', error)
    ElMessage.error(t('mcp_mgmt.toast_refresh_error'))
  } finally {
    loading.value = false
  }
}

const handleRefresh = async () => {
  await fetchStatus()
  ElMessage.success(t('mcp_mgmt.toast_refresh_success'))
}

const selectServer = (server: MCPServer) => {
  selectedServer.value = server
}

onMounted(() => {
  fetchStatus()
})
</script>

<template>
  <div class="h-full w-full flex flex-col gap-4">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <h2 class="text-xl font-semibold tracking-tight">{{ t('mcp_mgmt.title') }}</h2>
      <ElButton :loading="loading" @click="handleRefresh">
        <RefreshCw class="mr-2 h-4 w-4" :class="{ 'animate-spin': loading }" />
        {{ t('mcp_mgmt.refresh') }}
      </ElButton>
    </div>

    <!-- DEBUG INFO (Temporary) -->
    <div v-if="servers.length === 0 && !loading" class="bg-yellow-50 p-2 border border-yellow-200 rounded text-xs text-yellow-800">
      <p class="font-bold">DEBUG INFO:</p>
      <p>Servers Count: {{ servers.length }}</p>
      <p>Loading: {{ loading }}</p>
      <p>Please check console for detailed API response.</p>
    </div>

    <!-- Main Content: Split View -->
    <div class="flex flex-1 gap-6 overflow-hidden h-[calc(100vh-140px)]">
      
      <!-- Left: Server List -->
      <div class="w-1/3 flex flex-col gap-4 overflow-y-auto pr-2">
        <ElCard 
          v-for="server in servers" 
          :key="server.name"
          class="cursor-pointer transition-all hover:shadow-md border-l-4"
          :class="[
            selectedServer?.name === server.name ? 'border-l-primary ring-1 ring-primary/20' : 'border-l-transparent',
            server.status === 'error' ? 'border-l-destructive' : ''
          ]"
          @click="selectServer(server)"
          shadow="hover"
        >
          <div class="flex justify-between items-start">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-full bg-secondary/50">
                <Server class="h-5 w-5 text-foreground" />
              </div>
              <div>
                <h3 class="font-medium text-base">{{ server.name }}</h3>
                <div class="flex items-center gap-2 mt-1">
                  <!-- Status Badge -->
                  <div class="flex items-center text-xs font-medium" 
                    :class="{
                      'text-green-600': server.status === 'connected',
                      'text-red-600': server.status === 'error',
                      'text-gray-500': server.status === 'disconnected'
                    }"
                  >
                    <CheckCircle2 v-if="server.status === 'connected'" class="h-3 w-3 mr-1" />
                    <XCircle v-else-if="server.status === 'error'" class="h-3 w-3 mr-1" />
                    <AlertCircle v-else class="h-3 w-3 mr-1" />
                    
                    <span v-if="server.status === 'connected'">{{ t('mcp_mgmt.status_connected') }}</span>
                    <span v-else-if="server.status === 'error'">{{ t('mcp_mgmt.status_error') }}</span>
                    <span v-else>{{ t('mcp_mgmt.status_disconnected') }}</span>
                  </div>
                </div>
              </div>
            </div>
            
            <ElTag size="small" effect="plain" round>
              {{ server.tool_count }} {{ t('mcp_mgmt.header_tools') }}
            </ElTag>
          </div>
          
          <!-- Error Message Preview -->
          <div v-if="server.error" class="mt-3 text-xs text-destructive bg-destructive/10 p-2 rounded">
            {{ server.error }}
          </div>
        </ElCard>
      </div>

      <!-- Right: Details & Tools -->
      <div class="flex-1 overflow-y-auto">
        <div v-if="selectedServer" class="space-y-6">
          <!-- Server Info Card -->
          <ElCard shadow="never">
            <template #header>
              <div class="flex items-center gap-2">
                <Wrench class="h-5 w-5 text-primary" />
                <span class="font-semibold">{{ t('mcp_mgmt.details_title') }}</span>
              </div>
            </template>
            
            <ElDescriptions :column="1" border>
              <ElDescriptionsItem :label="t('mcp_mgmt.header_name')">
                {{ selectedServer.name }}
              </ElDescriptionsItem>
              <ElDescriptionsItem :label="t('mcp_mgmt.header_status')">
                <ElTag 
                  :type="selectedServer.status === 'connected' ? 'success' : selectedServer.status === 'error' ? 'danger' : 'info'"
                >
                  {{ selectedServer.status.toUpperCase() }}
                </ElTag>
              </ElDescriptionsItem>
              <ElDescriptionsItem label="Command" v-if="selectedServer.config">
                 <code class="bg-muted px-2 py-1 rounded text-xs font-mono">
                   {{ selectedServer.config.command }} {{ (selectedServer.config.args || []).join(' ') }}
                 </code>
              </ElDescriptionsItem>
            </ElDescriptions>
          </ElCard>

          <!-- Tools List -->
          <div>
            <h3 class="text-lg font-medium mb-3 flex items-center gap-2">
              {{ t('mcp_mgmt.tools_list') }}
              <span class="text-sm text-muted-foreground font-normal">({{ (selectedServer.tools || []).length }})</span>
            </h3>
            
            <div v-if="(selectedServer.tools || []).length === 0" class="text-center py-12 bg-muted/30 rounded-lg border border-dashed">
              <p class="text-muted-foreground">{{ t('common.no_data') }}</p>
            </div>

            <div v-else class="grid grid-cols-1 gap-4">
              <ElCard 
                v-for="tool in (selectedServer.tools || [])" 
                :key="tool.name" 
                shadow="never"
                class="hover:border-primary/50 transition-colors"
              >
                <div class="flex flex-col gap-2">
                  <div class="flex justify-between items-start">
                    <h4 class="text-base font-semibold text-primary font-mono">{{ tool.name }}</h4>
                  </div>
                  
                  <p class="text-sm text-muted-foreground">{{ tool.description }}</p>
                  
                  <!-- Schema Viewer (Collapsible) -->
                  <ElCollapse class="mt-2 border-none">
                    <ElCollapseItem :title="t('mcp_mgmt.tool_schema')" name="1">
                      <pre class="bg-slate-950 text-slate-50 p-3 rounded text-xs overflow-x-auto font-mono leading-relaxed">{{ JSON.stringify(tool.args_schema, null, 2) }}</pre>
                    </ElCollapseItem>
                  </ElCollapse>
                </div>
              </ElCard>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="h-full flex flex-col items-center justify-center text-muted-foreground bg-muted/10 rounded-lg border border-dashed">
          <Server class="h-12 w-12 mb-4 opacity-20" />
          <p>{{ t('mcp_mgmt.no_selection') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(.el-collapse-item__header) {
  height: 32px;
  line-height: 32px;
  border-bottom: none;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
:deep(.el-collapse-item__wrap) {
  border-bottom: none;
}
:deep(.el-collapse) {
  border-top: none;
  border-bottom: none;
}
</style>
