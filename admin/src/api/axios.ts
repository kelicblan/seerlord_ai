import axios from 'axios'

const envTenantApiKey = import.meta.env.VITE_TENANT_API_KEY || ''

export const getTenantApiKey = () => {
  const runtimeKey = localStorage.getItem('tenant_api_key') || sessionStorage.getItem('tenant_api_key') || ''
  if (runtimeKey) return runtimeKey
  if (envTenantApiKey) return envTenantApiKey
  if (import.meta.env.DEV) return 'sk-admin-test'
  return ''
}

// Create axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '', // Fallback to relative path if not set, assuming proxy
})

// Request interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token')
  const tenantApiKey = getTenantApiKey()
  config.headers = config.headers ?? {}
  if (token) {
    if (typeof (config.headers as any).set === 'function') {
      ;(config.headers as any).set('Authorization', `Bearer ${token}`)
    } else {
      ;(config.headers as any).Authorization = `Bearer ${token}`
    }
  }
  // 为后端 TenantMiddleware 注入租户 API Key（优先使用 VITE_TENANT_API_KEY）
  if (tenantApiKey) {
    if (typeof (config.headers as any).set === 'function') {
      ;(config.headers as any).set('X-API-Key', tenantApiKey)
    } else {
      ;(config.headers as any)['X-API-Key'] = tenantApiKey
    }
  }
  return config
})

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const requestUrl: string = error.config?.url || ''
      if (requestUrl.includes('/api/v1/login/access-token')) {
        return Promise.reject(error)
      }
      const detail: string = typeof error.response?.data?.detail === 'string' ? error.response.data.detail : ''
      if (detail.includes('X-API-Key') || detail.includes('Tenant')) {
        return Promise.reject(error)
      }
      console.error('Authentication failed (401):', error.response.data)
      localStorage.removeItem('token')
      sessionStorage.removeItem('token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
