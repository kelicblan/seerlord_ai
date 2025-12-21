<script setup lang="ts">
import { onMounted, ref, watch, nextTick, computed } from 'vue'
import { useAgent } from '@/composables/useAgent'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import mermaid from 'mermaid'

import { Loader2, Sparkles, Paperclip, Mic, ArrowUp, History, MessageSquarePlus, Briefcase, GitBranch } from 'lucide-vue-next'
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
  mermaid.initialize({ startOnLoad: false, theme: 'default' })
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

const handleSend = async () => {
  if (!userInput.value.trim() || isThinking.value) return
  const text = userInput.value
  userInput.value = ''
  await sendMessage(text, locale.value)
}
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-2 h-[calc(100vh-60px)]">
    <!-- Left Panel: Chat -->
    <ElCard shadow="never" class="flex flex-col h-full overflow-hidden">
      <template #header>
        <div class="text-base flex justify-between items-center text-primary">
          <span>{{ t('common.chat') }}</span>
          <div class="flex gap-2">
            <ElSelect
              v-model="selectedPlugin"
              class="w-[220px]"
              :placeholder="t('common.select_agent')"
              filterable
              clearable
            >
              <ElOption
                v-for="plugin in applicationPlugins"
                :key="plugin.id"
                :label="getPluginName(plugin)"
                :value="plugin.id"
              />
            </ElSelect>
            
            <ElButton
              type="primary"
              text
              circle
              class="h-8 w-8"
              @click="router.push('/history')"
              :title="t('common.history')"
            >
              <History class="h-4 w-4" />
            </ElButton>

            <ElButton
              type="primary"
              text
              circle
              class="h-8 w-8"
              @click="handleNewSession"
              :title="t('common.new_session')"
            >
              <MessageSquarePlus class="h-4 w-4" />
            </ElButton>
          </div>
        </div>
      </template>
      
      <div class="flex-1 p-0 flex flex-col overflow-hidden min-h-0">
        <div ref="messagesContainer" class="min-h-0 h-[calc(100vh-250px)] overflow-auto p-4">
          <div class="space-y-4">
            <div
              v-for="(msg, index) in messages"
              :key="index"
              class="flex flex-col"
              :class="msg.role === 'user' ? 'items-end' : 'items-start'"
            >
              <div
                class="max-w-[85%] rounded-lg px-4 py-2"
                :class="msg.role === 'user'
                  ? 'bg-gray text-foreground rounded-br-none'
                  : 'bg-muted text-foreground rounded-bl-none'"
              >
                <div class="prose dark:prose-invert max-w-none">
                  <ThoughtProcess
                    v-if="msg.role === 'ai' && ((msg.thoughts?.length ?? 0) > 0 || (isThinking && index === messages.length - 1))"
                    :steps="msg.thoughts || []"
                    :isFinished="!isThinking || index !== messages.length - 1"
                  />

                  <span v-if="!msg.content && ((msg.thoughts?.length ?? 0) === 0)">{{ t('common.waiting_content') }}</span>
                  <MarkdownRender
                    v-else-if="msg.content"
                    :content="msg.content"
                  />
                </div>
              </div>
              <span class="text-xs text-muted-foreground mt-1">
                {{ new Date(msg.timestamp).toLocaleTimeString() }}
              </span>
            </div>
            <div v-if="isThinking && messages[messages.length-1]?.role !== 'ai'" class="flex items-start">
              <div class="bg-muted text-foreground rounded-lg rounded-bl-none px-4 py-2 flex items-center gap-2">
                <Loader2 class="h-4 w-4 animate-spin" />
                <span>{{ t('common.thinking') }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-background border-t p-2 shrink-0 sticky bottom-0">
          <form @submit.prevent="handleSend" class="relative rounded-xl border bg-background focus-within:ring-1 focus-within:ring-ring transition-all">
            <textarea 
              v-model="userInput" 
              :placeholder="t('common.input_placeholder')" 
              :disabled="isThinking"
              class="min-h-[60px] w-full resize-none border-0 bg-transparent px-4 py-3 text-sm focus-visible:ring-0 shadow-none placeholder:text-muted-foreground focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
              @keydown.enter.exact.prevent="handleSend"
            ></textarea>
            
            <div class="flex items-center justify-between p-2">
              <!-- Left: Optimize -->
              <ElButton type="primary" text circle class="h-8 w-8 text-muted-foreground hover:text-foreground">
                <Sparkles class="h-4 w-4" />
              </ElButton>
              
              <!-- Right: Tools + Send -->
              <div class="flex items-center gap-2">
                 <ElButton type="primary" text circle class="h-8 w-8 text-muted-foreground hover:text-foreground">
                   <Paperclip class="h-4 w-4" />
                 </ElButton>
                 <ElButton type="primary" text circle class="h-8 w-8 text-muted-foreground hover:text-foreground">
                   <Mic class="h-4 w-4" />
                 </ElButton>
                 <ElButton type="primary" native-type="submit" :disabled="isThinking || !userInput.trim()" class="h-8 rounded-md px-3" size="small">
                   {{ t('common.send') }} <ArrowUp class="ml-2 h-4 w-4" />
                 </ElButton>
              </div>
            </div>
          </form>
        </div>
      </div>
    </ElCard>

    <!-- Right Panel: Dashboard -->
      <div class="flex flex-col gap-2 h-full overflow-hidden">
      <!-- Metrics -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="rounded-md border bg-card p-2">
          <ElStatistic
            :title="t('common.status')"
            :value="metrics.duration"
            :formatter="formatStatusStatistic"
            :value-style="{ color: 'var(--el-color-primary)', fontWeight: 700 }"
          />
        </div>
        <div class="rounded-md border bg-card p-2">
          <ElStatistic :title="t('common.duration')" :value="metrics.duration" :value-style="{ fontWeight: 700 }">
            <template #suffix>s</template>
          </ElStatistic>
        </div>
        <div class="rounded-md border bg-card p-2">
          <ElStatistic :title="t('common.total_tokens')" :value="metrics.totalTokens" :value-style="{ fontWeight: 700 }" />
        </div>
        <div class="rounded-md border bg-card p-2">
          <ElStatistic
            :title="t('common.tokens_in_out')"
            :value="metrics.totalTokens"
            :formatter="formatTokensInOutStatistic"
            :value-style="{ fontWeight: 700 }"
          />
        </div>
        
        <!-- MCP Metrics -->
        <ElCard shadow="never" class="col-span-2 md:col-span-4">
          <div class="p-4">
            <div class="text-xs text-muted-foreground mb-1">{{ t('common.mcp_services') }}</div>
            <div v-if="!mcpStatus" class="text-sm">{{ t('common.loading') }}</div>
            <div v-else>
               <div class="text-sm font-bold text-blue-600 mb-2">
                 {{ t('common.total_servers') }}: {{ mcpStatus.total_servers }} | {{ t('common.total_tools') }}: {{ mcpStatus.total_tools }}
               </div>
               <div class="flex flex-wrap gap-2">
                 <ElTag
                   v-for="server in mcpStatus.servers"
                   :key="server.name"
                   :type="server.status === 'connected' ? 'success' : 'danger'"
                   effect="light"
                 >
                   <div class="flex items-center gap-2">
                     <div class="w-2 h-2 rounded-full" :class="server.status === 'connected' ? 'bg-green-500' : 'bg-red-500'"></div>
                     <span>{{ server.name }}</span>
                     <span class="text-xs opacity-80">({{ server.tool_count }})</span>
                   </div>
                 </ElTag>
               </div>
            </div>
          </div>
        </ElCard>
      </div>

      <!-- Tabs: Logs & Graph -->
      <ElTabs v-model="activeRightTab" type="border-card" class="w-full shadow-sm">
        <ElTabPane name="logs" :label="t('common.execution_log')">
          <div class="h-[calc(100vh-345px)] overflow-auto">
            <div class="p-2 font-mono text-xs space-y-1">
              <div v-for="(log, i) in logs" :key="i" class="border-b border-border/50 pb-1 last:border-0">
                <span class="text-muted-foreground">[{{ log.time }}]</span>
                <ElTag type="info" effect="plain" class="mx-2">
                  {{ log.type }}
                </ElTag>
                <span class="text-foreground">{{ log.detail }}</span>
              </div>
              <div v-if="logs.length === 0" class="text-muted-foreground p-2">{{ t('common.waiting_execution') }}</div>
            </div>
          </div>
        </ElTabPane>
        <ElTabPane name="graph" :label="t('common.workflow_graph')">
          <div class="h-[calc(100vh-345px)] overflow-auto">
            <div ref="graphContainer" class="flex justify-center items-center min-h-[200px] p-4">
              {{ t('common.select_agent_graph') }}
            </div>
          </div>
        </ElTabPane>
        <ElTabPane name="context" :label="t('common.context')">
          <div class="h-[calc(100vh-345px)] overflow-auto">
            <div v-if="llmContexts.length === 0" class="text-muted-foreground">{{ t('common.no_data') }}</div>
            <div v-for="ctx in llmContexts" :key="ctx.id" class="mb-4 p-3 bg-card">
              <div class="flex justify-between items-center mb-2 border-b pb-2">
                <div class="font-bold text-sm">{{ ctx.model }}</div>
                <div class="text-xs text-muted-foreground">{{ ctx.timestamp }}</div>
              </div>
              <div class="space-y-2">
                <div v-for="(msg, idx) in ctx.prompts" :key="idx" class="text-sm">
                  <div class="font-semibold text-xs uppercase text-muted-foreground mb-1">{{ msg.type || msg.role }}</div>
                  <div class="whitespace-pre-wrap bg-muted/50 p-2 rounded text-xs font-mono break-words">{{ msg.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </ElTabPane>

        <!-- New Skills Tab -->
        <ElTabPane name="skills" :label="t('common.skills_tab')">
            <template #label>
                <span class="flex items-center gap-2">
                    <Briefcase class="w-4 h-4" />
                    {{ t('common.skills_tab') }}
                    <span v-if="skillExecutionData.evolutions.length > 0" class="flex h-2 w-2 rounded-full bg-red-500"></span>
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
                    
                    <div v-if="skillExecutionData.usedSkills.length === 0" class="text-gray-400 text-sm py-4 text-center italic">
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
  </div>
</template>

<style scoped>
/* Ensure mermaid graph is visible */
:deep(svg) {
  max-width: 100%;
  height: auto;
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
.bg-gray{
  background-color: #ebebeb;
}
</style>
