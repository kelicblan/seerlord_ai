import { get, post } from '@/api/request'

export interface ExampleItem {
  id: number
  title: string
  category: string
  status: number
  views: number
  createTime: string
}

export interface ExampleDetail extends ExampleItem {
  content?: string
}

export interface ExampleListParams {
  page?: number
  pageSize?: number
  keyword?: string
  status?: number | null
}

export interface ExampleListResponse {
  list: ExampleItem[]
  total: number
  page: number
  pageSize: number
}

export interface ExampleFormData {
  id?: number
  title: string
  category: string
  status: boolean
  content?: string
}

export const examplesListApi = (params: ExampleListParams) =>
  get<ExampleListResponse>('/examples/list', { params })

export const examplesDetailApi = (id: number) =>
  get<ExampleDetail>('/examples/detail', { params: { id } })

export const examplesCreateApi = (data: ExampleFormData) =>
  post<{ id: number }>('/examples/create', data)

export const examplesUpdateApi = (data: ExampleFormData) =>
  post('/examples/update', data)

export const examplesDeleteApi = (id: number) =>
  post('/examples/delete', { id })
