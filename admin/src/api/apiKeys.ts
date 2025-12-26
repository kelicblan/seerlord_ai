import api from './axios'

export interface ApiKey {
  id: string
  user_id: number
  key: string
  name: string
  is_active: boolean
  created_at: string
}

export interface ApiKeyCreate {
  name: string
  is_active?: boolean
}

export interface ApiKeyUpdate {
  name?: string
  is_active?: boolean
}

export const getApiKeys = () => {
  return api.get<ApiKey[]>('/api/v1/api-keys/')
}

export const createApiKey = (data: ApiKeyCreate) => {
  return api.post<ApiKey>('/api/v1/api-keys/', data)
}

export const deleteApiKey = (id: string) => {
  return api.delete(`/api/v1/api-keys/${id}`)
}

export const updateApiKey = (id: string, data: ApiKeyUpdate) => {
  return api.put<ApiKey>(`/api/v1/api-keys/${id}`, data)
}
