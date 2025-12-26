<template>
  <div class="h-full flex flex-col p-4">
    <div class="mb-4 flex justify-between items-center">
      <h2 class="text-xl font-bold">{{ $t('plaza.title') }}</h2>
      <div class="flex items-center gap-2">
        <span class="text-sm text-gray-500">{{ $t('plaza.filter_agent') }}:</span>
        <el-select v-model="selectedAgent" clearable :placeholder="$t('plaza.all_agents')" style="width: 200px">
          <el-option
            v-for="plugin in plugins"
            :key="plugin.id"
            :label="plugin.name_zh || plugin.name || plugin.id"
            :value="plugin.id"
          />
        </el-select>
      </div>
    </div>

    <div v-loading="loading" class="flex-1 overflow-auto flex flex-col">
      <el-empty v-if="artifacts.length === 0" :description="$t('plaza.no_content')" />
      
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 flex-1 content-start">
        <el-card v-for="item in artifacts" :key="item.id" shadow="hover" class="flex flex-col">
          <template #header>
            <div class="flex justify-between items-start">
              <span class="font-bold truncate" :title="item.title || 'Untitled'">{{ item.title || 'Untitled' }}</span>
              <el-tag size="small">{{ getAgentName(item.agent_id) }}</el-tag>
            </div>
          </template>
          <div class="text-sm text-gray-500 mb-2 h-10 overflow-hidden text-ellipsis line-clamp-2">
            {{ getLocalizedText(item.description, locale) || '-' }}
          </div>
          <div class="text-xs text-gray-400 mb-4 flex justify-between items-center">
            <span>{{ formatTime(item.created_at) }}</span>
            <span v-if="item.total_tokens" class="bg-blue-50 text-blue-500 px-2 py-0.5 rounded text-xs font-mono">
               {{ item.total_tokens.toLocaleString() }} T
            </span>
          </div>
          <div class="mt-auto flex justify-end gap-2">
             <el-button type="primary" link @click="handlePreview(item)">{{ $t('plaza.preview') }}</el-button>
             <el-button v-if="item.type === 'file'" type="success" link @click="handleDownload(item)">{{ $t('plaza.download') }}</el-button>
          </div>
        </el-card>
      </div>

      <!-- Pagination -->
      <div class="mt-4 flex justify-end" v-if="total > 0">
        <el-pagination
          background
          layout="total, prev, pager, next, jumper"
          :total="total"
          :page-size="pageSize"
          v-model:current-page="currentPage"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- Preview Dialog -->
    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      width="80%"
      top="5vh"
      destroy-on-close
    >
      <div v-loading="previewLoading" class="h-[70vh] overflow-auto">
        <!-- Content Type -->
        <div v-if="previewData?.type === 'content'" class="content-preview">
           <MarkdownRender :content="previewData.content || ''" />
        </div>

        <!-- File Type -->
        <div v-else-if="previewData?.type === 'file'" class="w-full h-full">
           <!-- HTML File: Iframe -->
           <iframe
             v-if="isHtmlFile(previewData.filename)"
             :src="htmlIframeSrc"
             class="w-full h-full border-0"
           ></iframe>

           <div v-else-if="isOfficeFile(previewData.filename)" class="w-full h-full">
             <div v-if="officeRenderFailed" class="text-center">
               <el-icon class="text-6xl text-gray-300 mb-4"><Document /></el-icon>
               <p class="mb-4">{{ $t('plaza.file_preview_not_supported') }}</p>
               <el-button type="primary" @click="handleDownload(currentItem!)">
                 {{ $t('plaza.download_file') }} ({{ previewData.filename }})
               </el-button>
             </div>
             <VueOfficeDocx
               v-else-if="officeKind === 'docx' && officeSrc"
               :src="officeSrc"
               style="height: 100%;"
               @error="handleOfficeError"
             />
             <VueOfficeExcel
               v-else-if="officeKind === 'xlsx' && officeSrc"
               :src="officeSrc"
               style="height: 100%;"
               @error="handleOfficeError"
             />
             <VueOfficePptx
               v-else-if="officeKind === 'pptx' && officeSrc"
               :src="officeSrc"
               style="height: 100%;"
               @error="handleOfficeError"
             />
             <VueOfficePdf
               v-else-if="officeKind === 'pdf' && officeSrc"
               :src="officeSrc"
               style="height: 100%;"
               @error="handleOfficeError"
             />
           </div>
           
           <!-- Other Files: Message -->
           <div v-else class="text-center">
             <el-icon class="text-6xl text-gray-300 mb-4"><Document /></el-icon>
             <p class="mb-4">{{ $t('plaza.file_preview_not_supported') }}</p>
             <el-button type="primary" @click="handleDownload(currentItem!)">
               {{ $t('plaza.download_file') }} ({{ previewData.filename }})
             </el-button>
           </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listArtifacts, previewArtifact, type AgentArtifact, type ArtifactPreview } from '@/api/artifact'
