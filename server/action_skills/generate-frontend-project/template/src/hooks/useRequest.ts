import { ref, type Ref } from 'vue'
import axios, {
  type AxiosRequestConfig,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios'
import { ACCESS_TOKEN_KEY } from '@/constants/app'

export interface UseRequestOptions {
  enableDeduplication?: boolean
  defaultTimeout?: number
}

export interface UseRequestReturn {
  loading: Ref<boolean>
  pendingCount: Ref<number>
  deduplicationCache: Map<string, Promise<unknown>>
  setAuthToken: (token: string) => void
  removeAuthToken: () => void
  clearDeduplicationCache: () => void
  createRequestConfig: (config?: AxiosRequestConfig) => AxiosRequestConfig
  withLoading: <T>(request: Promise<T>) => Promise<T>
  withTimeout: <T>(promise: Promise<T>, timeout?: number) => Promise<T>
  deduplicateRequest: <T>(config: AxiosRequestConfig, requestFn: () => Promise<T>) => Promise<T>
  createRequestInterceptor: () => number
}

const generateRequestKey = (config: AxiosRequestConfig): string => {
  const { method, url, params, data } = config
  return [method, url, JSON.stringify(params), JSON.stringify(data)].join('&')
}

export const useRequest = (options: UseRequestOptions = {}): UseRequestReturn => {
  const { enableDeduplication = true, defaultTimeout = 30000 } = options

  const loading = ref(false)
  const pendingCount = ref(0)
  const deduplicationCache = new Map<string, Promise<unknown>>()
  const authToken = ref<string | null>(localStorage.getItem(ACCESS_TOKEN_KEY))

  const setAuthToken = (token: string): void => {
    authToken.value = token
    localStorage.setItem(ACCESS_TOKEN_KEY, token)
  }

  const removeAuthToken = (): void => {
    authToken.value = null
    localStorage.removeItem(ACCESS_TOKEN_KEY)
  }

  const clearDeduplicationCache = (): void => {
    deduplicationCache.clear()
  }

  const createRequestConfig = (config?: AxiosRequestConfig): InternalAxiosRequestConfig => {
    const finalConfig = {
      ...config,
      timeout: config?.timeout ?? defaultTimeout,
    } as InternalAxiosRequestConfig

    if (authToken.value) {
      finalConfig.headers = {
        ...finalConfig.headers,
        Authorization: `Bearer ${authToken.value}`,
      } as InternalAxiosRequestConfig['headers']
    }

    return finalConfig
  }

  const withLoading = async <T>(request: Promise<T>): Promise<T> => {
    loading.value = true
    pendingCount.value++

    try {
      return await request
    } finally {
      pendingCount.value--
      if (pendingCount.value <= 0) {
        pendingCount.value = 0
        loading.value = false
      }
    }
  }

  const withTimeout = <T>(promise: Promise<T>, timeout?: number): Promise<T> => {
    const timeoutMs = timeout ?? defaultTimeout
    return Promise.race([
      promise,
      new Promise<T>((_, reject) =>
        setTimeout(() => reject(new Error(`请求超时: ${timeoutMs}ms`)), timeoutMs)
      ),
    ])
  }

  const deduplicateRequest = <T>(
    config: AxiosRequestConfig,
    requestFn: () => Promise<T>
  ): Promise<T> => {
    if (!enableDeduplication) {
      return requestFn()
    }

    const key = generateRequestKey(config)

    if (deduplicationCache.has(key)) {
      console.warn('检测到重复请求，已合并:', key)
      return deduplicationCache.get(key) as Promise<T>
    }

    const requestPromise = requestFn().finally(() => {
      setTimeout(() => {
        deduplicationCache.delete(key)
      }, 1000)
    })

    deduplicationCache.set(key, requestPromise)
    return requestPromise
  }

  const createRequestInterceptor = () => {
    return axios.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const finalConfig = createRequestConfig(config)

        if (enableDeduplication) {
          const key = generateRequestKey(finalConfig)
          if (deduplicationCache.has(key)) {
            console.warn('请求去重:', key)
          }
        }

        return finalConfig
      },
      (error: AxiosError) => {
        console.error('请求拦截器错误:', error)
        return Promise.reject(error)
      }
    )
  }

  return {
    loading,
    pendingCount,
    deduplicationCache,
    setAuthToken,
    removeAuthToken,
    clearDeduplicationCache,
    createRequestConfig,
    withLoading,
    withTimeout,
    deduplicateRequest,
    createRequestInterceptor,
  }
}

export const requestInterceptor = useRequest()
