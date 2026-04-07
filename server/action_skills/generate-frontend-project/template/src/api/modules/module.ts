import { get, post } from '@/api/http'

export type ModuleStatus = 'enabled' | 'disabled' | 'draft'

export interface ModuleRecord {
  id: number
  name: string
  owner: string
  status: ModuleStatus
  updatedAt: string
  remark: string
}

export interface ModuleQuery {
  keyword: string
  status: string
}

export interface CreateModulePayload {
  name: string
  category: string
  owner: string
  budget: number | null
  enabled: boolean
  tags: string[]
  cycle: string[]
  description: string
}

export const fetchModuleListApi = (params: ModuleQuery) => get<ModuleRecord[]>('/modules', { params })

export const createModuleApi = (payload: CreateModulePayload) =>
  post<ModuleRecord>('/modules', payload)
