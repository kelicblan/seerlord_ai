import api from './axios'

// Reuse types from Vue file or define here
export type SkillLevel = 1 | 2 | 3

export interface Skill {
  id: string
  name: string
  description: string
  category: string
  level: SkillLevel
  parentId?: string
  content: string
  tags: string[]
  version: number
}

export const getSkills = (category?: string) => {
  return api.get<Skill[]>('/api/v1/skills', { params: { category } })
}

export const getSkill = (id: string) => {
  return api.get<Skill>(`/api/v1/skills/${id}`)
}

export const createSkill = (data: Omit<Skill, 'id' | 'version'>) => {
  return api.post<Skill>('/api/v1/skills', data)
}

export const updateSkill = (id: string, data: Partial<Skill>) => {
  return api.put<Skill>(`/api/v1/skills/${id}`, data)
}

export const deleteSkill = (id: string) => {
  return api.delete(`/api/v1/skills/${id}`)
}

export const getSkillHistory = (id: string) => {
  return api.get<any[]>(`/api/v1/skills/${id}/history`)
}
