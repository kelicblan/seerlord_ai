<script setup lang="ts">
import { onMounted, ref, watch, nextTick, computed, reactive } from 'vue'
import { useAgent } from '@/composables/useAgent'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/axios'
import { uploadFile } from '@/api/files'
import { ElMessage, ElProgress } from 'element-plus'
import { useMediaQuery } from '@vueuse/core'

import { Loader2, Sparkles, Paperclip, Mic, ArrowUp, History, MessageSquarePlus, Briefcase, GitBranch, X, FileText } from 'lucide-vue-next'
import { MarkdownRender } from 'markstream-vue'
import 'markstream-vue/index.css'
import ThoughtProcess from '@/components/ThoughtProcess.vue'

const {
  plugins,
  selectedPlugin,
  messages,
  isThinking,
  metrics,
  logs,
  graphData,
  nodeStatuses,
  mcpStatus,
  llmContexts,
  skillExecutionData,
  fetchPlugins,
  fetchMCPStatus,
  fetchGraph,
  sendMessage,
  createNewSession,
  loadSession
} = useAgent()

const { locale, t } = useI18n()
const route = useRoute()
const router = useRouter()

// 按需加载 mermaid：避免把图渲染相关的大依赖打进首屏包
let mermaidApi: (typeof import('mermaid'))['default'] | null = null
let mermaidInitialized = false
const getMermaid = async () => {
  if (mermaidApi) return mermaidApi
  const mod = await import('mermaid')
  mermaidApi = mod.default
  return mermaidApi
}

const applicationPlugins = computed(() => {
  return plugins.value.filter(p => !p.type || p.type === 'application')
})

const handleNewSession = () => {
  createNewSession()
  // Remove query param if exists
  if (route.query.thread_id) {
    router.replace({ name: 'home' })
  }
}


const userInput = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const graphContainer = ref<HTMLElement | null>(null)
const activeRightTab = ref('logs')
const isLg = useMediaQuery('(min-width: 1024px)')
const splitterLayout = computed(() => (isLg.value ? 'horizontal' : 'vertical'))
const leftPanelSize = ref<string | number>('55%')
const rightPanelSize = ref<string | number>('45%')

// Helper to get localized plugin name
const getPluginName = (plugin: any) => {
  const isChinese = locale.value === 'zh-CN' || locale.value === 'zh-TW'
  return (isChinese && plugin.name_zh) ? plugin.name_zh : plugin.name
}

const formatStatusStatistic = () => t('common.status_' + metrics.status)

const formatTokensInOutStatistic = () => `${metrics.inputTokens} / ${metrics.outputTokens}`

// Auto-scroll to bottom of chat
watch(() => messages.value.length, () => {
  nextTick(() => {
    scrollToBottom()
  })
})

watch(() => messages.value[messages.value.length - 1]?.content, () => {
  scrollToBottom()
}, { deep: true })

