import { ElMessage } from 'element-plus'

const envTenantApiKey = import.meta.env.VITE_TENANT_API_KEY || ''

const getTenantApiKey = () => {
  const runtimeKey = localStorage.getItem('tenant_api_key') || sessionStorage.getItem('tenant_api_key') || ''
  if (runtimeKey) return runtimeKey
  if (envTenantApiKey) return envTenantApiKey
  if (import.meta.env.DEV) return 'sk-admin-test'
  return ''
}

const getAuthToken = () => {
  return localStorage.getItem('token') || sessionStorage.getItem('token') || ''
}

/**
 * Unified fetch wrapper for streaming requests.
 * Handles Authorization and X-API-Key headers automatically.
 * Handles 401 errors by redirecting to login.
 */
export async function fetchStream(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers)

  // Inject Auth Token
  const token = getAuthToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  // Inject Tenant API Key
  const tenantApiKey = getTenantApiKey()
  if (tenantApiKey) {
    headers.set('X-API-Key', tenantApiKey)
  }

  // Ensure Content-Type is JSON by default if body is present
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const config: RequestInit = {
    ...options,
    headers
  }

  try {
    const response = await fetch(url, config)

    if (response.status === 401) {
      console.error('Authentication failed (401)')
      localStorage.removeItem('token')
      sessionStorage.removeItem('token')
      
      // Prevent redirect loops if already on login page
      if (window.location.pathname !== '/login') {
         ElMessage.error('Session expired. Please login again.')
         window.location.href = '/login'
      }
      throw new Error('Unauthorized')
    }

    return response
  } catch (error) {
    throw error
  }
}
