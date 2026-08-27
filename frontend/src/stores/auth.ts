/**
 * 认证状态（Pinia）：access token 存内存，user 信息；refresh token 在 httpOnly Cookie。
 */
import { defineStore } from 'pinia'
import type { TokenData, UserInfo } from '@/api/types'

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
  },
})