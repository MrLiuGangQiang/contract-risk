/**
 * 认证相关接口（《05-API设计规范》第 2.2 节）。
 */
import client from './client'
import type {
  DingTalkAuthorizeUrl,
  LoginMethods,
  TokenData,
  UserInfo,
} from './types'

/** 提取后端业务错误信息；网络异常返回通用文案 */
function errorMessage(e: unknown): string {
  const err = e as { response?: { data?: { message?: string } }; message?: string }
  return err.response?.data?.message ?? err.message ?? '请求失败，请稍后再试'
}

export async function getLoginMethods(): Promise<LoginMethods> {
  try {
    const resp = await client.get('/auth/login-methods')
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function login(username: string, password: string): Promise<TokenData> {
  try {
    const resp = await client.post('/auth/login', { username, password })
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function changePassword(old_password: string, new_password: string): Promise<void> {
  try {
    const resp = await client.post('/auth/change-password', { old_password, new_password })
    if (resp.data.code !== 0) throw new Error(resp.data.message)
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function logout(): Promise<void> {
  try {
    await client.post('/auth/logout')
  } catch {
    // 登出失败不阻塞前端清理
  }
}

export async function getDingtalkAuthorizeUrl(): Promise<DingTalkAuthorizeUrl> {
  try {
    const resp = await client.get('/auth/dingtalk/authorize-url')
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function dingtalkCallback(
  auth_code: string,
  state: string,
): Promise<TokenData> {
  try {
    const resp = await client.post('/auth/dingtalk/callback', { auth_code, state })
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

/**
 * 钉钉 H5 微应用免登（仅钉钉客户端内）：
 * 免登码来自 dd.runtime.permission.requestAuthCode，5 分钟有效、一次性。
 */
export async function dingtalkMicroappLogin(auth_code: string): Promise<TokenData> {
  try {
    const resp = await client.post('/auth/dingtalk/microapp-login', { auth_code })
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function getMe(): Promise<UserInfo> {
  try {
    const resp = await client.get('/auth/me')
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}
