import axios, { type AxiosRequestConfig, type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import {
  ACCESS_TOKEN_KEY,
  REQUEST_TIMEOUT,
} from '@/constants/app'

const http: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: REQUEST_TIMEOUT,
})

http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY)

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error) => {
    console.error('请求发送失败', error)
    return Promise.reject(error)
  },
)

http.interceptors.response.use(
  (response) => {
    const payload = response.data

    if (payload && typeof payload === 'object' && 'code' in payload) {
      if (payload.code === 200) {
        return payload.data
      }

      const message = payload.message || '请求处理失败'
      ElMessage.error(message)
      return Promise.reject(new Error(message))
    }

    return response.data
  },
  (error) => {
    const { response } = error

    if (response) {
      const status = response.status

      if (status === 401) {
        ElMessage.error('登录已过期，请重新登录')
        localStorage.removeItem(ACCESS_TOKEN_KEY)
        router.push('/login')
      } else if (status === 403) {
        ElMessage.error('您没有权限访问该资源')
        router.push('/403')
      } else if (status === 404) {
        ElMessage.error('请求的资源不存在')
      } else if (status >= 500) {
        ElMessage.error('服务器错误，请稍后再试')
        router.push('/500')
      } else {
        const message = response.data?.message || '请求处理失败'
        ElMessage.error(message)
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后再试')
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }

    return Promise.reject(error)
  },
)

export const get = <T = any>(
  url: string,
  config?: AxiosRequestConfig,
): Promise<T> => {
  return http.get(url, config)
}

export const post = <T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig,
): Promise<T> => {
  return http.post(url, data, config)
}

export const put = <T = any>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig,
): Promise<T> => {
  return http.put(url, data, config)
}

export const del = <T = any>(
  url: string,
  config?: AxiosRequestConfig,
): Promise<T> => {
  return http.delete(url, config)
}

export default http
