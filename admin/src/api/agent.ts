import api from './axios'

export interface AgentPlugin {
  id: string
  name: string
  name_zh?: string
  description: string
  type: 'system' | 'example' | 'application'
}

export interface AgentConfigResponse {
  content: string
}

export interface ConfigUpdateRequest {
  content: string
}

export const getPlugins = () => {
  return api.get<AgentPlugin[]>('/api/v1/plugins')
}

export const getAgentConfig = (agentId: string) => {
  return api.get<AgentConfigResponse>(`/api/v1/paas/agents/${agentId}/config`)
}

export const updateAgentConfig = (agentId: string, content: string) => {
  return api.post(`/api/v1/paas/agents/${agentId}/config`, { content })
}
