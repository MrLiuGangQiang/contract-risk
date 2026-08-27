/**
 * 认证状态（Pinia）：access token 存内存，user 信息；refresh token 在 httpOnly Cookie。
 * 页面刷新/应用重启时通过 refresh 接口静默恢复会话（《04》第 2 节）。
 */
import axios from 'axios'
import { defineStore } from 'pinia'
import type { ApiResponse, TokenData, UserInfo } from '@/api/types'

// 并发恢复会话去重（模块级，避免 Pinia state 存 Promise）
let restoringPromise: Promise<boolean> | null = null

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: '' as string,
    user: null as UserInfo | null,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken),
    mustChangePassword: (state) => Boolean(state.user?.must_change_password),
    isSuperAdmin: (state) => Boolean(state.user?.is_super_admin),
  },
  actions: {
    setTokens(data: TokenData) {
      this.accessToken = data.access_token
      this.user = data.user
    },
    setUser(user: UserInfo) {
      this.user = user
    },
    clear() {
      this.accessToken = ''
      this.user = null
    },

    /**
     * 用 httpOnly refresh Cookie 静默恢复登录态（仅一次；失败返回 false）。
     * 避免页面刷新、浏览器标签重开时被强制重新登录。
     */
    async restoreSession(): Promise<boolean> {
      if (this.accessToken) return true
      if (restoringPromise) return restoringPromise
      restoringPromise = (async () => {
        try {
          const resp = await axios.post<ApiResponse<TokenData>>(
            '/api/v1/auth/refresh',
            {},
            { withCredentials: true },
          )
          if (resp.data.code === 0 && resp.data.data) {
            this.setTokens(resp.data.data)
            return true
          }
          return false
        } catch {
          return false
        } finally {
          restoringPromise = null
        }
      })()
      return restoringPromise
    },
  },
})