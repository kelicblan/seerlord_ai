import api from './axios'

export interface LLMModel {
  id: number
  name: string
  provider: string
  base_url?: string
  model_name: string
  api_key?: string
  model_type: string
  price_per_1k_tokens?: number
  created_at?: string
}

export interface SystemSetting {
  key: string
  value: string
  description?: string
}

export const getModels = () => {
  return api.get<LLMModel[]>('/api/v1/settings/models')
}

export const createModel = (data: Omit<LLMModel, 'id' | 'created_at'>) => {
  return api.post<LLMModel>('/api/v1/settings/models', data)
}

export const updateModel = (id: number, data: Omit<LLMModel, 'id' | 'created_at'>) => {
  return api.put<LLMModel>(`/api/v1/settings/models/${id}`, data)
}

export const deleteModel = (id: number) => {
  return api.delete(`/api/v1/settings/models/${id}`)
}

export const getSystemSettings = () => {
  return api.get<SystemSetting[]>('/api/v1/settings/system')
}

export const updateSystemSettings = (data: { key: string; value: string; description?: string }[]) => {
  return api.post('/api/v1/settings/system', data)
}
