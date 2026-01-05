<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getModels,
  createModel,
  updateModel,
  deleteModel,
  getSystemSettings,
  updateSystemSettings,
  type LLMModel
} from '@/api/settings'
import { Edit, Trash2 } from 'lucide-vue-next'

const { t } = useI18n()
const activeTab = ref('system')
const loading = ref(false)

// Data Storage
const models = ref<LLMModel[]>([])
const settings = ref<Record<string, string>>({})

// System Settings Form
const systemForm = ref({
  AGENT_LLM_ID: '',
  FULL_MODAL_MODEL_ID: '',
  EMBEDDING_MODEL_ID: '',
  RERANKER_MODEL_ID: '',
  TEXT_TO_IMAGE_MODEL_ID: '',
  TEXT_TO_VIDEO_MODEL_ID: '',
  VOICE_MODEL_ID: '',
  LLM_TIMEOUT: '60'
})

// Model Management Form
const modelFormVisible = ref(false)
const isEditMode = ref(false)
const editingId = ref<number | null>(null)

const modelForm = ref({
  name: '',
  provider: 'openai',
  base_url: '',
  model_name: '',
  api_key: '',
  model_type: 'llm',
  price_per_1k_tokens: 0
})

const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Ollama', value: 'ollama' }
]

const modelTypeOptions = [
  { label: 'LLM', value: 'llm' },
  { label: 'Embedding', value: 'embedding' },
  { label: 'Reranker', value: 'reranker' },
  { label: 'Text-to-Image', value: 'text-to-image' },
  { label: 'Text-to-Video', value: 'text-to-video' },
  { label: 'Voice', value: 'voice' },
  { label: 'MoE', value: 'MoE' }
]

// Computed properties for filtering models
const llmModels = computed(() => models.value.filter(m => m.model_type === 'llm'))
const embeddingModels = computed(() => models.value.filter(m => m.model_type === 'embedding'))
const rerankerModels = computed(() => models.value.filter(m => m.model_type === 'reranker'))
const textToImageModels = computed(() => models.value.filter(m => m.model_type === 'text-to-image'))
const textToVideoModels = computed(() => models.value.filter(m => m.model_type === 'text-to-video'))
const voiceModels = computed(() => models.value.filter(m => m.model_type === 'voice'))
const fullModalModels = computed(() => models.value.filter(m => m.model_type === 'llm' || m.model_type === 'MoE'))

