import { get, post, put, del } from '@/api/request'
import type { PaginationParams } from '@/api/type'

export interface UserRecord {
  id: number
  account: string
  userName: string
  email?: string
  phone?: string
  roles: string[]
  status: 'enabled' | 'disabled'
  createdAt: string
  updatedAt: string
}

export interface CreateUserPayload {
  account: string
  userName: string
  password?: string
  email?: string
  phone?: string
  roles: string[]
  status: 'enabled' | 'disabled'
}

export interface UpdateUserPayload extends Partial<CreateUserPayload> {
  id: number
}

export interface UserQueryParams extends PaginationParams {
  keyword?: string
  status?: string
  roleId?: number
}

export const getUserList = (params: UserQueryParams) =>
  get<UserRecord[]>('/system/users', { params })

export const createUser = (payload: CreateUserPayload) =>
  post<UserRecord>('/system/users', payload)

export const updateUser = (payload: UpdateUserPayload) =>
  put<UserRecord>(`/system/users/${payload.id}`, payload)

export const deleteUser = (id: number) => del<void>(`/system/users/${id}`)

export interface RoleRecord {
  id: number
  name: string
  code: string
  description?: string
  permissions: string[]
  status: 'enabled' | 'disabled'
  createdAt: string
  updatedAt: string
}

export interface CreateRolePayload {
  name: string
  code: string
  description?: string
  permissions: string[]
  status: 'enabled' | 'disabled'
}

export interface UpdateRolePayload extends Partial<CreateRolePayload> {
  id: number
}

export interface RoleQueryParams extends PaginationParams {
  keyword?: string
  status?: string
}

export const getRoleList = (params: RoleQueryParams) =>
  get<RoleRecord[]>('/system/roles', { params })

export const createRole = (payload: CreateRolePayload) =>
  post<RoleRecord>('/system/roles', payload)

export const updateRole = (payload: UpdateRolePayload) =>
  put<RoleRecord>(`/system/roles/${payload.id}`, payload)

export const deleteRole = (id: number) => del<void>(`/system/roles/${id}`)

export interface DepartmentRecord {
  id: number
  name: string
  parentId: number | null
  orderNum: number
  leader?: string
  phone?: string
  email?: string
  status: 'enabled' | 'disabled'
  children?: DepartmentRecord[]
}

export const getDeptTree = () => get<DepartmentRecord[]>('/system/departments')

export interface OperateLogRecord {
  id: number
  userId: number
  userName: string
  module: string
  action: string
  method: string
  url: string
  ip: string
  location?: string
  params?: string
  result?: string
  duration: number
  createdAt: string
}

export interface OperateLogParams extends PaginationParams {
  keyword?: string
  module?: string
  startDate?: string
  endDate?: string
}

export const getOperateLog = (params: OperateLogParams) =>
  get<OperateLogRecord[]>('/system/logs/operate', { params })

export interface LoginLogRecord {
  id: number
  userId: number
  userName: string
  account: string
  ip: string
  location?: string
  device?: string
  browser?: string
  status: 'success' | 'failed'
  message?: string
  createdAt: string
}

export interface LoginLogParams extends PaginationParams {
  keyword?: string
  status?: string
  startDate?: string
  endDate?: string
}

export const getLoginLog = (params: LoginLogParams) =>
  get<LoginLogRecord[]>('/system/logs/login', { params })

export interface SystemConfigRecord {
  key: string
  value: string
  type: 'string' | 'number' | 'boolean' | 'json'
  label: string
  group: string
  description?: string
}

export const getConfig = (key: string) =>
  get<SystemConfigRecord>(`/system/config/${key}`)

export const updateConfig = (key: string, value: string) =>
  put<SystemConfigRecord>(`/system/config/${key}`, { value })

export interface BackupRecord {
  id: number
  filename: string
  size: number
  status: 'success' | 'failed'
  message?: string
  createdAt: string
}

export const getBackupList = () => get<BackupRecord[]>('/system/backup')

export const createBackup = () => post<BackupRecord>('/system/backup')

export const restoreBackup = (id: number) =>
  post<void>(`/system/backup/${id}/restore`)

export interface NoticeRecord {
  id: number
  title: string
  content: string
  type: 'info' | 'warning' | 'error' | 'success'
  status: 'draft' | 'published' | 'archived'
  publishedAt?: string
  createdAt: string
  updatedAt: string
}

export interface CreateNoticePayload {
  title: string
  content: string
  type: 'info' | 'warning' | 'error' | 'success'
  status: 'draft' | 'published' | 'archived'
}

export interface UpdateNoticePayload extends Partial<CreateNoticePayload> {
  id: number
}

export interface NoticeQueryParams extends PaginationParams {
  keyword?: string
  status?: string
  type?: string
}

export const getNoticeList = (params: NoticeQueryParams) =>
  get<NoticeRecord[]>('/system/notices', { params })

export const createNotice = (payload: CreateNoticePayload) =>
  post<NoticeRecord>('/system/notices', payload)

export const updateNotice = (payload: UpdateNoticePayload) =>
  put<NoticeRecord>(`/system/notices/${payload.id}`, payload)

export const deleteNotice = (id: number) => del<void>(`/system/notices/${id}`)
