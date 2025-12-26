<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Key, Delete } from '@element-plus/icons-vue'
import { getApiKeys, createApiKey, deleteApiKey, type ApiKey } from '../api/apiKeys'

const { t } = useI18n()
const activeTab = ref('keys')
const loading = ref(false)
const apiKeys = ref<ApiKey[]>([])
const dialogVisible = ref(false)
const newKeyForm = reactive({
  name: ''
})
const createdKey = ref<string | null>(null)

const fetchKeys = async () => {
  loading.value = true
  try {
    const res = await getApiKeys()
    apiKeys.value = res.data
  } catch (error) {
    console.error(error)
    ElMessage.error('Failed to fetch API keys')
  } finally {
    loading.value = false
  }
}

const handleCreateKey = async () => {
  if (!newKeyForm.name) {
    ElMessage.warning(t('api_platform.keys.key_name_placeholder'))
    return
  }
  try {
    const res = await createApiKey({ name: newKeyForm.name })
    createdKey.value = res.data.key
    fetchKeys()
    // Don't close dialog immediately, show the key
  } catch (error) {
    console.error(error)
    ElMessage.error('Failed to create API key')
  }
}

const handleCloseDialog = () => {
  dialogVisible.value = false
  newKeyForm.name = ''
  createdKey.value = null
}

const handleDeleteKey = (id: string) => {
  ElMessageBox.confirm(
    t('api_platform.keys.revoke_confirm'),
    t('api_platform.keys.revoke'),
    {
      confirmButtonText: t('common.delete'),
      cancelButtonText: 'Cancel',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await deleteApiKey(id)
      ElMessage.success('API Key revoked')
      fetchKeys()
    } catch (error) {
      console.error(error)
      ElMessage.error('Failed to revoke API key')
    }
  })
}

const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success(t('api_platform.keys.copied'))
  })
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString()
}

onMounted(() => {
  fetchKeys()
})

const exampleCode = `curl -X POST "${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/agent/stream_events" \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -d '{
    "input": {
      "messages": [
        {"role": "user", "content": "Hello, how are you?"}
      ]
    },
    "config": {
      "configurable": {
        "agent_id": "simple_chat"
      }
    }
  }'`

</script>

<template>
  <div class="p-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-800">{{ t('api_platform.title') }}</h1>
    </div>

    <el-tabs v-model="activeTab" class="bg-white p-6 rounded-lg shadow-sm">
      <!-- API Keys Tab -->
      <el-tab-pane :label="t('api_platform.tabs.keys')" name="keys">
        <div class="flex justify-between items-center mb-4">
          <div class="text-gray-600">
            {{ t('api_platform.tabs.keys_desc') }}
          </div>
          <el-button type="primary" :icon="Key" @click="dialogVisible = true">
            {{ t('api_platform.keys.create') }}
          </el-button>
        </div>

        <el-table :data="apiKeys" v-loading="loading" style="width: 100%">
          <el-table-column prop="name" :label="t('api_platform.keys.name')" width="180" />
          <el-table-column :label="t('api_platform.keys.key')" min-width="220">
            <template #default="scope">
              <div class="flex items-center space-x-2">
                <span class="font-mono text-gray-500 text-sm">
                  {{ scope.row.key.substring(0, 8) }}...{{ scope.row.key.substring(scope.row.key.length - 4) }}
                </span>
                <el-button link type="primary" :icon="CopyDocument" @click="copyToClipboard(scope.row.key)">
                  {{ t('api_platform.keys.copy') }}
                </el-button>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" :label="t('api_platform.keys.created_at')" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="t('api_platform.keys.status')" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success' : 'danger'">
                {{ scope.row.is_active ? t('api_platform.keys.active') : t('api_platform.keys.inactive') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('api_platform.keys.actions')" width="120" align="right">
            <template #default="scope">
              <el-button type="danger" link :icon="Delete" @click="handleDeleteKey(scope.row.id)">
                {{ t('api_platform.keys.revoke') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Documentation Tab -->
      <el-tab-pane :label="t('api_platform.tabs.docs')" name="docs">
        <div class="prose max-w-none">
          <h3>{{ t('api_platform.docs.run_agent') }}</h3>
          <p>{{ t('api_platform.docs.run_agent_desc') }}</p>
          
          <div class="bg-gray-50 rounded-lg p-4 my-4 border border-gray-200">
            <div class="flex items-center space-x-2 mb-2">
              <span class="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-bold">POST</span>
              <span class="font-mono text-sm text-gray-700">/api/v1/agent/stream_events</span>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
              <div>
                <h4 class="text-sm font-semibold text-gray-700 mb-2">{{ t('api_platform.docs.auth_header') }}</h4>
                <div class="bg-white p-3 rounded border border-gray-200 font-mono text-sm">
                  X-API-Key: YOUR_API_KEY
                </div>

                <h4 class="text-sm font-semibold text-gray-700 mt-4 mb-2">{{ t('api_platform.docs.request_body') }}</h4>
                <pre class="bg-white p-3 rounded border border-gray-200 font-mono text-xs overflow-auto h-40">
{
  "input": {
    "messages": [...]
  },
  "config": {
    "configurable": {
      "agent_id": "agent_name"
    }
  }
}</pre>
              </div>
              
              <div>
                <h4 class="text-sm font-semibold text-gray-700 mb-2">{{ t('api_platform.docs.example') }}</h4>
                <div class="relative group">
                  <pre class="bg-gray-800 text-gray-100 p-4 rounded text-xs overflow-auto h-64 font-mono">{{ exampleCode }}</pre>
                  <button 
                    @click="copyToClipboard(exampleCode)"
                    class="absolute top-2 right-2 p-1 bg-gray-700 text-white rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <el-icon><CopyDocument /></el-icon>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Create Key Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="t('api_platform.keys.create_dialog_title')"
      width="30%"
      @closed="handleCloseDialog"
    >
      <div v-if="!createdKey">
        <el-form :model="newKeyForm" label-position="top">
          <el-form-item :label="t('api_platform.keys.name')">
            <el-input v-model="newKeyForm.name" :placeholder="t('api_platform.keys.key_name_placeholder')" />
          </el-form-item>
        </el-form>
      </div>
      <div v-else class="text-center">
        <el-result
          icon="success"
          :title="t('api_platform.keys.key_created_success')"
          :sub-title="t('api_platform.keys.key_created_desc')"
        >
        </el-result>
        <div class="bg-gray-100 p-4 rounded-lg flex items-center justify-between mb-4">
          <span class="font-mono font-bold text-lg text-gray-800 break-all">{{ createdKey }}</span>
          <el-button type="primary" text :icon="CopyDocument" @click="copyToClipboard(createdKey!)">
            {{ t('api_platform.keys.copy') }}
          </el-button>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button v-if="!createdKey" @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
          <el-button v-if="!createdKey" type="primary" @click="handleCreateKey">
            {{ t('common.confirm') }}
          </el-button>
          <el-button v-if="createdKey" type="primary" @click="handleCloseDialog">
            {{ t('common.close') }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* Add any specific styles here if tailwind isn't enough */
</style>