// Initialization
const fetchData = async () => {
  loading.value = true
  try {
    const [modelsRes, settingsRes] = await Promise.all([
      getModels(),
      getSystemSettings()
    ])
    
    models.value = modelsRes.data
    
    // Map settings array to object
    const settingsMap: Record<string, string> = {}
    settingsRes.data.forEach(s => {
      settingsMap[s.key] = s.value
    })
    settings.value = settingsMap
    
    // Initialize system form
    systemForm.value = {
      AGENT_LLM_ID: settingsMap['AGENT_LLM_ID'] || '',
      FULL_MODAL_MODEL_ID: settingsMap['FULL_MODAL_MODEL_ID'] || '',
      EMBEDDING_MODEL_ID: settingsMap['EMBEDDING_MODEL_ID'] || '',
      RERANKER_MODEL_ID: settingsMap['RERANKER_MODEL_ID'] || '',
      TEXT_TO_IMAGE_MODEL_ID: settingsMap['TEXT_TO_IMAGE_MODEL_ID'] || '',
      TEXT_TO_VIDEO_MODEL_ID: settingsMap['TEXT_TO_VIDEO_MODEL_ID'] || '',
      VOICE_MODEL_ID: settingsMap['VOICE_MODEL_ID'] || '',
      LLM_TIMEOUT: settingsMap['LLM_TIMEOUT'] || '60'
    }
  } catch (error) {
    console.error(error)
    ElMessage.error(t('common.no_data'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})

// System Settings Actions
const saveSystemSettings = async () => {
  loading.value = true
  try {
    const settingsToUpdate = [
      { key: 'AGENT_LLM_ID', value: systemForm.value.AGENT_LLM_ID, description: 'Active LLM Agent Model ID' },
      { key: 'FULL_MODAL_MODEL_ID', value: systemForm.value.FULL_MODAL_MODEL_ID, description: 'Active Full Modal Model ID' },
      { key: 'EMBEDDING_MODEL_ID', value: systemForm.value.EMBEDDING_MODEL_ID, description: 'Active Embedding Model ID' },
      { key: 'RERANKER_MODEL_ID', value: systemForm.value.RERANKER_MODEL_ID, description: 'Active Reranker Model ID' },
      { key: 'TEXT_TO_IMAGE_MODEL_ID', value: systemForm.value.TEXT_TO_IMAGE_MODEL_ID, description: 'Active Text-to-Image Model ID' },
      { key: 'TEXT_TO_VIDEO_MODEL_ID', value: systemForm.value.TEXT_TO_VIDEO_MODEL_ID, description: 'Active Text-to-Video Model ID' },
      { key: 'VOICE_MODEL_ID', value: systemForm.value.VOICE_MODEL_ID, description: 'Active Voice Model ID' },
      { key: 'LLM_TIMEOUT', value: systemForm.value.LLM_TIMEOUT, description: 'LLM Request Timeout (seconds)' }
    ]
    
    await updateSystemSettings(settingsToUpdate)
    ElMessage.success(t('settings.save_success'))
    await fetchData()
  } catch (error) {
    console.error(error)
    ElMessage.error(t('settings.save_failed'))
  } finally {
    loading.value = false
  }
}

// Model Management Actions
const openCreateModelDialog = () => {
  isEditMode.value = false
  editingId.value = null
  modelForm.value = {
    name: '',
    provider: 'openai',
    base_url: '',
    model_name: '',
    api_key: '',
    model_type: 'llm',
    price_per_1k_tokens: 0
  }
  modelFormVisible.value = true
}

const openEditModelDialog = (row: LLMModel) => {
  isEditMode.value = true
  editingId.value = row.id
  modelForm.value = {
    name: row.name,
    provider: row.provider,
    base_url: row.base_url || '',
    model_name: row.model_name,
    api_key: row.api_key || '',
    model_type: row.model_type,
    price_per_1k_tokens: row.price_per_1k_tokens || 0
  }
  modelFormVisible.value = true
}

const handleSaveModel = async () => {
  if (!modelForm.value.name || !modelForm.value.model_name) {
    ElMessage.warning(t('settings.required_fields'))
    return
  }
  
  loading.value = true
  try {
    if (isEditMode.value && editingId.value) {
      await updateModel(editingId.value, modelForm.value)
      ElMessage.success(t('settings.model_updated'))
    } else {
      await createModel(modelForm.value)
      ElMessage.success(t('settings.model_added'))
    }
    modelFormVisible.value = false
    await fetchData()
  } catch (error) {
    console.error(error)
    ElMessage.error(t('settings.model_save_failed'))
  } finally {
    loading.value = false
  }
}

const handleDeleteModel = async (row: LLMModel) => {
  try {
    await ElMessageBox.confirm(
      t('settings.delete_model_confirm'),
      t('common.confirm'),
      {
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    
    loading.value = true
    await deleteModel(row.id)
    ElMessage.success(t('settings.model_deleted'))
    await fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error(t('settings.model_delete_failed'))
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="h-full flex flex-col bg-background p-2">
    <div class="mb-2">
      <h2 class="text-2xl font-bold tracking-tight">{{ t('settings.title') }}</h2>
      <p class="text-muted-foreground">{{ t('settings.subtitle') }}</p>
    </div>

    <div class="flex-1 bg-card rounded-lg border shadow-sm overflow-hidden">
      <ElTabs v-model="activeTab" class="h-full flex flex-col" type="border-card">
        <!-- Tab 1: System Settings -->
        <ElTabPane :label="t('settings.system_tab')" name="system" class="p-4 h-full overflow-auto">
          <div class="max-w-2xl mx-auto space-y-8 py-4">
            <ElForm :model="systemForm" label-position="top" size="large">
              
              <div class="grid gap-2">
                <!-- Agent Model Selection -->
                <div class="space-y-2">
                  <h3 class="text-lg font-medium">{{ t('settings.agent_model') }}</h3>
                  <div class="grid grid-cols-1 gap-2 md:grid-cols-2 ">
                  <ElFormItem :label="t('settings.default_agent')">
                    <ElSelect v-model="systemForm.AGENT_LLM_ID" placeholder="Select an LLM model" class="w-full">
                      <ElOption
                        v-for="item in llmModels"
                        :key="item.id"
                        :label="item.name + ' (' + item.model_name + ')'"
                        :value="item.id.toString()"
                      />
                    </ElSelect>
                  </ElFormItem>
                  
                  <ElFormItem :label="t('settings.full_modal_model')">
                    <ElSelect v-model="systemForm.FULL_MODAL_MODEL_ID" placeholder="Select a Full Modal model" class="w-full">
                      <ElOption
                        v-for="item in fullModalModels"
                        :key="item.id"
                        :label="item.name + ' (' + item.model_name + ')'"
                        :value="item.id.toString()"
                      />
                    </ElSelect>
                  </ElFormItem>
                    <ElFormItem :label="t('settings.embedding_model')">
                      <ElSelect v-model="systemForm.EMBEDDING_MODEL_ID" placeholder="Select an Embedding model" class="w-full">
                         <ElOption
                          v-for="item in embeddingModels"
                          :key="item.id"
                          :label="item.name + ' (' + item.model_name + ')'"
                          :value="item.id.toString()"
                        />
                      </ElSelect>
                    </ElFormItem>

                    <ElFormItem :label="t('settings.reranker_model')">
                      <ElSelect v-model="systemForm.RERANKER_MODEL_ID" placeholder="Select a Reranker model" class="w-full">
                         <ElOption
                          v-for="item in rerankerModels"
                          :key="item.id"
                          :label="item.name + ' (' + item.model_name + ')'"
                          :value="item.id.toString()"
                        />
                      </ElSelect>
                    </ElFormItem>

                    <ElFormItem :label="t('settings.text_to_image_model')">
                      <ElSelect v-model="systemForm.TEXT_TO_IMAGE_MODEL_ID" placeholder="Select a Text-to-Image model" class="w-full">
                         <ElOption
                          v-for="item in textToImageModels"
                          :key="item.id"
                          :label="item.name + ' (' + item.model_name + ')'"
                          :value="item.id.toString()"
                        />
                      </ElSelect>
                    </ElFormItem>

                    <ElFormItem :label="t('settings.text_to_video_model')">
                      <ElSelect v-model="systemForm.TEXT_TO_VIDEO_MODEL_ID" placeholder="Select a Text-to-Video model" class="w-full">
                         <ElOption
                          v-for="item in textToVideoModels"
                          :key="item.id"
                          :label="item.name + ' (' + item.model_name + ')'"
                          :value="item.id.toString()"
                        />
                      </ElSelect>
                    </ElFormItem>

                    <ElFormItem :label="t('settings.voice_model')">
                      <ElSelect v-model="systemForm.VOICE_MODEL_ID" placeholder="Select a Voice model" class="w-full">
                         <ElOption
                          v-for="item in voiceModels"
                          :key="item.id"
                          :label="item.name + ' (' + item.model_name + ')'"
                          :value="item.id.toString()"
                        />
                      </ElSelect>
                    </ElFormItem>
                  </div>
                </div>

                <!-- General Configuration -->
                <div class="space-y-2">
                  <h3 class="text-lg font-medium">{{ t('settings.general_config') }}</h3>
                  <ElFormItem :label="t('settings.llm_timeout')">
                    <ElInput v-model="systemForm.LLM_TIMEOUT" placeholder="60" />
                  </ElFormItem>
                </div>

                <div class="pt-4">
                  <ElButton type="primary" :loading="loading" @click="saveSystemSettings" class="md:w-auto">
                    {{ t('settings.save_config') }}
                  </ElButton>
                </div>
              </div>

            </ElForm>
          </div>
        </ElTabPane>

        <!-- Tab 2: Model Management -->
        <ElTabPane :label="t('settings.models_tab')" name="models" class="h-full flex flex-col">
          <div class="p-4 flex justify-between items-center border-b">
            <h3 class="text-lg font-medium">{{ t('settings.registered_models') }}</h3>
            <ElButton type="primary" @click="openCreateModelDialog">
              {{ t('settings.add_model') }}
            </ElButton>
          </div>

          <div class="flex-1 p-4 overflow-auto">
            <ElTable :data="models" style="width: 100%" border stripe>
              <ElTableColumn prop="id" label="ID" width="60" />
              <ElTableColumn prop="name" :label="t('settings.model_form.display_name')" min-width="150" />
              <ElTableColumn prop="provider" :label="t('settings.model_form.provider')" width="100">
                <template #default="{ row }">
                  <span class="capitalize">{{ row.provider }}</span>
                </template>
              </ElTableColumn>
              <ElTableColumn prop="model_type" :label="t('settings.model_form.model_type')" width="100">
                <template #default="{ row }">
                  <span class="capitalize">{{ row.model_type }}</span>
                </template>
              </ElTableColumn>
              <ElTableColumn prop="model_name" :label="t('settings.model_form.model_id')" min-width="150" />
              <ElTableColumn prop="price_per_1k_tokens" :label="t('settings.model_form.price_per_1k')" width="180">
                <template #default="{ row }">
                   {{ row.price_per_1k_tokens }}
                </template>
              </ElTableColumn>
              <ElTableColumn prop="base_url" :label="t('settings.model_form.base_url')" min-width="200" show-overflow-tooltip />
              <ElTableColumn :label="t('common.settings')" width="120" fixed="right">
                <template #default="{ row }">
                   <div class="flex gap-2">
                      <ElButton type="primary" size="small" circle @click="openEditModelDialog(row)">
                        <template #icon>
                            <Edit class="w-4 h-4" />
                        </template>
                      </ElButton>
                      <ElButton type="danger" size="small" circle @click="handleDeleteModel(row)">
                         <template #icon>
                            <Trash2 class="w-4 h-4" />
                         </template>
                      </ElButton>
                   </div>
                </template>
              </ElTableColumn>
            </ElTable>
          </div>
        </ElTabPane>
      </ElTabs>
    </div>

    <!-- Add/Edit Model Dialog -->
    <ElDialog v-model="modelFormVisible" :title="isEditMode ? t('settings.edit_model') : t('settings.add_model')" width="500px">
      <ElForm :model="modelForm" label-position="top">
        <ElFormItem :label="t('settings.model_form.display_name')" required>
          <ElInput v-model="modelForm.name" placeholder="e.g., GPT-4o" />
        </ElFormItem>
        
        <ElFormItem :label="t('settings.model_form.provider')" required>
          <ElSelect v-model="modelForm.provider" class="w-full">
            <ElOption v-for="opt in providerOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </ElSelect>
        </ElFormItem>

        <ElFormItem :label="t('settings.model_form.model_type')" required>
          <ElSelect v-model="modelForm.model_type" class="w-full">
            <ElOption v-for="opt in modelTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </ElSelect>
        </ElFormItem>

        <ElFormItem :label="t('settings.model_form.model_id')" required>
          <ElInput v-model="modelForm.model_name" placeholder="e.g., gpt-4o or llama3" />
          <div class="text-xs text-muted-foreground mt-1">{{ t('settings.model_form.model_id_desc') }}</div>
        </ElFormItem>

        <ElFormItem :label="t('settings.model_form.price_per_1k')">
          <ElInputNumber v-model="modelForm.price_per_1k_tokens" :min="0" :step="0.001" :precision="4" class="w-full" />
        </ElFormItem>

        <ElFormItem :label="t('settings.model_form.base_url')">
          <ElInput v-model="modelForm.base_url" placeholder="Optional. e.g., http://localhost:11434" />
        </ElFormItem>

        <ElFormItem :label="t('settings.model_form.api_key')">
          <ElInput v-model="modelForm.api_key" type="password" show-password placeholder="Optional" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <span class="dialog-footer">
          <ElButton @click="modelFormVisible = false">{{ t('common.cancel') }}</ElButton>
          <ElButton type="primary" :loading="loading" @click="handleSaveModel">
            {{ isEditMode ? t('common.confirm') : t('settings.add_model') }}
          </ElButton>
        </span>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
:deep(.el-tabs__content) {
  padding: 0;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
:deep(.el-tabs__header) {
  margin: 0;
  background-color: var(--el-fill-color-light);
}
</style>