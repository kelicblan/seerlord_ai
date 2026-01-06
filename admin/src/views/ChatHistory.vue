<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Search } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import api from '@/api/axios'

interface ChatSession {
  id: string
  thread_id: string
  agent_name: string
  summary: string
  message_count: number
  created_at: string
  updated_at: string
}

const router = useRouter()
const { t } = useI18n()

const sessions = ref<ChatSession[]>([])
const loading = ref(false)
const searchQuery = ref('')

// Pagination state
const currentPage = ref(1)
const pageSize = ref(10)
const totalSessions = ref(0)

// Mock fetch function
const fetchHistory = async () => {
  loading.value = true
  try {
    const skip = (currentPage.value - 1) * pageSize.value
    const response = await api.get('/api/v1/chat/sessions', {
        params: {
            skip,
            limit: pageSize.value
        }
    })
    
    const data = response.data
    // Backend doesn't return total count yet, so pagination might be limited to "next page" style
    // Or we assume if we got pageSize items, there might be more.
    // For now, let's just show what we got.
    // To support real pagination, backend needs to return total count.
    
    sessions.value = data.map((s: any) => ({
        id: s.id,
        thread_id: s.id,
        agent_name: s.agent_id || 'Agent',
        summary: s.title || 'No Title',
        message_count: 0, // Not available yet
        created_at: new Date(s.created_at).toLocaleString(),
        updated_at: new Date(s.updated_at).toLocaleString()
    }))

    // Filter by search (Frontend filtering for now as backend doesn't support search yet)
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      sessions.value = sessions.value.filter(s => 
        s.thread_id.toLowerCase().includes(q) || 
        s.summary.toLowerCase().includes(q) ||
        s.agent_name.toLowerCase().includes(q)
      )
    }

    // Since we are paginating on backend, totalSessions is unknown. 
    // We can set it to a large number if full page, or just hide pagination if we don't have count.
    // Let's set it to at least current page * pageSize if we have data.
    if (sessions.value.length === pageSize.value) {
        totalSessions.value = (currentPage.value + 1) * pageSize.value
    } else {
        totalSessions.value = (currentPage.value - 1) * pageSize.value + sessions.value.length
    }
    
  } catch (error) {
    console.error('Failed to fetch history:', error)
    ElMessage.error(t('chat_history.toast_error_load'))
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchHistory()
}

const handleRowClick = (row: ChatSession) => {
  router.push({ name: 'home', query: { thread_id: row.thread_id } })
}

onMounted(() => {
  fetchHistory()
})
</script>

<template>
  <div class="h-full w-full space-y-4">
    <!-- Top Bar -->
    <div class="flex justify-between items-center">
      <h2 class="text-lg font-medium">{{ t('common.nav_history') }}</h2>
      
      <div class="flex items-center gap-2">
        <div class="relative w-[300px]">
          <ElInput
            v-model="searchQuery"
            :placeholder="t('common.search') + '...'"
            @keyup.enter="handleSearch"
            clearable
          >
            <template #prefix>
              <Search class="h-4 w-4 text-muted-foreground" />
            </template>
          </ElInput>
        </div>
        <ElButton type="primary" @click="handleSearch">
          {{ t('common.search') }}
        </ElButton>
      </div>
    </div>

    <ElCard shadow="never" class="!border-0">
      <div class="mt-4">
        <ElTable
          :data="sessions"
          style="width: 100%"
          @row-click="handleRowClick"
          class="cursor-pointer"
          v-loading="loading"
        >
          <ElTableColumn prop="thread_id" :label="t('chat_history.header_thread_id')" width="220" />
          <ElTableColumn prop="agent_name" :label="t('common.nav_agent')" width="180">
             <template #default="{ row }">
               <ElTag>{{ row.agent_name }}</ElTag>
             </template>
          </ElTableColumn>
          <ElTableColumn prop="summary" :label="t('chat_history.header_summary')" show-overflow-tooltip />
          <ElTableColumn prop="message_count" :label="t('chat_history.header_msgs')" width="100" align="center" />
          <ElTableColumn prop="updated_at" :label="t('chat_history.header_time')" width="180" class-name="text-muted-foreground" />
          <ElTableColumn width="100" align="right">
             <template #default>
               <ElButton link type="primary">{{ t('chat_history.btn_view') }}</ElButton>
             </template>
          </ElTableColumn>
        </ElTable>
        
        <div class="flex justify-end mt-4">
           <ElPagination
            background
            layout="prev, pager, next"
            :total="totalSessions"
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            @current-change="fetchHistory"
          />
        </div>
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
