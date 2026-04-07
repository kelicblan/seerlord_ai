import axios, { type AxiosError, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import {
  ACCESS_TOKEN_KEY,
  DEFAULT_ROUTE,
  LOGIN_ROUTE,
  SUCCESS_CODE,
} from '@/constants/app'

export interface StatusCodeConfig {
  code: number
  message: string
  action?: 'toast' | 'redirect' | 'retry' | 'silent'
  redirectUrl?: string
}

export interface UseResponseOptions {
  enableToast?: boolean
  enableRedirect?: boolean
  statusCodeMapping?: StatusCodeConfig[]
}

export interface UseResponseReturn {
  handleResponse: <T>(response: AxiosResponse<T>) => unknown
  handleError: (error: AxiosError) => Promise<never>
  getErrorMessage: (error: AxiosError) => string
  isSuccessCode: (code: number) => boolean
  getStatusMessage: (status: number) => string
  createResponseInterceptor: () => number
}

const DEFAULT_STATUS_MESSAGES: Record<number, string> = {
  400: '请求参数错误',
  401: '登录状态已失效，请重新登录',
  403: '没有访问权限',
  404: '请求资源不存在',
  408: '请求超时',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务暂不可用',
  504: '网关超时',
}

const DEFAULT_ERROR_MESSAGES = {
  network: '网络连接失败，请检查网络设置',
  timeout: '请求超时，请稍后重试',
  cancel: '请求已取消',
  unknown: '未知错误，请稍后重试',
}

export const useResponse = (options: UseResponseOptions = {}): UseResponseReturn => {
  const {
    enableToast = true,
    enableRedirect = true,
    statusCodeMapping,
  } = options

  const getStatusMessage = (status: number): string => {
    return DEFAULT_STATUS_MESSAGES[status] || `请求失败 (${status})`
  }

  const getErrorMessage = (error: AxiosError): string => {
    if (axios.isCancel(error)) {
      return DEFAULT_ERROR_MESSAGES.cancel
    }

    if (error.code === 'ECONNABORTED') {
      return DEFAULT_ERROR_MESSAGES.timeout
    }

    if (!navigator.onLine) {
      return DEFAULT_ERROR_MESSAGES.network
    }

    const response = error.response
    if (response) {
      const customMapping = statusCodeMapping?.find(m => m.code === response.status)
      if (customMapping) {
        return customMapping.message
      }
      return (
        response.data &&
        typeof response.data === 'object' &&
        'message' in response.data
      ) ? (response.data as { message: string }).message : getStatusMessage(response.status)
    }

    if (error.message.includes('Network Error')) {
      return DEFAULT_ERROR_MESSAGES.network
    }

    return error.message || DEFAULT_ERROR_MESSAGES.unknown
  }

  const isSuccessCode = (code: number): boolean => {
    return code === SUCCESS_CODE
  }

  const handleResponse = <T>(response: AxiosResponse<T>): unknown => {
    const payload = response.data as Partial<{ code: number; message: string; data: unknown }>

    if (payload && 'code' in payload) {
      if (isSuccessCode(payload.code!)) {
        return payload.data
      }

      const message = payload.message || '请求处理失败'
      if (enableToast) {
        ElMessage.error(message)
      }
      return Promise.reject(new Error(message))
    }

    return response.data
  }

  const handleError = async (error: AxiosError): Promise<never> => {
    console.error('响应拦截器错误:', error)

    const status = error.response?.status
    const message = getErrorMessage(error)

    if (enableToast) {
      ElMessage.error(message)
    }

    if (status === 401 && enableRedirect) {
      localStorage.removeItem(ACCESS_TOKEN_KEY)

      if (router.currentRoute.value.path !== LOGIN_ROUTE) {
        await router.replace({
          path: LOGIN_ROUTE,
          query: {
            redirect: router.currentRoute.value.fullPath || DEFAULT_ROUTE,
          },
        })
      }
    }

    return Promise.reject(error)
  }

  const createResponseInterceptor = () => {
    return axios.interceptors.response.use(
      (response: AxiosResponse) => handleResponse(response) as unknown as AxiosResponse,
      (error: AxiosError) => handleError(error)
    )
  }

  return {
    handleResponse,
    handleError,
    getErrorMessage,
    isSuccessCode,
    getStatusMessage,
    createResponseInterceptor,
  }
}

export const responseInterceptor = useResponse()