const scrollToBottom = () => {
  const el = messagesContainer.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

// Initialize Mermaid
onMounted(() => {
  fetchPlugins()
  fetchMCPStatus()

  // Check for thread_id in query
  if (route.query.thread_id) {
    const threadId = route.query.thread_id as string
    loadSession(threadId)
  }
})

// Watch for route changes to handle browser back/forward or direct navigation
watch(() => route.query.thread_id, (newId) => {
  if (newId) {
    loadSession(newId as string)
  } else {
    // If thread_id is removed (e.g. new session), we might already have handled it in handleNewSession
    // But if it's via back button to root, we should ensure we are in a new session state or keep current
    // For now, let's assume if no thread_id, we don't force a reload unless it's explicit
  }
})

// Watch for graph data changes to render mermaid
watch(graphData, async (newData) => {
  if (newData && graphContainer.value) {
    try {
      graphContainer.value.innerHTML = ''
      const mermaid = await getMermaid()
      if (!mermaidInitialized) {
        mermaid.initialize({ startOnLoad: false, theme: 'default' })
        mermaidInitialized = true
      }
      const { svg } = await mermaid.render('mermaidSvg' + Date.now(), newData)
      graphContainer.value.innerHTML = svg
    } catch (e) {
      console.error('Mermaid render error:', e)
      if (graphContainer.value) graphContainer.value.innerText = t('common.graph_render_failed')
    }
  }
})

// Watch for node status changes to update graph styles
watch(nodeStatuses, (newStatuses) => {
  if (!graphContainer.value) return

  Object.entries(newStatuses).forEach(([nodeName, status]) => {
    // Mermaid renders nodes with ids or classes containing the node name
    // However, exact selection depends on how Mermaid generates SVG.
    // Usually text content of the node label is the best bet if IDs are internal.

    // We try to find nodes by text content similar to the index.html logic
    const nodes = graphContainer.value?.querySelectorAll('.node')
    if (nodes) {
      nodes.forEach((node: Element) => {
        if (node.textContent?.trim() === nodeName) {
          node.classList.remove('node-running', 'node-completed')
          if (status !== 'idle') {
            node.classList.add(`node-${status}`)
          }
        }
      })
    }
  })
}, { deep: true })

// Watch for plugin selection change
watch(selectedPlugin, (newVal) => {
  if (newVal) {
    fetchGraph(newVal)
  }
})

const isDownloadingPdf = ref(false)
const isDownloadingPpt = ref(false)
const isDownloadingDocx = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const isUploadLayerOpen = ref(false)

interface UploadedFile {
  id: string
  name: string
  size: string
  path: string
  status: 'uploading' | 'done' | 'error'
  progress: number
}

const uploadedFiles = ref<UploadedFile[]>([])

/**
 * 打开上传图层：悬浮在输入框上方，不占用布局高度
 */
const openUploadLayer = () => {
  isUploadLayerOpen.value = true
}

/**
 * 关闭上传图层
 */
const closeUploadLayer = () => {
  isUploadLayerOpen.value = false
}

/**
 * 切换上传图层显示状态
 */
const toggleUploadLayer = () => {
  isUploadLayerOpen.value = !isUploadLayerOpen.value
}

/**
 * 触发“回形针”按钮：先拉出上传图层
 */
const triggerFileUpload = () => {
  toggleUploadLayer()
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 判断文件类型是否允许上传
 */
const isAllowedUploadFile = (file: File) => {
  const name = file.name.toLowerCase()
  return name.endsWith('.docx') || name.endsWith('.pdf') || name.endsWith('.md') || name.endsWith('.txt')
}

/**
 * 上传单个文件：写入列表并调用后端接口
 */
const uploadOneFile = async (file: File) => {
  if (!isAllowedUploadFile(file)) {
    ElMessage.warning(t('common.upload_unsupported_type'))
    return
  }

  const fileId = `${Date.now()}-${Math.random().toString(16).slice(2)}`

  // 添加到上传列表（用于展示进度/状态）
  const newFile: UploadedFile = reactive({
    id: fileId,
    name: file.name,
    size: formatFileSize(file.size),
    path: '',
    status: 'uploading',
    progress: 0
  })
  uploadedFiles.value.push(newFile)

  try {
    const formData = new FormData()
    formData.append('file', file)

    const response = await uploadFile(formData, (progressEvent) => {
      if (progressEvent.total) {
        newFile.progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
      }
    })

    newFile.path = response.data.file_path
    newFile.status = 'done'
    newFile.progress = 100
  } catch (error) {
    console.error('Upload error:', error)
    newFile.status = 'error'
    ElMessage.error(t('common.upload_failed'))
  }
}

/**
 * 点击“+”选择文件
 */
const selectUploadFile = () => {
  openUploadLayer()
  fileInput.value?.click()
}

/**
 * 处理 input 选择文件的回调
 */
const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  try {
    const file = target.files?.item(0)
    if (!file) return
    await uploadOneFile(file)
  } finally {
    // 重置 input，确保同名文件重复选择也会触发 change
    target.value = ''
  }
}

/**
 * 拖拽上传：将文件拖到上传区域后直接上传
 */
const handleDropUpload = async (event: DragEvent) => {
  const file = event.dataTransfer?.files?.item(0)
  if (!file) return
  openUploadLayer()
  await uploadOneFile(file)
}

const removeFile = (index: number) => {
  uploadedFiles.value.splice(index, 1)
}

/**
 * 调用后端 md_to_pdf 工具将 Markdown 内容转换为 PDF 并下载
 * @param content Markdown 内容
 */
const downloadPdf = async (content: string) => {
  if (!content) return
  if (isDownloadingPdf.value) return

  isDownloadingPdf.value = true
  try {
    ElMessage.info('正在生成 PDF...')
    const response = await api.post('/api/v1/tools/md_to_pdf', { content }, {
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `conversation_${new Date().getTime()}.pdf`)
    document.body.appendChild(link)
    link.click()

    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('PDF 下载成功')
  } catch (error) {
    console.error('Failed to download PDF:', error)
    ElMessage.error('生成 PDF 失败')
  } finally {
    isDownloadingPdf.value = false
  }
}

/**
 * 调用后端 md_to_ppt 工具将 Markdown 内容转换为 PPT 并下载
 * @param content Markdown 内容
 */
const generateAndDownloadPpt = async (content: string) => {
  if (!content) return
  if (isDownloadingPpt.value) return

  isDownloadingPpt.value = true
  try {
    ElMessage.info('正在生成 PPT...')
    // 这里我们调用一个专门的API，它会调用MCP工具生成PPT并返回文件流
    const response = await api.post('/api/v1/tools/md_to_ppt', { content }, {
      responseType: 'blob'
    })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `presentation_${new Date().getTime()}.pptx`)
    document.body.appendChild(link)
    link.click()

    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('PPT 下载成功')
  } catch (error) {
    console.error('Failed to download PPT:', error)
    ElMessage.error('生成 PPT 失败')
  } finally {
    isDownloadingPpt.value = false
  }
}

/**
 * 获取用于导出的 Markdown：导出当前会话区域（聊天窗口）的全部内容
 */
const getConversationExportMarkdown = () => {
  const parts: string[] = []
  for (const msg of messages.value) {
    const content = (msg?.content ?? '').trim()
    if (!content) continue

    const roleLabel = msg.role === 'user'
      ? '用户'
      : msg.role === 'ai'
        ? 'AI'
        : String(msg.role ?? 'unknown')

    parts.push(`### ${roleLabel}\n\n${content}`)
  }
  return parts.join('\n\n---\n\n')
}

/**
 * 调用后端 md_to_docx_tool 工具将 Markdown 内容转换为 DOCX 并下载
 */
const generateAndDownloadDocx = async () => {
  const content = getConversationExportMarkdown()
  if (!content.trim()) {
    ElMessage.warning('没有可导出的内容')
    return
  }
  if (isDownloadingDocx.value) return

  isDownloadingDocx.value = true
  try {
    ElMessage.info('正在生成 DOCX...')
    const response = await api.post('/api/v1/tools/md_to_docx', { content }, { responseType: 'blob' })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `conversation_${new Date().getTime()}.docx`)
    document.body.appendChild(link)
    link.click()

    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('DOCX 下载成功')
  } catch (error) {
    console.error('Failed to download DOCX:', error)
    ElMessage.error('生成 DOCX 失败')
  } finally {
    isDownloadingDocx.value = false
  }
}

