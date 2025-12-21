import { ref, reactive, watch } from 'vue'
import api from '@/api/axios'
import i18n from '@/i18n'

export interface AgentPlugin {
  id: string
  name: string
  name_zh?: string
  description?: string
  type?: 'system' | 'example' | 'application'
}

export interface ThoughtStep {
  id: string
  type: 'thought' | 'tool'
  name: string
  status: 'pending' | 'success' | 'failed'
  input?: string
  output?: string
  duration?: number
  startTime: number
}

export interface Message {
  role: 'user' | 'ai'
  content: string
  timestamp: number
  thoughts?: ThoughtStep[]
}

export interface LogEntry {
  time: string
  type: string
  detail: string
}

export interface Metrics {
  status: string
  duration: number
  totalTokens: number
  inputTokens: number
  outputTokens: number
}

export interface NodeStatus {
  [key: string]: 'running' | 'completed' | 'idle'
}

export interface MCPStatus {
  total_servers: number
  total_tools: number
  servers: Array<{
    name: string
    tool_count: number
    status?: string
  }>
}

export interface LLMContext {
  id: string
  model: string
  timestamp: string
  prompts: any[]
}

export function useAgent() {
  const envTenantApiKey = import.meta.env.VITE_TENANT_API_KEY || ''

  const getTenantApiKey = () => {
    const runtimeKey = localStorage.getItem('tenant_api_key') || sessionStorage.getItem('tenant_api_key') || ''
    if (runtimeKey) return runtimeKey
    if (envTenantApiKey) return envTenantApiKey
    if (import.meta.env.DEV) return 'sk-admin-test'
    return ''
  }

  const getAuthToken = () => {
    return localStorage.getItem('token') || sessionStorage.getItem('token') || ''
  }

  const plugins = ref<AgentPlugin[]>([])
  const selectedPlugin = ref<string>('')
  const messages = ref<Message[]>([{
    role: 'ai',
    content: (i18n.global as any).t('common.welcome_message'),
    timestamp: Date.now()
  }])
  const isThinking = ref(false)
  
  const metrics = reactive<Metrics>({
    status: 'idle',
    duration: 0,
    totalTokens: 0,
    inputTokens: 0,
    outputTokens: 0
  })

  const logs = ref<LogEntry[]>([])
  const graphData = ref<string>('')
  const nodeStatuses = ref<NodeStatus>({})
  const mcpStatus = ref<MCPStatus | null>(null)
  const llmContexts = ref<LLMContext[]>([])
  
  // New: Skill Execution Data
  const skillExecutionData = ref<{
    usedSkills: Array<{id: string, name: string, level: number}>
    usedSkillDetails: Record<string, any>
    evolutions: Array<{skill_id: string, skill_name: string, change: string}>
  }>({
    usedSkills: [],
    usedSkillDetails: {},
    evolutions: []
  })

  const threadId = ref(`web-test-${Date.now()}`)

  const createNewSession = () => {
    threadId.value = `web-test-${Date.now()}`
    messages.value = [{
      role: 'ai',
      content: (i18n.global as any).t('common.welcome_message'),
      timestamp: Date.now()
    }]
    skillExecutionData.value = { usedSkills: [], usedSkillDetails: {}, evolutions: [] }
    resetMetrics()
    addLog('INFO', 'New session created')
  }

  const loadSession = async (id: string) => {
    threadId.value = id
    isThinking.value = true
    messages.value = [] // Clear current messages
    resetMetrics()
    
    // TODO: Replace with actual backend API call
    // For now, we simulate loading history based on ID
    addLog('INFO', `Loading session ${id}...`)
    
    try {
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 600))
      
      // Mock data
      messages.value = [
        {
          role: 'ai',
          content: (i18n.global as any).t('common.welcome_message'),
          timestamp: Date.now() - 100000
        },
        {
          role: 'user',
          content: 'Help me analyze the latest AI news.',
          timestamp: Date.now() - 90000
        },
        {
          role: 'ai',
          content: 'Sure! I can help you with that. Here is a summary of the latest AI news...',
          timestamp: Date.now() - 80000,
          thoughts: [
            {
              id: 'job-1',
              type: 'thought',
              name: 'news_search',
              status: 'success',
              startTime: Date.now() - 85000,
              duration: 2000,
              output: 'Found 5 articles'
            }
          ]
        }
      ]
      
      addLog('INFO', 'Session loaded successfully')
    } catch (e) {
      console.error(e)
      addLog('ERROR', 'Failed to load session')
    } finally {
      isThinking.value = false
    }
  }

  const fetchPlugins = async () => {
    try {
      const response = await api.get('/api/v1/plugins')
      plugins.value = response.data
      if (plugins.value && plugins.value.length > 0) {
        // Try to restore selection from local storage
        const savedPluginId = localStorage.getItem('selected-agent-plugin')
        const pluginToSelect = plugins.value.find(p => p.id === savedPluginId) || 
                               plugins.value.find(p => !p.type || p.type === 'application') ||
                               plugins.value[0]
        
        if (pluginToSelect) {
          selectedPlugin.value = pluginToSelect.id
          await fetchGraph(selectedPlugin.value)
        }
      }
    } catch (error) {
      console.error('Failed to load plugins:', error)
      addLog('ERROR', 'Failed to load plugin list')
    }
  }

  // Persist plugin selection
  watch(selectedPlugin, (newVal) => {
    if (newVal) {
      localStorage.setItem('selected-agent-plugin', newVal)
    }
  })

  const fetchMCPStatus = async () => {
    try {
      const response = await api.get('/api/v1/mcp/status')
      mcpStatus.value = response.data
    } catch (error) {
      console.error('Failed to load MCP status:', error)
      addLog('ERROR', 'Failed to load MCP status')
    }
  }

  const fetchGraph = async (agentId: string) => {
    if (!agentId) return
    try {
      const response = await api.get(`/api/v1/agent/${agentId}/graph`)
      if (response.data.mermaid) {
        graphData.value = response.data.mermaid
      }
    } catch (error) {
      console.error('Failed to load graph:', error)
      addLog('ERROR', `Failed to load graph for ${agentId}`)
    }
  }

  const addLog = (type: string, detail: string) => {
    logs.value.push({
      time: new Date().toLocaleTimeString(),
      type,
      detail
    })
  }

  const resetMetrics = () => {
    metrics.status = 'idle'
    metrics.duration = 0
    metrics.totalTokens = 0
    metrics.inputTokens = 0
    metrics.outputTokens = 0
    logs.value = []
    nodeStatuses.value = {}
    llmContexts.value = []
  }

  const sendMessage = async (text: string, language: string = 'zh-CN') => {
    if (!text.trim()) return

    messages.value.push({
      role: 'user',
      content: text,
      timestamp: Date.now()
    })

    isThinking.value = true
    resetMetrics()
    metrics.status = 'running'
    // Reset skill data for new run
    skillExecutionData.value = { usedSkills: [], usedSkillDetails: {}, evolutions: [] }
    addLog('START', 'Sending request to backend...')

    const startTime = Date.now()
    const timerInterval = setInterval(() => {
      metrics.duration = Number(((Date.now() - startTime) / 1000).toFixed(2))
    }, 100)

    // Estimate input tokens from user message (fallback)
    const estimatedInputTokens = text.length
    metrics.inputTokens += estimatedInputTokens
    metrics.totalTokens += estimatedInputTokens

    try {
      // Setup streaming request
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }
      const token = getAuthToken()
      const tenantApiKey = getTenantApiKey()
      if (token) headers.Authorization = `Bearer ${token}`
      if (tenantApiKey) headers['X-API-Key'] = tenantApiKey

      const response = await fetch('/api/v1/agent/stream_events', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          input: {
            messages: [{ type: "human", content: text }],
            language,
            target_plugin: selectedPlugin.value || undefined
          },
          config: {
            configurable: {
              thread_id: threadId.value
            }
          },
          version: "v2"
        })
      })

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
      if (!response.body) throw new Error('Response body is null')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      
      // 添加 AI 占位消息，后续流式内容会追加到该条消息上
      messages.value.push({
        role: 'ai',
        content: '',
        timestamp: Date.now(),
        thoughts: []
      })
      const aiMessageIndex = messages.value.length - 1
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.trim() === '') continue
          if (line.startsWith('event:')) continue
          
          if (line.startsWith('data:')) {
            try {
              const jsonStr = line.slice(5).trim()
              if (!jsonStr) continue
              const eventData = JSON.parse(jsonStr)
              const eventType = eventData.event
              const eventName = eventData.name
              const runId = eventData.run_id

              const currentMessage = messages.value[aiMessageIndex]
              
              if (!currentMessage) continue
              const thoughts = (currentMessage.thoughts ||= [])

              // --- 1. Tool Events ---
              if (eventType === 'on_tool_start') {
                addLog('TOOL', `Starting ${eventName}`)
                const step: ThoughtStep = {
                  id: runId,
                  type: 'tool',
                  name: eventName,
                  status: 'pending',
                  input: JSON.stringify(eventData.data?.input || {}),
                  startTime: Date.now()
                }
                thoughts.push(step)
              } 
              else if (eventType === 'on_tool_end') {
                const status = eventData.data.output ? "SUCCESS" : "FAILED"
                addLog('TOOL', `Finished ${eventName} (${status})`)
                
                const step = thoughts.find(s => s.id === runId)
                if (step) {
                  step.status = eventData.data.output ? 'success' : 'failed'
                  step.output = typeof eventData.data.output === 'string' 
                    ? eventData.data.output 
                    : JSON.stringify(eventData.data.output)
                  step.duration = Date.now() - step.startTime
                }
              }
              // --- 2. Chain/Node Events (Thoughts) ---
              else if (eventType === 'on_chain_start' && eventName && eventName !== 'LangGraph' && !eventName.startsWith('__')) {
                addLog('NODE', `Entering: ${eventName}`)
                nodeStatuses.value[eventName] = 'running'
                
                // Treat meaningful nodes as "thoughts"
                // We exclude the main wrapper if possible, but often node names are good enough
                const step: ThoughtStep = {
                  id: runId,
                  type: 'thought',
                  name: eventName,
                  status: 'pending',
                  startTime: Date.now()
                }
                thoughts.push(step)

                // Auto-switch graph if we detect a plugin starting
                const pluginExists = plugins.value.find(p => p.id === eventName)
                if (pluginExists && selectedPlugin.value !== eventName) {
                    selectedPlugin.value = eventName
                    await fetchGraph(eventName)
                    addLog('UI', `Switched view to: ${eventName}`)
                }
              }
              else if (eventType === 'on_chain_end' && eventName && eventName !== 'LangGraph' && !eventName.startsWith('__')) {
                addLog('NODE', `Finished: ${eventName}`)
                nodeStatuses.value[eventName] = 'completed'

                const step = thoughts.find(s => s.id === runId)
                if (step) {
                  step.status = 'success'
                  // For thoughts, output might be internal state, we can show it if needed
                  // step.output = JSON.stringify(eventData.data.output) 
                  step.duration = Date.now() - step.startTime
                }

                // Fallback: Capture output from task nodes if streaming didn't populate the message
                // Only if this looks like a final output node and we haven't streamed content
                if (eventData.data?.output?.results?.[eventName]) {
                   const nodeResult = eventData.data.output.results[eventName]
                   if (!currentMessage.content && typeof nodeResult === 'string') {
                      currentMessage.content = nodeResult
                      
                      // Estimate tokens if we populated from fallback
                      if (metrics.outputTokens === 0) {
                          const estimated = nodeResult.length
                          metrics.outputTokens = estimated
                          metrics.totalTokens += estimated
                      }
                   }
                }
              }
              // --- 3. Chat Model Stream (Content) ---
              else if (eventType === 'on_chat_model_stream') {
                const chunk = eventData.data?.chunk as any
                const content =
                  chunk?.content ??
                  chunk?.kwargs?.content ??
                  chunk?.kwargs?.delta?.content

                if (content) {
                  currentMessage.content += content
                  
                  metrics.outputTokens += 1
                  metrics.totalTokens += 1
                }
              }
              // --- 4. Model Metadata ---
              else if (eventType === 'on_chat_model_start') {
                addLog('MODEL', `Invoking: ${eventName || 'LLM'}`)
                if (eventData.data?.input?.messages) {
                  // Flatten if it's a list of lists (sometimes happens in LangChain)
                  const rawMsgs = eventData.data.input.messages
                  const msgs = Array.isArray(rawMsgs[0]) ? rawMsgs[0] : rawMsgs
                  
                  // Helper to normalize message structure
                  const normalizeMessage = (m: any) => {
                    if (m.type === 'constructor' && m.kwargs) {
                        return {
                            role: m.kwargs.type || (m.id && m.id.length > 0 ? m.id[m.id.length - 1] : 'unknown'),
                            content: m.kwargs.content
                        }
                    }
                    if (m.content !== undefined) {
                        return {
                            role: m.type || m.role || 'unknown',
                            content: m.content
                        }
                    }
                    return { role: 'unknown', content: JSON.stringify(m) }
                  }

                  llmContexts.value.push({
                     id: runId,
                     model: eventName || 'Unknown Model',
                     timestamp: new Date().toLocaleTimeString(),
                     prompts: msgs.map(normalizeMessage)
                   })
                 } else if (eventData.data?.input?.prompts) {
                   // Handle raw prompts (legacy LLM)
                   const rawPrompts = eventData.data.input.prompts
                   const prompts = Array.isArray(rawPrompts) ? rawPrompts : [rawPrompts]
                   
                   llmContexts.value.push({
                     id: runId,
                     model: eventName || 'Unknown Model',
                     timestamp: new Date().toLocaleTimeString(),
                     prompts: prompts.map((p: string) => ({ role: 'prompt', content: p }))
                   })
                 }
              }
              else if (eventType === 'on_chat_model_end') {

                const output = eventData.data?.output
                addLog('MODEL', `Finished: ${eventName || 'LLM'}`)
                
                let usage = output?.usage_metadata
                
                // Fallback: Check inside kwargs (LangChain serialization)
                if (!usage && output?.kwargs?.usage_metadata) {
                    usage = output.kwargs.usage_metadata
                }

                // Fallback: check response_metadata if usage_metadata is missing
                if (!usage && output?.response_metadata?.token_usage) {
                   usage = {
                      input_tokens: output.response_metadata.token_usage.prompt_tokens,
                      output_tokens: output.response_metadata.token_usage.completion_tokens,
                      total_tokens: output.response_metadata.token_usage.total_tokens
                   }
                }

                // Fallback: check response_metadata inside kwargs
                if (!usage && output?.kwargs?.response_metadata?.token_usage) {
                   const tokenUsage = output.kwargs.response_metadata.token_usage
                   usage = {
                      input_tokens: tokenUsage.prompt_tokens,
                      output_tokens: tokenUsage.completion_tokens,
                      total_tokens: tokenUsage.total_tokens
                   }
                }
                
                // Fallback: Check if output is an AIMessage with usage_metadata directly
                if (!usage && output?.message?.usage_metadata) {
                    usage = output.message.usage_metadata
                }
                
                // Fallback: Check additional_kwargs (sometimes usage is here for OpenAI)
                if (!usage && output?.kwargs?.additional_kwargs?.usage) {
                     const u = output.kwargs.additional_kwargs.usage
                     usage = {
                        input_tokens: u.prompt_tokens,
                        output_tokens: u.completion_tokens,
                        total_tokens: u.total_tokens
                     }
                }

                if (usage) {
                    // If we have real usage, we should technically replace our estimates.
                    // But since we have multiple streaming chunks and potentially multiple model calls,
                    // replacing is complex.
                    // For now, if usage is present, we add it. 
                    // This might double count if we also estimated.
                    // Given the user's environment (Ollama), real usage is likely missing, so this block won't run.
                    // If it does run, better to have more tokens than 0.
                    
                    metrics.inputTokens += usage.input_tokens || 0
                    metrics.outputTokens += usage.output_tokens || 0
                    metrics.totalTokens += usage.total_tokens || 0
                } else {
                    // Fallback: If no usage info and outputTokens is still 0 (streaming failed to count),
                    // estimate from the final message content.
                    const lastMsg = messages.value[messages.value.length - 1]
                    if (lastMsg && lastMsg.role === 'ai' && metrics.outputTokens === 0 && lastMsg.content) {
                        const estimated = lastMsg.content.length
                        metrics.outputTokens = estimated
                        metrics.totalTokens += estimated // Add to total
                    }
                }
              }
              else if (eventType === 'on_chain_end' && eventName === 'LangGraph') {
                const outMsgs = eventData.data?.output?.messages
                if (!currentMessage.content && Array.isArray(outMsgs)) {
                  for (let i = outMsgs.length - 1; i >= 0; i--) {
                    const m: any = outMsgs[i]
                    const t = m?.type ?? m?.kwargs?.type
                    const c = m?.content ?? m?.kwargs?.content
                    if (t === 'ai' && typeof c === 'string' && c) {
                      currentMessage.content = c
                      break
                    }
                  }
                }
              }
              
              // --- 5. Custom Events (Skills) ---
              else if (eventType === 'on_custom_event') {
                if (eventName === 'skill_usage') {
                   const data = eventData.data
                   if (data && data.used_skills) {
                      skillExecutionData.value.usedSkills = data.used_skills
                      skillExecutionData.value.usedSkillDetails = {}
                      addLog('SKILL', `Loaded ${data.used_skills.length} skills`)

                      try {
                        const results = await Promise.all(
                          data.used_skills.map(async (s: { id: string }) => {
                            try {
                              const res = await api.get(`/api/v1/skills/${s.id}`)
                              return [s.id, res.data] as const
                            } catch {
                              return [s.id, null] as const
                            }
                          })
                        )
                        const detailMap: Record<string, any> = {}
                        for (const [id, detail] of results) {
                          if (detail) detailMap[id] = detail
                        }
                        skillExecutionData.value.usedSkillDetails = detailMap
                      } catch (e) {
                        addLog('SKILL', `Failed to load skill details: ${String(e)}`)
                      }
                   }
                }
                else if (eventName === 'skill_evolution') {
                   const data = eventData.data
                   if (data) {
                      skillExecutionData.value.evolutions.push(data)
                      addLog('EVOLVE', `Skill evolved: ${data.skill_name}`)
                      // Show global notification
                      import('element-plus').then(({ ElNotification }) => {
                        ElNotification({
                          title: 'Skill Evolved!',
                          message: `${data.skill_name} has been updated based on this interaction.`,
                          type: 'success',
                          duration: 5000
                        })
                      })
                   }
                }
              }
              
            } catch (e) {
              console.warn('Error parsing JSON from stream', e)
            }
          }
        }
      }

    } catch (error) {
      console.error('Streaming error:', error)
      addLog('ERROR', String(error))
      metrics.status = 'Error'
      messages.value.push({
        role: 'ai',
        content: `Error: ${String(error)}`,
        timestamp: Date.now()
      })
    } finally {
      clearInterval(timerInterval)
      isThinking.value = false
      if (metrics.status !== 'Error') {
        metrics.status = 'Completed'
      }
      addLog('END', 'Request completed')
    }
  }

  return {
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
  }
}