import { getTenantApiKey } from '@/api/axios'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { useAgent } from '@/composables/useAgent'
import { MarkdownRender } from 'markstream-vue'
import 'markstream-vue/index.css'
import VueOfficeDocx from '@vue-office/docx'
import VueOfficeExcel from '@vue-office/excel'
import VueOfficePdf from '@vue-office/pdf'
import VueOfficePptx from '@vue-office/pptx'
import '@vue-office/docx/lib/index.css'
import '@vue-office/excel/lib/index.css'
import { getLocalizedText } from '@/lib/utils'

const { t, locale } = useI18n()
const loading = ref(false)
const artifacts = ref<AgentArtifact[]>([])
const selectedAgent = ref('')
const currentPage = ref(1)
const pageSize = ref(12)
const total = ref(0)

const previewVisible = ref(false)
const previewLoading = ref(false)
const previewTitle = ref('')
const previewData = ref<ArtifactPreview | null>(null)
const currentItem = ref<AgentArtifact | null>(null)
const htmlIframeSrc = ref('')
const htmlIframeObjectUrl = ref<string | null>(null)

type OfficeKind = 'docx' | 'xlsx' | 'pptx' | 'pdf'
const officeKind = ref<OfficeKind | null>(null)
const officeSrc = ref<ArrayBuffer | null>(null)
const officeRenderFailed = ref(false)

const { plugins, fetchPlugins } = useAgent()

// Computed
const agentLabelMap = computed(() => {
  const map = new Map<string, string>()
  for (const p of plugins.value) {
    map.set(p.id, p.name_zh || p.name || p.id)
  }
  return map
})

// Methods
const fetchArtifacts = async () => {
  loading.value = true
  try {
    const res = await listArtifacts(currentPage.value, pageSize.value, selectedAgent.value || undefined)
    artifacts.value = res.data.items
    total.value = res.data.total
  } catch (error) {
    console.error(error)
    ElMessage.error('Failed to load artifacts')
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchArtifacts()
}

watch(selectedAgent, () => {
  currentPage.value = 1
  fetchArtifacts()
})

const getAgentName = (agentId: string) => {
  return agentLabelMap.value.get(agentId) || agentId
}

const formatTime = (time: string) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const handlePreview = async (item: AgentArtifact) => {
  currentItem.value = item
  previewTitle.value = item.title || 'Preview'
  previewVisible.value = true
  previewLoading.value = true
  previewData.value = null
  officeKind.value = null
  officeSrc.value = null
  officeRenderFailed.value = false
  htmlIframeSrc.value = ''
  if (htmlIframeObjectUrl.value) {
    URL.revokeObjectURL(htmlIframeObjectUrl.value)
    htmlIframeObjectUrl.value = null
  }

  try {
    const res = await previewArtifact(item.id)
    previewData.value = res.data

    if (res.data.type === 'file' && isOfficeFile(res.data.filename)) {
      const kind = getOfficeKind(res.data.filename)
      if (kind) {
        officeKind.value = kind
        try {
          const token = localStorage.getItem('token') || sessionStorage.getItem('token')
          const headers: HeadersInit = {}
          if (token) headers['Authorization'] = `Bearer ${token}`
          const tenantKey = getTenantApiKey()
          if (tenantKey) headers['X-API-Key'] = tenantKey

          const response = await fetch(getDownloadUrl(item.id), { headers })
          if (!response.ok) {
            throw new Error(`Download failed: ${response.status} ${response.statusText}`)
          }
          officeSrc.value = await response.arrayBuffer()
        } catch (e: any) {
          console.error('Office Preview download failed:', e)
          ElMessage.error(t('plaza.preview') + ' ' + t('common.status_Error') + ': ' + e.message)
          officeRenderFailed.value = true
        }
      }
    }

    if (res.data.type === 'file' && isHtmlFile(res.data.filename)) {
      try {
        const token = localStorage.getItem('token') || sessionStorage.getItem('token')
        const headers: HeadersInit = {}
        if (token) headers['Authorization'] = `Bearer ${token}`
        const tenantKey = getTenantApiKey()
        if (tenantKey) headers['X-API-Key'] = tenantKey

        const response = await fetch(getDownloadUrl(item.id), { headers })
        
        if (!response.ok) {
          throw new Error(`Download failed: ${response.status} ${response.statusText}`)
        }
        
        const blob = await response.blob()
        const objectUrl = URL.createObjectURL(blob)
        htmlIframeObjectUrl.value = objectUrl
        htmlIframeSrc.value = objectUrl
      } catch (e: any) {
         console.error('HTML Preview download failed:', e)
         ElMessage.error(t('plaza.preview') + ' ' + t('common.status_Error') + ': ' + e.message)
         // Fallback or just stop
         htmlIframeSrc.value = '' 
       }
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('Failed to load preview')
    previewVisible.value = false
  } finally {
    previewLoading.value = false
  }
}

const getFilenameFromDisposition = (disposition?: string): string => {
  if (!disposition) return ''
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }
  const asciiMatch = disposition.match(/filename="?([^"]+)"?/i)
  return asciiMatch?.[1] || ''
}

