import api from './axios'

export interface AgentArtifact {
  id: string
  tenant_id: string
  user_id?: string
  agent_id: string
  execution_id?: string
  type: 'file' | 'content'
  value: string
  title?: string
  description?: string
  total_tokens?: number
  created_at: string
}

export interface ArtifactPreview {
  type: 'file' | 'content'
  content?: string
  filename?: string
  download_url?: string
}

export interface ArtifactListResponse {
  items: AgentArtifact[]
  total: number
}

export const listArtifacts = (page: number = 1, pageSize: number = 12, agentId?: string) => {
  return api.get<ArtifactListResponse>('/api/v1/artifact/list', { 
    params: { 
      page, 
      page_size: pageSize, 
      agent_id: agentId 
    } 
  })
}

export const getArtifact = (id: string) => {
  return api.get<AgentArtifact>(`/api/v1/artifact/${id}`)
}

export const previewArtifact = (id: string) => {
  return api.get<ArtifactPreview>(`/api/v1/artifact/${id}/preview`)
}