const handleSend = async () => {
  // Check if we have files to send even if input is empty
  const hasFiles = uploadedFiles.value.length > 0 && uploadedFiles.value.every(f => f.status === 'done')

  if ((!userInput.value.trim() && !hasFiles) || isThinking.value) return

  let text = userInput.value

  // Append file info to text if present
  if (hasFiles) {
    const fileInfos = uploadedFiles.value.map(f => `[附件: ${f.path}]`).join('\n')
    // If text is empty, provide a default prompt
    if (!text.trim()) {
      text = `我上传了以下文件，请分析：\n${fileInfos}`
    } else {
      text = `${text}\n\n${fileInfos}`
    }
  }

  userInput.value = ''
  uploadedFiles.value = [] // Clear files after send
  closeUploadLayer()

  await sendMessage(text, locale.value)
}
</script>

<template>
  <div>
    <ElSplitter class="h-full" :layout="splitterLayout" lazy>
      <ElSplitterPanel v-model:size="leftPanelSize" collapsible min="280">
        <ElCard shadow="never" class="flex flex-col h-full mr-1">
          <template #header>
            <div class="text-base flex justify-between items-right text-primary">
              <span>{{ t('common.chat') }}</span>
              <div class="flex gap-2">
                <ElSelect v-model="selectedPlugin" class="w-[220px]" :placeholder="t('common.select_agent')" filterable
                  clearable>
                  <ElOption v-for="plugin in applicationPlugins" :key="plugin.id" :label="getPluginName(plugin)"
                    :value="plugin.id" />
                </ElSelect>

                <ElButton type="primary" text circle @click="router.push('/history')" :title="t('common.history')"
                  :icon="History">
                </ElButton>

                <ElButton type="primary" text circle @click="handleNewSession" :title="t('common.new_session')"
                  :icon="MessageSquarePlus">
                </ElButton>
              </div>
            </div>
          </template>

          <div class="flex-1 p-0 flex flex-col min-h-0">
            <div ref="messagesContainer" class="min-h-0 h-[calc(100vh-250px)] overflow-auto p-4">
              <div class="space-y-4">
                <div v-for="(msg, index) in messages" :key="index" class="flex flex-col group"
                  :class="msg.role === 'user' ? 'items-end' : 'items-start'">
                  <div class="max-w-[85%] rounded-lg px-4 py-2" :class="msg.role === 'user'
                    ? 'bg-gray text-foreground rounded-br-none'
                    : 'bg-muted text-foreground rounded-bl-none'">
                    <div class="prose dark:prose-invert max-w-none">
                      <ThoughtProcess
                        v-if="msg.role === 'ai' && ((msg.thoughts?.length ?? 0) > 0 || (isThinking && index === messages.length - 1))"
                        :steps="msg.thoughts || []" :isFinished="!isThinking || index !== messages.length - 1" />

                      <span v-if="!msg.content && ((msg.thoughts?.length ?? 0) === 0)">{{ t('common.waiting_content')
                        }}</span>
                      <MarkdownRender v-else-if="msg.content" :content="msg.content" />
                    </div>
                  </div>
                  <div class="flex items-center gap-2 mt-1">
                    <span class="text-xs text-muted-foreground">
                      {{ new Date(msg.timestamp).toLocaleTimeString() }}
                    </span>
                    <!-- 下载 PDF 按钮 -->
                    <ElButton v-if="msg.role === 'ai' && msg.content" link type="primary"
                      class="opacity-0 group-hover:opacity-100 transition-opacity" @click="downloadPdf(msg.content)"
                      :loading="isDownloadingPdf" title="下载为 PDF">
                      <img src="@/assets/icon/pdf.svg" alt="PDF" class="w-4 h-4" />
                    </ElButton>

                    <!-- 生成 PPT 按钮 -->
                    <ElButton v-if="msg.role === 'ai' && msg.content" link type="primary"
                      class="opacity-0 group-hover:opacity-100 transition-opacity"
                      @click="generateAndDownloadPpt(msg.content)" :loading="isDownloadingPpt" title="生成并下载 PPT">
                      <img src="@/assets/icon/pptx.svg" alt="PPT" class="w-4 h-4" />
                    </ElButton>

                    <!-- 生成 docx 按钮 -->
                    <ElButton v-if="msg.role === 'ai' && msg.content" link type="primary"
                      class="opacity-0 group-hover:opacity-100 transition-opacity" @click="generateAndDownloadDocx"
                      :loading="isDownloadingDocx" title="生成并下载 DOCX">
                      <img src="@/assets/icon/docx.svg" alt="DOCX" class="w-4 h-4" />
                    </ElButton>
                  </div>
                </div>
                <div v-if="isThinking && messages[messages.length - 1]?.role !== 'ai'" class="flex items-start">
                  <div class="bg-muted text-foreground rounded-lg rounded-bl-none px-4 py-2 flex items-center gap-2">
                    <Loader2 class="h-4 w-4 animate-spin" />
                    <span>{{ t('common.thinking') }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-background border-t p-2 shrink-0 sticky bottom-0 relative">
              <input type="file" ref="fileInput" class="hidden" @change="handleFileUpload"
                accept=".docx,.pdf,.md,.txt" />

              <Transition name="upload-layer">
                <div v-if="isUploadLayerOpen" class="absolute left-2 right-2 bottom-full mb-2 z-50">
                    <div class="rounded-xl border bg-background shadow-lg overflow-hidden">
                      <div class="flex items-center justify-between px-4 py-3 border-b">
                      <div class="text-sm font-semibold">{{ t('common.upload_file') }}</div>
                      <ElButton type="primary" text circle class="h-8 w-8 text-muted-foreground hover:text-foreground"
                        @click="closeUploadLayer">
                        <X class="h-4 w-4" />
                      </ElButton>
                    </div>

                    <div class="p-4">
                      <div v-if="uploadedFiles.length === 0"
                        class="h-28 rounded-lg border border-dashed border-border bg-muted/30 flex flex-col items-center justify-center gap-1 cursor-pointer select-none"
                        @click="selectUploadFile" @dragover.prevent @drop.prevent="handleDropUpload">
                        <FileText class="h-7 w-7 text-muted-foreground" />
                        <div class="text-sm font-medium">{{ t('common.upload_file') }}</div>
                        <div class="text-xs text-muted-foreground">{{ t('common.upload_click_or_drag') }}</div>
                      </div>

                      <div v-else class="flex gap-3 overflow-x-auto pb-1">
                        <div v-for="(file, index) in uploadedFiles" :key="file.id"
                          class="w-[260px] shrink-0 rounded-lg border bg-muted/20 p-3 relative"
                          :class="file.status === 'error' ? 'border-red-300 bg-red-50/30' : 'border-border'">
                          <ElButton type="danger" text circle size="small" class="absolute right-2 top-2"
                            @click="removeFile(index)">
                            <X class="w-4 h-4" />
                          </ElButton>

                          <div class="flex items-center gap-3 overflow-hidden pr-8">
                            <div class="w-10 h-10 rounded bg-red-100 flex items-center justify-center shrink-0">
                              <FileText class="w-5 h-5 text-red-500" />
                            </div>
                            <div class="flex flex-col min-w-0">
                              <span class="text-sm font-medium truncate">{{ file.name }}</span>
                              <span class="text-xs text-muted-foreground">{{ file.size }}</span>
                            </div>
                          </div>

                          <div v-if="file.status === 'uploading'" class="mt-3">
                            <ElProgress :percentage="file.progress" :show-text="false" :stroke-width="4" />
                          </div>
                          <div v-else-if="file.status === 'error'" class="mt-3 text-xs text-red-600">
                            {{ t('common.upload_failed') }}
                          </div>
                        </div>

                        <button type="button"
                          class="w-[260px] shrink-0 rounded-lg border border-dashed border-border bg-muted/10 hover:bg-muted/20 transition-colors flex items-center justify-center"
                          @click="selectUploadFile">
                          <div class="text-4xl text-muted-foreground leading-none">+</div>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </Transition>

              <form @submit.prevent="handleSend"
                class="relative rounded-xl border bg-background focus-within:ring-1 focus-within:ring-ring transition-all">
                <textarea v-model="userInput" :placeholder="t('common.input_placeholder')" :disabled="isThinking"
                  class="min-h-[60px] w-full resize-none border-0 bg-transparent px-4 py-3 text-sm focus-visible:ring-0 shadow-none placeholder:text-muted-foreground focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                  @keydown.enter.exact.prevent="handleSend"></textarea>

                <div class="flex items-center justify-between p-2">
                  <!-- Left: Optimize -->
                  <ElButton type="primary" text circle class="h-8 w-8 text-muted-foreground hover:text-foreground">
                    <Sparkles class="h-4 w-4" />
                  </ElButton>

                  <!-- Right: Tools + Send -->
                  <div class="flex items-center gap-2">
                    <ElButton type="primary" text circle class="h-8 w-8 text-muted-foreground hover:text-foreground"
                      @click="triggerFileUpload">
                      <Paperclip class="h-4 w-4" />
                    </ElButton>
                    <ElButton type="primary" text circle class="h-8 w-8 text-muted-foreground hover:text-foreground">
                      <Mic class="h-4 w-4" />
                    </ElButton>
                    <ElButton type="primary" native-type="submit"
                      :disabled="isThinking || (!userInput.trim() && uploadedFiles.length === 0)"
                      class="h-8 rounded-md px-3" size="small">
                      {{ t('common.send') }}
                      <ArrowUp class="ml-2 h-4 w-4" />
                    </ElButton>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </ElCard>
      </ElSplitterPanel>

      <ElSplitterPanel v-model:size="rightPanelSize" collapsible min="320">
        <div class="flex flex-col gap-2 h-full ml-1">
          <!-- Metrics -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="rounded-md border bg-card p-2">
              <ElStatistic :title="t('common.status')" :value="metrics.duration" :formatter="formatStatusStatistic"
                :value-style="{ color: 'var(--el-color-primary)', fontWeight: 700 }" />
            </div>
            <div class="rounded-md border bg-card p-2">
              <ElStatistic :title="t('common.duration')" :value="metrics.duration" :value-style="{ fontWeight: 700 }">
                <template #suffix>s</template>
              </ElStatistic>
            </div>
            <div class="rounded-md border bg-card p-2">
              <ElStatistic :title="t('common.total_tokens')" :value="metrics.totalTokens"
                :value-style="{ fontWeight: 700 }" />
            </div>
            <div class="rounded-md border bg-card p-2 overflow-hidden">
              <ElStatistic :title="t('common.tokens_in_out')" :value="metrics.totalTokens"
                :formatter="formatTokensInOutStatistic" />
            </div>

            <!-- MCP Metrics -->
            <ElCard shadow="never" class="col-span-2 md:col-span-4">
              <div class="p-2">
                <div class="text-xs text-muted-foreground mb-1">{{ t('common.mcp_services') }}</div>
                <div v-if="!mcpStatus" class="text-sm">{{ t('common.loading') }}</div>
                <div v-else>
                  <div class="text-sm font-bold text-blue-600 mb-2">
                    {{ t('common.total_servers') }}: {{ mcpStatus.total_servers }} | {{ t('common.total_tools') }}: {{
                    mcpStatus.total_tools }}
                  </div>
                  <!-- <div class="flex flex-wrap gap-2">
                    <ElTag v-for="server in mcpStatus.servers" :key="server.name"
                      :type="server.status === 'connected' ? 'success' : 'danger'" effect="light">
                      <div class="flex items-center gap-2">
                        <div class="w-2 h-2 rounded-full"
                          :class="server.status === 'connected' ? 'bg-green-500' : 'bg-red-500'"></div>
                        <span>{{ server.name }}</span>
                        <span class="text-xs opacity-80">({{ server.tool_count }})</span>
                      </div>
                    </ElTag>
                  </div> -->
                </div>
              </div>
            </ElCard>
          </div>

          <!-- Tabs: Logs & Graph -->
          <ElTabs v-model="activeRightTab" type="border-card" class="w-full shadow-sm">
            <ElTabPane name="logs" :label="t('common.execution_log')">
              <div class="h-[calc(100vh-270px)] overflow-auto">
                <div class="p-2 font-mono text-xs space-y-1">
                  <div v-for="(log, i) in logs" :key="i" class="border-b border-border/50 pb-1 last:border-0">
                    <span class="text-muted-foreground">[{{ log.time }}]</span>
                    <ElTag type="info" effect="plain" class="mx-2">
                      {{ log.type }}
                    </ElTag>
                    <span class="text-foreground">{{ log.detail }}</span>
                  </div>
                  <div v-if="logs.length === 0" class="text-muted-foreground p-2">{{ t('common.waiting_execution') }}
                  </div>
                </div>
              </div>
            </ElTabPane>
            <ElTabPane name="graph" :label="t('common.workflow_graph')">
              <div class="h-[calc(100vh-270px)] overflow-auto">
                <div ref="graphContainer" class="flex justify-center items-center min-h-[200px] p-4">
                  {{ t('common.select_agent_graph') }}
                </div>
              </div>
            </ElTabPane>
            <ElTabPane name="context" :label="t('common.context')">
              <div class="h-[calc(100vh-270px)] overflow-auto">
                <div v-if="llmContexts.length === 0" class="text-muted-foreground">{{ t('common.no_data') }}</div>
                <div v-for="ctx in llmContexts" :key="ctx.id" class="mb-4 p-3 bg-card">
                  <div class="flex justify-between items-center mb-2 border-b pb-2">
                    <div class="font-bold text-sm">{{ ctx.model }}</div>
                    <div class="text-xs text-muted-foreground">{{ ctx.timestamp }}</div>
                  </div>
                  <div class="space-y-2">
                    <div v-for="(msg, idx) in ctx.prompts" :key="idx" class="text-sm">
                      <div class="font-semibold text-xs uppercase text-muted-foreground mb-1">{{ msg.type || msg.role }}
                      </div>
                      <div class="whitespace-pre-wrap bg-muted/50 p-2 rounded text-xs font-mono break-words">{{
                        msg.content }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </ElTabPane>

            <!-- New Skills Tab -->
            <ElTabPane name="skills" :label="t('common.skills_tab')">
                <template #label>
                  <span class="flex items-center gap-2">
                    {{ t('common.skills_tab') }}
                    <span v-if="skillExecutionData.evolutions.length > 0"
                      class="flex h-2 w-2 rounded-full bg-red-500"></span>
                  </span>
                </template>

                <div class="h-full overflow-y-auto p-4 space-y-6">
                  <!-- 1. Evolution Events (High Priority) -->
                  <div v-if="skillExecutionData.evolutions.length > 0" class="space-y-3">
                    <div class="flex items-center gap-2 text-amber-600 font-bold border-b pb-2 border-amber-100">
                      <GitBranch class="w-4 h-4" />
                      <span>{{ t('common.skills_evolutions_title') }}</span>
                    </div>
                    <div v-for="(ev, idx) in skillExecutionData.evolutions" :key="idx"
                      class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm animate-in fade-in slide-in-from-bottom-2">
                      <div class="font-medium text-amber-800">{{ ev.skill_name }}</div>
                      <div class="text-amber-600 text-xs mt-1">{{ ev.change }}</div>
                      <div class="mt-2 text-xs bg-white/50 p-1 rounded text-amber-900/70">
                        {{ t('common.skills_evolution_note') }}
                      </div>
                    </div>
                  </div>

                  <!-- 2. Used Skills -->
                  <div class="space-y-3">
                    <div class="flex items-center gap-2 text-gray-700 font-bold border-b pb-2">
                      <Briefcase class="w-4 h-4" />
                      <span>{{ t('common.skills_used_title') }}</span>
                      <span class="text-xs font-normal text-gray-400 ml-auto">
                        {{ t('common.skills_active_count', { count: skillExecutionData.usedSkills.length }) }}
                      </span>
                    </div>

                    <div v-if="skillExecutionData.usedSkills.length === 0"
                      class="text-gray-400 text-sm py-4 text-center italic">
                      {{ t('common.skills_none') }}
                    </div>

                    <div v-for="skill in skillExecutionData.usedSkills" :key="skill.id"
                      class="rounded-md hover:bg-gray-50 transition-colors">
                      <div class="flex justify-between items-start">
                        <span class="font-medium text-gray-900">{{ skill.name }}</span>
                        <span :class="{
                          'bg-blue-100 text-blue-700': skill.level === 1,
                          'bg-green-100 text-green-700': skill.level === 2,
                          'bg-orange-100 text-orange-700': skill.level === 3,
                        }" class="px-2 py-0.5 rounded text-xs font-medium">
                          L{{ skill.level }}
                        </span>
                      </div>
                      <div class="text-xs text-gray-500 mt-1 font-mono">ID: {{ skill.id }}</div>

                      <div class="mt-3 border-t pt-3">
                        <div class="text-xs font-semibold text-gray-600 mb-2">
                          {{ t('common.skills_detail_title') }}
                        </div>
                        <div v-if="!skillExecutionData.usedSkillDetails?.[skill.id]" class="text-xs text-gray-400 italic">
                          {{ t('common.skills_detail_loading') }}
                        </div>
                        <div v-else class="text-xs">
                          <div class="text-gray-600 mb-2">
                            {{ skillExecutionData.usedSkillDetails[skill.id].description }}
                          </div>
                          <div class="bg-muted/50 rounded p-2">
                            <MarkdownRender :content="skillExecutionData.usedSkillDetails[skill.id].content" />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
            </ElTabPane>
          </ElTabs>
        </div>
      </ElSplitterPanel>
    </ElSplitter>
  </div>
</template>

<style scoped>
/* Ensure mermaid graph is visible */
:deep(svg) {
  max-width: 100%;
  height: auto;
}

:deep(.upload-layer-enter-active),
:deep(.upload-layer-leave-active) {
  transition: opacity 160ms ease, transform 160ms ease;
}

:deep(.upload-layer-enter-from),
:deep(.upload-layer-leave-to) {
  opacity: 0;
  transform: translateY(8px);
}

:deep(.el-card__header) {
  padding: 8px;
}

:deep(.el-card__body) {
  padding: 0 !important;
}

:deep(.el-statistic__content) {
  font-size: 16px;
}

:deep(.el-tabs--border-card>.el-tabs__content) {
  padding: 0 !important;
}

:deep(.el-button+.el-button) {
  margin-left: 0;
}

:deep(.el-splitter-bar__dragger:after) {
  background-color: #fff !important;
}

:deep(.el-splitter-bar__dragger:before) {
  background-color: #fff !important;
}

:deep(.overflow-hidden) {
  overflow: hidden !important;
}
:deep(.el-statistic__head){
  font-weight: 700;
    width: 90px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
}

.bg-gray {
  background-color: #ebebeb;
}

.docx-btn {
  background: url('@/assets/icon/docx.svg') no-repeat center center;
  background-size: 24px 24px;
}

.pptx-btn {
  background: url('@/assets/icon/pptx.svg') no-repeat center center;
  background-size: 24px 24px;
}

.pdf-btn {
  background: url('@/assets/icon/pdf.svg') no-repeat center center;
  background-size: 24px 24px;
}

.xlsx-btn {
  background: url('@/assets/icon/xlsx.svg') no-repeat center center;
  background-size: 24px 24px;
}
</style>
