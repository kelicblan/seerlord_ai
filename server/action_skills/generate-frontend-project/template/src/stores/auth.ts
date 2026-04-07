import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { loginApi } from '@/api/modules/auth'
import type { AuthSession } from './types'
import router from '@/router'
import {
  ACCESS_TOKEN_KEY,
  DEFAULT_ROUTE,
  LOGIN_ROUTE,
  USER_NAME_KEY,
} from '@/constants/app'

export interface LoginPayload {
  account: string
  password: string
  captcha?: string
  captchaKey?: string
  remember: boolean
}

const ALL_PERMISSIONS = [
  'system:user:view',
  'system:role:view',
  'security:permission:view',
  'system:dept:view',
  'system:config:view',
  'system:notice:view',
  'system:log:operate',
  'system:log:login',
  'system:backup:view',
  'security:anomaly:view',
  'security:encryption:view',
  'security:rate-limit:view',
]

export const useAuthStore = defineStore(
  'auth',
  () => {
    const token = ref('')
    const userName = ref('')
    const roles = ref<string[]>([])
    const permissions = ref<string[]>([])
    const loading = ref(false)

    const isAuthenticated = computed(() => Boolean(token.value))
    const isAdmin = computed(() => roles.value.includes('admin'))

    const setSession = (session: AuthSession) => {
      token.value = session.token
      userName.value = session.userName

      if (session.userName?.toLowerCase() === 'admin') {
        roles.value = ['admin']
        permissions.value = ALL_PERMISSIONS
      } else if (session.userName?.toLowerCase() === 'guest') {
        roles.value = ['guest']
        permissions.value = []
      } else {
        roles.value = session.roles || []
        permissions.value = session.permissions || []
      }

      localStorage.setItem(ACCESS_TOKEN_KEY, session.token)
      localStorage.setItem(USER_NAME_KEY, session.userName)
    }

    const clearSession = () => {
      token.value = ''
      userName.value = ''
      roles.value = []
      permissions.value = []
      localStorage.removeItem(ACCESS_TOKEN_KEY)
      localStorage.removeItem(USER_NAME_KEY)
    }

    const login = async (payload: LoginPayload) => {
      loading.value = true

      try {
        const session = await loginApi(payload)
        setSession(session)
        return session
      } catch (error) {
        console.error('登录失败', error)
        throw error
      } finally {
        loading.value = false
      }
    }

    const logout = async () => {
      clearSession()

      if (router.currentRoute.value.path !== LOGIN_ROUTE) {
        await router.replace(LOGIN_ROUTE)
      }
    }

    const ensureSession = () => {
      if (token.value) {
        localStorage.setItem(ACCESS_TOKEN_KEY, token.value)
      }

      if (userName.value) {
        localStorage.setItem(USER_NAME_KEY, userName.value)
      }

      if (token.value && !userName.value) {
        userName.value = localStorage.getItem(USER_NAME_KEY) || '系统管理员'
      }
    }

    const redirectAfterLogin = async (redirect?: string | null) => {
      await router.replace(redirect || DEFAULT_ROUTE)
    }

    return {
      token,
      userName,
      roles,
      permissions,
      loading,
      isAuthenticated,
      isAdmin,
      login,
      logout,
      clearSession,
      ensureSession,
      redirectAfterLogin,
    }
  },
  {
    persist: {
      key: 'auth-session',
      pick: ['token', 'userName', 'roles', 'permissions'],
    },
  },
)
