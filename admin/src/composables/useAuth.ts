import { ref, computed } from 'vue'
import api from '@/api/axios'

export interface AuthUser {
  id?: number
  username?: string
  is_active?: boolean
  is_superuser?: boolean
}

const user = ref<AuthUser | null>(null)

// 获取已持久化的 token：优先 localStorage，其次 sessionStorage（用于未勾选“记住我”的场景）
const getStoredToken = (): string | null => {
  return localStorage.getItem('token') || sessionStorage.getItem('token')
}

// 写入 token：remember=true -> localStorage；remember=false -> sessionStorage
const setStoredToken = (accessToken: string, remember: boolean) => {
  if (remember) {
    sessionStorage.removeItem('token')
    localStorage.setItem('token', accessToken)
  } else {
    localStorage.removeItem('token')
    sessionStorage.setItem('token', accessToken)
  }
}

// 清理 token：同时清理两处存储，避免登录态不一致
const clearStoredToken = () => {
  localStorage.removeItem('token')
  sessionStorage.removeItem('token')
}

const token = ref<string | null>(getStoredToken())

const isAuthenticated = computed(() => !!token.value)

// 退出登录：清理 token 和用户信息并回到登录页
const logout = () => {
  token.value = null
  user.value = null
  clearStoredToken()
  window.location.href = '/login'
}

export function useAuth() {
  // 登录：获取 access_token，按“记住我”策略保存，并拉取当前用户信息
  const login = async (username: string, password: string, remember: boolean = true) => {
    const params = new URLSearchParams()
    params.append('username', username)
    params.append('password', password)

    // 兼容两种部署方式：
    // 1) Vite 代理（vite.config.ts）；2) 同源部署（baseURL 为空）
    const response = await api.post<{ access_token: string }>('/api/v1/login/access-token', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    const { access_token } = response.data

    token.value = access_token
    setStoredToken(access_token, remember)

    await fetchUser()
  }

  // 拉取当前登录用户信息（用于侧边栏/权限显示等）
  const fetchUser = async () => {
    if (!token.value) return
    try {
      const response = await api.get<AuthUser>('/api/v1/users/me')
      user.value = response.data
    } catch (e) {
      console.error('获取用户信息失败：', e)
      // 这里不主动登出：401 会由 axios 拦截器统一处理
    }
  }

  return {
    user,
    token,
    isAuthenticated,
    login,
    logout,
    fetchUser
  }
}