const downloadBlob = (blob: Blob, filename: string) => {
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = filename
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(objectUrl)
}

const handleDownload = async (item: AgentArtifact) => {
  try {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const tenantKey = getTenantApiKey()
    if (tenantKey) headers['X-API-Key'] = tenantKey

    const response = await fetch(getDownloadUrl(item.id), { headers })
    if (!response.ok) throw new Error(`Download failed: ${response.status} ${response.statusText}`)

    const blob = await response.blob()
    const disposition = response.headers.get('content-disposition') || undefined
    const headerFilename = getFilenameFromDisposition(disposition)
    const fallbackFilename = previewData.value?.filename || item.title || `artifact_${item.id}`
    const filename = headerFilename || fallbackFilename
    downloadBlob(blob, filename)
  } catch (error: any) {
    console.error(error)
    ElMessage.error(t('plaza.download') + ' ' + t('common.status_Error') + ': ' + error.message)
  }
}

const getDownloadUrl = (id?: string) => {
  if (!id) return ''
  // Assuming API is at /api/v1
  // We need the full URL or relative to current origin if proxied
  // The backend route is /api/v1/artifact/{id}/download
  // Vite proxy usually maps /api/v1 to backend
  return `/api/v1/artifact/${id}/download`
}

const isHtmlFile = (filename?: string) => {
  if (!filename) return false
  return filename.toLowerCase().endsWith('.html') || filename.toLowerCase().endsWith('.htm')
}

const getOfficeKind = (filename?: string): OfficeKind | null => {
  if (!filename) return null
  const ext = filename.toLowerCase().split('.').pop()
  if (ext === 'docx' || ext === 'xlsx' || ext === 'pptx' || ext === 'pdf') return ext
  return null
}

const isOfficeFile = (filename?: string) => {
  return getOfficeKind(filename) !== null
}

const handleOfficeError = () => {
  officeRenderFailed.value = true
  ElMessage.error('Failed to render file preview')
}

watch(previewVisible, visible => {
  if (!visible) {
    previewData.value = null
    currentItem.value = null
    officeKind.value = null
    officeSrc.value = null
    officeRenderFailed.value = false
    htmlIframeSrc.value = ''
    if (htmlIframeObjectUrl.value) {
      URL.revokeObjectURL(htmlIframeObjectUrl.value)
      htmlIframeObjectUrl.value = null
    }
  }
})

onMounted(() => {
  fetchArtifacts()
  fetchPlugins()
})
</script>

<style scoped>
.content-preview {
  max-width: 900px;
  margin: 0 auto;
  padding: 12px 8px;
}
</style>
