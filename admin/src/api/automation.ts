import request from './axios'

export interface AutomationTask {
  id: number
  name: string
  agent_id: string
  input_prompt: string
  cron_expression?: string
  interval_seconds?: number
  is_one_time: boolean
  is_active: boolean
  last_run_time?: string
  created_at: string
}

export interface AutomationLog {
  id: number
  task_id: number
  status: string
  output?: string
  error_message?: string
  start_time: string
  end_time?: string
}

export const getTasks = () => {
  return request.get<AutomationTask[]>('/api/v1/automation/tasks')
}

export const createTask = (data: any) => {
  return request.post<AutomationTask>('/api/v1/automation/tasks', data)
}

export const updateTask = (id: number, data: any) => {
  return request.put<AutomationTask>(`/api/v1/automation/tasks/${id}`, data)
}

export const deleteTask = (id: number) => {
  return request.delete(`/api/v1/automation/tasks/${id}`)
}

export const runTask = (id: number) => {
  return request.post(`/api/v1/automation/tasks/${id}/run`)
}

export const getTaskLogs = (id: number) => {
  return request.get<AutomationLog[]>(`/api/v1/automation/tasks/${id}/logs`)
}

export const generateCronExpression = (description: string) => {
  return request.post<{ cron_expression: string }>('/api/v1/automation/cron/generate', { description })
}
