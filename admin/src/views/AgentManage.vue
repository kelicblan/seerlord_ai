<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getPlugins, getAgentConfig, updateAgentConfig, type AgentPlugin } from '@/api/agent'
import { ElMessage } from 'element-plus'
import { Edit, Refresh } from '@element-plus/icons-vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { load } from 'js-yaml'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const loading = ref(false)
const agents = ref<AgentPlugin[]>([])
const searchKeyword = ref('')

// Config Dialog
const configDialogVisible = ref(false)
const currentAgent = ref<AgentPlugin | null>(null)
const configContent = ref('')
const configLoading = ref(false)
const savingConfig = ref(false)

const MONACO_OPTIONS = {
  minimap: { enabled: false },
  automaticLayout: true,
  formatOnType: true,
  formatOnPaste: true,
  scrollBeyondLastLine: false,
  fontSize: 14,
  tabSize: 2
}

const filteredAgents = computed(() => {
  let list = agents.value.filter(a => a.type === 'application')
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    list = list.filter(a => 
      a.name.toLowerCase().includes(kw) || 
      (a.name_zh && a.name_zh.toLowerCase().includes(kw)) ||
      a.description.toLowerCase().includes(kw)
    )
  }
  return list
})

const fetchAgents = async () => {
  loading.value = true
  try {
    const res = await getPlugins()
    agents.value = res.data
  } catch (error) {
    console.error('Failed to fetch agents:', error)
    ElMessage.error(t('agent_mgmt.toast_error_load_agents'))
  } finally {
    loading.value = false
  }
}

const handleEditConfig = async (agent: AgentPlugin) => {
  currentAgent.value = agent
  configDialogVisible.value = true
  configLoading.value = true
  configContent.value = ''
  
  try {
    const res = await getAgentConfig(agent.id)
    configContent.value = res.data.content
  } catch (error) {
    console.error('Failed to fetch config:', error)
    ElMessage.error(t('agent_mgmt.toast_error_load_config'))
    configContent.value = t('agent_mgmt.toast_error_load_config_content')
  } finally {
    configLoading.value = false
  }
}

const handleSaveConfig = async () => {
  if (!currentAgent.value) return
  
  // Client-side YAML validation
  try {
    load(configContent.value)
  } catch (e: any) {
    ElMessage.error(t('agent_mgmt.toast_error_yaml', { message: e.message }))
    return
  }

  savingConfig.value = true
  try {
    await updateAgentConfig(currentAgent.value.id, configContent.value)
    ElMessage.success(t('agent_mgmt.toast_success_update'))
    configDialogVisible.value = false
  } catch (error: any) {
    console.error('Failed to save config:', error)
    ElMessage.error(error.response?.data?.detail || t('agent_mgmt.toast_error_save'))
  } finally {
    savingConfig.value = false
  }
}

onMounted(() => {
  fetchAgents()
})
</script>

<template>
  <ElCard shadow="never" class="h-full flex flex-col">
    <template #header>
      <div class="flex justify-between items-center">
        <div class="font-semibold text-lg">{{ t('agent_mgmt.title') }}</div>
        <div class="flex gap-2">
          <ElInput
            v-model="searchKeyword"
            :placeholder="t('agent_mgmt.search_placeholder')"
            style="width: 200px"
            clearable
          />
          <ElButton :icon="Refresh" circle @click="fetchAgents" />
        </div>
      </div>
    </template>
    
    <ElTable v-loading="loading" :data="filteredAgents" style="width: 100%">
      <ElTableColumn prop="name" :label="t('agent_mgmt.header_id')" width="180" />
      <ElTableColumn prop="name_zh" :label="t('agent_mgmt.header_name')" width="180">
        <template #default="{ row }">
          {{ row.name_zh || row.name }}
        </template>
      </ElTableColumn>
      <ElTableColumn prop="description" :label="t('agent_mgmt.header_desc')" />
      <ElTableColumn :label="t('agent_mgmt.header_actions')" width="120" fixed="right">
        <template #default="{ row }">
          <ElButton link type="primary" :icon="Edit" @click="handleEditConfig(row)">
            {{ t('agent_mgmt.btn_config') }}
          </ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <!-- Config Editor Dialog -->
    <ElDialog
      v-model="configDialogVisible"
      :title="currentAgent ? t('agent_mgmt.dialog_title', { name: currentAgent.name_zh || currentAgent.name }) : t('agent_mgmt.dialog_title_default')"
      width="80%"
      top="5vh"
      destroy-on-close
    >
      <div v-loading="configLoading" class="config-editor-container">
        <VueMonacoEditor
          v-model:value="configContent"
          language="yaml"
          theme="vs-dark"
          :options="MONACO_OPTIONS"
          height="600px"
        />
      </div>
      <template #footer>
        <span class="dialog-footer">
          <ElButton @click="configDialogVisible = false">{{ t('agent_mgmt.btn_cancel') }}</ElButton>
          <ElButton type="primary" :loading="savingConfig" @click="handleSaveConfig">
            {{ t('agent_mgmt.btn_save') }}
          </ElButton>
        </span>
      </template>
    </ElDialog>
  </ElCard>
</template>

<style scoped>
.config-editor-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}
</style>
