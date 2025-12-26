<template>
  <div class="flex gap-2">
    <!-- Left Sidebar: KB List -->
    <div class="w-[220px] flex-none bg-white rounded-lg shadow p-4 flex flex-col">
      <div class="flex justify-between items-center mb-4 border-b pb-2">
        <h2 class="text-lg font-bold text-gray-800">{{ t('knowledge.sidebar_title') }}</h2>
        <el-button type="primary" size="small" @click="showCreateDialog = true">{{ t('knowledge.btn_new_kb') }}</el-button>
      </div>
      
      <div class="flex-1 overflow-y-auto space-y-2">
        <div 
          v-for="kb in kbList" 
          :key="kb.id"
          class="p-3 rounded cursor-pointer transition-all border border-transparent"
          :class="currentKb?.id === kb.id ? 'bg-blue-50 border-blue-200 shadow-sm' : 'hover:bg-gray-50'"
          @click="selectKb(kb)"
        >
          <div class="font-medium text-gray-800">{{ kb.name }}</div>
          <div class="text-xs text-gray-500 mt-1 truncate">{{ kb.description || t('knowledge.no_desc') }}</div>
          <div class="text-xs text-gray-400 mt-2 flex justify-between items-center">
            <span>{{ t('knowledge.doc_count', { count: kb.doc_count }) }}</span>
            <el-button type="danger" link size="small" @click.stop="handleDeleteKb(kb)">{{ t('common.delete') }}</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Content -->
    <div class="flex-1 min-w-0 bg-white rounded-lg shadow p-4 flex flex-col" v-if="currentKb">
      <div class="flex justify-between items-center mb-4 border-b pb-2">
        <div>
          <h2 class="text-xl font-bold text-gray-800">{{ currentKb.name }}</h2>
          <p class="text-sm text-gray-500">{{ currentKb.description }}</p>
        </div>
        <el-radio-group v-model="activeTab" size="small">
          <el-radio-button label="docs">{{ t('knowledge.tab_docs') }}</el-radio-button>
          <el-radio-button label="search">{{ t('knowledge.tab_search') }}</el-radio-button>
        </el-radio-group>
      </div>

      <!-- Docs Tab -->
      <div v-if="activeTab === 'docs'" class="flex-1 flex flex-col">
        <div class="mb-4 flex justify-between items-center">
          <div class="text-sm text-gray-500">
            {{ t('knowledge.support_formats') }}
          </div>
          <el-upload
            action="#"
            :http-request="handleUpload"
            :show-file-list="false"
            accept=".md,.txt,.pdf,.docx"
            :disabled="uploading"
          >
            <el-button type="primary" :loading="uploading">
              {{ uploading ? t('knowledge.btn_uploading') : t('knowledge.btn_upload_doc') }}
            </el-button>
          </el-upload>
        </div>

        <el-table :data="docList" v-loading="loadingDocs" style="width: 100%" height="100%">
          <el-table-column prop="filename" :label="t('knowledge.col_filename')" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <el-link type="primary" :underline="false" @click="openDocDetail(row)">{{ row.filename }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="status" :label="t('knowledge.col_status')" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small" effect="light">
                {{ formatDocStatus(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('knowledge.col_failed_reason')" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.status === 'failed'">{{ row.error_msg || '-' }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="chunk_count" :label="t('knowledge.col_chunk_count')" width="100" align="center" />
          <el-table-column prop="created_at" :label="t('knowledge.col_uploaded_at')" width="180">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column :label="t('knowledge.col_actions')" width="100" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'failed'" type="primary" link size="small" @click="handleRetryDoc(row)">{{ t('knowledge.btn_retry') }}</el-button>
              <el-button type="danger" link size="small" @click="handleDeleteDoc(row)">{{ t('common.delete') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <div class="mt-2 text-right">
             <el-button size="small" @click="loadDocuments">{{ t('knowledge.btn_refresh_list') }}</el-button>
        </div>
      </div>

      <!-- Search Tab -->
      <div v-if="activeTab === 'search'" class="flex-1 flex flex-col min-h-0">
        <div class="flex gap-2 mb-4">
          <el-input 
            v-model="searchQuery" 
            :placeholder="t('knowledge.search_placeholder')" 
            @keyup.enter="handleSearch" 
            clearable
          />
          <el-button type="primary" @click="handleSearch" :loading="searching">{{ t('common.search') }}</el-button>
        </div>

        <div class="overflow-y-auto space-y-4 p-2 h-[calc(100vh-210px)]">
          <div v-for="(res, idx) in searchResults" :key="idx" class="border rounded-lg p-4 bg-gray-50 hover:bg-gray-100 transition-colors">
            <div class="flex justify-between text-xs text-gray-500 mb-2 pb-2 border-b border-gray-200">
              <span class="font-mono bg-gray-200 px-1 rounded">{{ t('knowledge.score') }}: {{ res.score.toFixed(4) }}</span>
              <span class="truncate ml-2" :title="res.metadata.doc_id">{{ t('knowledge.source') }}: ...{{ res.metadata.doc_id.slice(-8) }} ({{ t('knowledge.chunk') }} {{ res.metadata.chunk_index }})</span>
            </div>
            <div class="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{{ res.text }}</div>
          </div>
          <el-empty v-if="!searchResults.length && !searching" :description="t('knowledge.search_empty')" />
        </div>
      </div>
    </div>
    
    <div v-else class="flex-1 bg-white rounded-lg shadow p-4 flex flex-col items-center justify-center text-gray-400">
      <div class="text-6xl mb-4">📚</div>
      <div>{{ t('knowledge.no_kb_selected') }}</div>
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreateDialog" :title="t('knowledge.create_dialog_title')" width="500px" align-center>
      <el-form :model="createForm" label-width="60px">
        <el-form-item :label="t('knowledge.form_name')" required>
          <el-input v-model="createForm.name" :placeholder="t('knowledge.form_name_placeholder')" />
        </el-form-item>
        <el-form-item :label="t('knowledge.form_desc')">
          <el-input v-model="createForm.description" type="textarea" :rows="3" :placeholder="t('knowledge.form_desc_placeholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ t('knowledge.btn_cancel') }}</el-button>
        <el-button type="primary" @click="handleCreateKb">{{ t('knowledge.btn_confirm') }}</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="showDocDetailDrawer" :title="docDetailTitle" size="80%" @closed="handleDocDetailDrawerClosed">
      <div class="h-full flex gap-4">
        <div class="w-96 flex-shrink-0 flex flex-col">
          <div class="border rounded-lg p-4 mb-4">
            <div class="text-sm text-gray-500">{{ t('knowledge.kb_label') }}</div>
            <div class="text-lg font-semibold text-gray-800 mt-1">{{ currentKb?.name }}</div>
            <div class="text-xs text-gray-500 mt-1">{{ currentKb?.description || t('knowledge.no_desc') }}</div>
            <div class="mt-3 flex items-center gap-2">
              <el-tag v-if="detailDoc" :type="getStatusType(detailDoc.status)" size="small" effect="light">
                {{ formatDocStatus(detailDoc.status) }}
              </el-tag>
              <span v-if="detailDoc" class="text-xs text-gray-500">{{ new Date(detailDoc.created_at).toLocaleString() }}</span>
            </div>
            <div v-if="detailDoc" class="text-xs text-gray-500 mt-2">{{ t('knowledge.chunk_count') }}：{{ detailDoc.chunk_count }}</div>
            <div v-if="detailDoc?.status === 'failed'" class="text-xs text-red-600 mt-2 break-all">{{ detailDoc.error_msg || '-' }}</div>
            <div class="mt-3 flex justify-end">
              <el-button size="small" @click="refreshDocDetail(true)">{{ t('knowledge.btn_refresh') }}</el-button>
            </div>
          </div>

          <div class="flex justify-between items-center mb-2">
            <div class="font-medium text-gray-800">{{ t('knowledge.events_title') }}</div>
            <div class="text-xs text-gray-500">{{ t('knowledge.items_count', { count: detailEvents.length }) }}</div>
          </div>
          <div class="flex-1 overflow-y-auto border rounded-lg p-3">
            <el-timeline>
              <el-timeline-item v-for="ev in detailEvents" :key="ev.id" :timestamp="new Date(ev.created_at).toLocaleString()" placement="top">
                <div class="text-sm text-gray-800">{{ ev.message }}</div>
                <div v-if="ev.data" class="text-xs text-gray-500 mt-1 font-mono break-all">{{ formatEventData(ev.data) }}</div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-if="!detailEvents.length" :description="t('knowledge.no_events')" />
          </div>
        </div>

        <div class="flex-1 flex flex-col">
          <div class="flex justify-between items-center mb-2">
            <div class="font-medium text-gray-800">{{ t('knowledge.chunks_title') }}</div>
            <div class="text-xs text-gray-500">{{ t('knowledge.items_count', { count: detailChunks.length }) }}</div>
          </div>
          <el-table :data="detailChunks" v-loading="loadingDocChunks" height="100%" style="width: 100%">
            <el-table-column prop="chunk_index" :label="t('knowledge.col_chunk_index')" width="70" />
            <el-table-column prop="text_len" :label="t('knowledge.col_text_len')" width="90" />
            <el-table-column prop="text" :label="t('knowledge.col_text')" min-width="420" show-overflow-tooltip />
          </el-table>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as API from '@/api/knowledge'
import type { UploadRequestOptions } from 'element-plus'

const { t } = useI18n()

const kbList = ref<API.KnowledgeBase[]>([])
const currentKb = ref<API.KnowledgeBase | null>(null)
const docList = ref<API.Document[]>([])
const loadingDocs = ref(false)
const showCreateDialog = ref(false)
const activeTab = ref('docs')
const uploading = ref(false)

const createForm = ref({
  name: '',
  description: ''
})

const searchQuery = ref('')
const searchResults = ref<API.SearchResult[]>([])
const searching = ref(false)

const DOC_DETAIL_POLL_INTERVAL_MS = 6000
const DOC_CHUNKS_LIMIT = 5000

const showDocDetailDrawer = ref(false)
const detailDoc = ref<API.Document | null>(null)
const detailEvents = ref<API.DocumentEvent[]>([])
const detailChunks = ref<API.DocumentChunk[]>([])
const loadingDocDetail = ref(false)
const loadingDocChunks = ref(false)
let docDetailPollTimer: ReturnType<typeof setInterval> | null = null

const docDetailTitle = computed(() => {
  if (!detailDoc.value) return t('knowledge.doc_detail_title')
  return detailDoc.value.filename
})

// Initialization
onMounted(() => {
  loadKbs()
})

onBeforeUnmount(() => {
  stopDocDetailPolling()
})

async function loadKbs() {
  try {
    const res = await API.getKnowledgeBases()
    kbList.value = res.data
  } catch (error) {
    console.error(error)
  }
}

async function handleCreateKb() {
  if (!createForm.value.name) return
  try {
    await API.createKnowledgeBase(createForm.value)
    showCreateDialog.value = false
    createForm.value = { name: '', description: '' }
    loadKbs()
    ElMessage.success(t('knowledge.toast_create_success'))
  } catch (error) {
    ElMessage.error(t('knowledge.toast_create_failed'))
  }
}

async function handleDeleteKb(kb: API.KnowledgeBase) {
  try {
    await ElMessageBox.confirm(t('knowledge.confirm_delete_kb', { name: kb.name }), t('knowledge.warning_title'), {
      type: 'warning',
      confirmButtonText: t('common.delete'),
      confirmButtonClass: 'el-button--danger'
    })
    await API.deleteKnowledgeBase(kb.id)
    if (currentKb.value?.id === kb.id) {
      currentKb.value = null
    }
    loadKbs()
    ElMessage.success(t('knowledge.toast_delete_kb_success'))
  } catch (e) {
    // cancelled
  }
}

async function selectKb(kb: API.KnowledgeBase) {
  currentKb.value = kb
  activeTab.value = 'docs'
  searchResults.value = []
  searchQuery.value = ''
  loadDocuments()
}

async function loadDocuments() {
  if (!currentKb.value) return
  loadingDocs.value = true
  try {
    const res = await API.getDocuments(currentKb.value.id)
    docList.value = res.data
  } finally {
    loadingDocs.value = false
  }
}

async function handleUpload(options: UploadRequestOptions) {
  if (!currentKb.value) return
  const formData = new FormData()
  formData.append('file', options.file)
  
  uploading.value = true
  try {
    await API.uploadDocument(currentKb.value.id, formData)
    ElMessage.success(t('knowledge.toast_upload_success'))
    // Refresh list periodically? For now just refresh once after a short delay
    setTimeout(loadDocuments, 1000)
  } catch (error) {
    ElMessage.error(t('knowledge.toast_upload_failed'))
  } finally {
    uploading.value = false
  }
}

async function handleDeleteDoc(doc: API.Document) {
  try {
    await API.deleteDocument(doc.id)
    loadDocuments()
    ElMessage.success(t('knowledge.toast_delete_doc_success'))
  } catch (error) {
    ElMessage.error(t('knowledge.toast_delete_doc_failed'))
  }
}

async function handleRetryDoc(doc: API.Document) {
  try {
    await API.retryDocument(doc.id)
    ElMessage.success(t('knowledge.toast_retry_submitted'))
    loadDocuments()
  } catch (error) {
    ElMessage.error(t('knowledge.toast_retry_failed'))
  }
}

function openDocDetail(doc: API.Document) {
  detailDoc.value = doc
  detailEvents.value = []
  detailChunks.value = []
  showDocDetailDrawer.value = true
  refreshDocDetail(true)
  startDocDetailPolling()
}

function handleDocDetailDrawerClosed() {
  stopDocDetailPolling()
  detailDoc.value = null
  detailEvents.value = []
  detailChunks.value = []
}

function startDocDetailPolling() {
  stopDocDetailPolling()
  docDetailPollTimer = setInterval(() => {
    const st = detailDoc.value?.status
    if (!showDocDetailDrawer.value || !detailDoc.value) return
    if (st === 'completed' || st === 'failed') {
      stopDocDetailPolling()
      return
    }
    refreshDocDetail(false, true)
  }, DOC_DETAIL_POLL_INTERVAL_MS)
}

function stopDocDetailPolling() {
  if (docDetailPollTimer) {
    clearInterval(docDetailPollTimer)
    docDetailPollTimer = null
  }
}

async function refreshDocDetail(forceChunks: boolean, silent: boolean = false) {
  if (!detailDoc.value) return
  if (!silent) loadingDocDetail.value = true
  try {
    const eventsRes = await API.getDocumentEvents(detailDoc.value.id)
    detailEvents.value = eventsRes.data

    const docRes = await API.getDocument(detailDoc.value.id)
    detailDoc.value = docRes.data
    const idx = docList.value.findIndex((d) => d.id === detailDoc.value?.id)
    if (idx >= 0) {
      docList.value[idx] = detailDoc.value
    }

    const shouldLoadChunks =
      forceChunks || (detailDoc.value?.chunk_count > 0 && detailChunks.value.length === 0)
    if (shouldLoadChunks) {
      loadingDocChunks.value = true
      try {
        const chunksRes = await API.getDocumentChunks(detailDoc.value.id, DOC_CHUNKS_LIMIT)
        detailChunks.value = chunksRes.data.items
      } finally {
        loadingDocChunks.value = false
      }
    }
  } finally {
    if (!silent) loadingDocDetail.value = false
  }
}

function formatEventData(data: Record<string, any>) {
  try {
    return JSON.stringify(data)
  } catch {
    return String(data)
  }
}

async function handleSearch() {
  if (!currentKb.value || !searchQuery.value) return
  searching.value = true
  try {
    const res = await API.searchKnowledgeBase(currentKb.value.id, searchQuery.value)
    searchResults.value = res.data
  } catch (error) {
    ElMessage.error(t('knowledge.toast_search_failed'))
  } finally {
    searching.value = false
  }
}

function getStatusType(status: string) {
  switch (status) {
    case 'completed': return 'success'
    case 'indexing': return 'warning'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

function formatDocStatus(status: API.Document['status'] | string) {
  const key = `knowledge.status_${status}`
  const translated = t(key)
  return translated === key ? status : translated
}
</script>
