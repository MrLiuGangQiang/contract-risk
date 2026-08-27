/**
 * axios 实例与拦截器：注入 access token、统一错误处理、401 自动刷新重放（《07》第 11 节）。
 */
import axios, {
  AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'
import type { ApiResponse } from './types'

/** 认证类错误码：未认证/令牌过期/无效（触发刷新重放） */
const AUTH_ERROR_CODES = [30000, 30001, 30002]

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  withCredentials: true, // refresh token 走 httpOnly Cookie
})

// 请求拦截：附加 Bearer token
client.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  return config
})

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean }

/** 使用裸 axios 刷新令牌（避免拦截器递归），返回新 access token 或 null */
async function refreshAccessToken(): Promise<string | null> {
  try {
    const resp = await axios.post<ApiResponse<{ access_token: string }>>(
      '/api/v1/auth/refresh',
      {},
      { withCredentials: true },
    )
    if (resp.data.code === 0 && resp.data.data) {
      return resp.data.data.access_token
    }
    return null
  } catch {
    return null
  }
}

let refreshing: Promise<string | null> | null = null

// 响应拦截：认证错误时刷新一次并重放；刷新失败则登出跳转
client.interceptors.response.use(
  (resp: AxiosResponse) => resp,
  async (error: AxiosError<ApiResponse>) => {
    const config = error.config as RetriableConfig | undefined
    const code = error.response?.data?.code
    if (config && code !== undefined && AUTH_ERROR_CODES.includes(code) && !config._retried) {
      config._retried = true
      if (!refreshing) {
        refreshing = refreshAccessToken()
      }
      const token = await refreshing
      refreshing = null
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
        return client(config)
      }
      const auth = useAuthStore()
      auth.clear()
      router.push({ name: 'login' })
    }
    return Promise.reject(error)
  },
)

export default client