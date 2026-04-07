import { post } from '@/api/request'

export interface LoginPayload {
  account: string
  password: string
  remember?: boolean
}

export interface LoginResponse {
  token: string
  userName: string
}

export interface UserInfo {
  id: number
  account: string
  userName: string
  avatar?: string
  email?: string
  phone?: string
  roles: string[]
  status: 'enabled' | 'disabled'
  createdAt: string
  updatedAt: string
}

export const loginApi = (payload: LoginPayload): Promise<LoginResponse> =>
  post<LoginResponse>('/auth/login', payload)

export const logoutApi = (): Promise<void> => post('/auth/logout')

export const getUserInfoApi = (): Promise<UserInfo> => post<UserInfo>('/auth/userinfo')
