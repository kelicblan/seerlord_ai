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

        <!-- Component Type -->
        <div v-else-if="previewData?.type === 'component'" class="w-full h-full overflow-auto bg-gray-50 p-4">
           <div class="bg-white shadow-sm min-h-full p-4 rounded relative">
             <component :is="dynamicComponent" v-bind="previewProps" v-if="dynamicComponent" />
             <div v-else class="text-center text-gray-400 py-10">
               {{ $t('common.loading') }}...
             </div>
           </div>
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
import { ref, computed, onMounted, watch, shallowRef, onErrorCaptured } from 'vue'
import { useI18n } from 'vue-i18n'
import * as Vue from 'vue'
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
import { loadModule } from 'vue3-sfc-loader'
import * as LucideVueNext from 'lucide-vue-next'
import * as ElementPlus from 'element-plus'

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
const dynamicComponent = shallowRef<any>(null)
const injectedStyles = ref<HTMLStyleElement[]>([])
const previewProps = ref<Record<string, any>>({})

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

/**
 * 清理 Vue 代码，移除 Markdown 代码块标记，并修复常见的运行时错误
 * @param code 原始代码字符串
 * @returns 清理后的代码
 */
const cleanVueCode = (code: string) => {
  let cleaned = code
  // 1. 尝试提取 Markdown 代码块
  const match = code.match(/```(?:vue|html|js|ts)?\s*([\s\S]*?)```/i)
  if (match && match[1]) {
    cleaned = match[1]
  }

  // 2. 确保包含基本的 SFC 标签，如果全是文本则尝试提取
  if (!cleaned.includes('<template') && !cleaned.includes('<script')) {
    // 尝试在全文中寻找标签块
    const templateMatch = code.match(/<template[\s\S]*?<\/template>/i)
    const scriptMatch = code.match(/<script[\s\S]*?<\/script>/i)
    const styleMatch = code.match(/<style[\s\S]*?<\/style>/i)
    
    let parts = []
    if (scriptMatch) parts.push(scriptMatch[0])
    if (templateMatch) parts.push(templateMatch[0])
    if (styleMatch) parts.push(styleMatch[0])
    
    if (parts.length > 0) {
      cleaned = parts.join('\n')
    }
  }
  
  // 3. 终极 Hack: 替换 .trim() 为 ?.trim() 以防止 undefined 报错
  // 这里的正则替换比较激进，假设所有 .trim() 调用前都可能为空
  // 注意：这可能会破坏某些合法的逻辑，但在预览场景下，防崩优于正确
  cleaned = cleaned.replace(/(\S+)\.trim\(\)/g, '$1?.trim()')
  // 修复常见的 props.xxx.trim() 或 var.trim()
  // 上面的正则可能匹配到 props.title.trim() -> props.title?.trim()，这是合法的 JS
  
  return cleaned
}

const generateMockProps = (component: any) => {
  const props: Record<string, any> = {}
  if (!component || !component.props) return props
  
  const compProps = component.props
  
  if (Array.isArray(compProps)) {
    compProps.forEach(key => {
      props[key] = 'Mock Data'
    })
  } else {
    for (const key in compProps) {
      const def = compProps[key]
      if (def === String || (def && def.type === String)) {
        props[key] = 'Mock String'
      } else if (def === Number || (def && def.type === Number)) {
        props[key] = 0
      } else if (def === Boolean || (def && def.type === Boolean)) {
        props[key] = false
      } else if (def === Array || (def && def.type === Array)) {
        props[key] = []
      } else if (def === Object || (def && def.type === Object)) {
        props[key] = {}
      } else {
        props[key] = null
      }
    }
  }
  return props
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

    if (res.data.type === 'file' && isVueFile(res.data.filename)) {
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
        
        const text = await response.text()
        const cleanedText = cleanVueCode(text)
        
        // 检查是否包含有效的 Vue SFC 结构
        if (!cleanedText.includes('<template') && !cleanedText.includes('<script')) {
          throw new Error(t('plaza.invalid_vue_code'))
        }

        // Load module
        const options = {
          moduleCache: {
            vue: Vue,
            'lucide-vue-next': LucideVueNext,
            // 添加 Element Plus 支持，确保生成的组件可以使用 el- 组件
            'element-plus': ElementPlus
          },
          getFile: () => Promise.resolve(cleanedText),
          addStyle: (textContent: string) => {
            const style = document.createElement('style')
            style.textContent = textContent
            document.head.appendChild(style)
            injectedStyles.value.push(style)
          },
        }

        const resModule = await loadModule('/component.vue', options)
        const component = resModule.default || resModule
        
        previewProps.value = generateMockProps(component)
        dynamicComponent.value = component

        previewData.value = {
          ...res.data,
          type: 'component',
        }
      } catch (e: any) {
         console.error('Vue Preview download failed:', e)
         ElMessage.error(t('plaza.preview') + ' ' + t('common.status_Error') + ': ' + e.message)
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

const isVueFile = (filename?: string) => {
  if (!filename) return false
  return filename.toLowerCase().endsWith('.vue')
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
    if (injectedStyles.value.length > 0) {
      injectedStyles.value.forEach(style => {
        if (style.parentNode) {
          style.parentNode.removeChild(style)
        }
      })
      injectedStyles.value = []
    }
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

onErrorCaptured((err) => {
  console.error('Captured Error in Preview:', err)
  ElMessage.error(t('common.status_Error') + ': ' + err.message)
  return false // Stop propagation
})
</script>

<style scoped>
.content-preview {
  max-width: 900px;
  margin: 0 auto;
  padding: 12px 8px;
}
</style>
