/**
 * 超管配置中心接口（《05-API设计规范》第 2.3 节）。
 */
import client from './client'
import type { AdminUser, AdminUserPage, AIConfig, AITestResult, DingTalkConfig, DingTalkTestResult, RiskRule, RiskRuleImportResult, RiskRulePage, Role } from './types'

export interface DingTalkConfigPayload {
  client_id: string
  client_secret: string
  corp_id: string
  redirect_uri: string
  enabled: boolean
}

function errorMessage(e: unknown): string {
  const err = e as { response?: { data?: { message?: string } }; message?: string }
  return err.response?.data?.message ?? err.message ?? '请求失败，请稍后再试'
}

export async function getDingtalkConfig(): Promise<DingTalkConfig> {
  try {
    const resp = await client.get('/admin/configs/dingtalk')
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function updateDingtalkConfig(
  payload: DingTalkConfigPayload,
): Promise<DingTalkConfig> {
  try {
    const resp = await client.put('/admin/configs/dingtalk', payload)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function testDingtalkConfig(): Promise<DingTalkTestResult> {
  try {
    const resp = await client.post('/admin/configs/dingtalk/test')
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}
// ==================== 用户与角色管理（《05-API设计规范》 2.4 节） ====================

export interface AdminUserCreatePayload {
  username: string
  display_name: string
  password: string
  roles: string[]
}

export interface AdminUserUpdatePayload {
  display_name: string
  status: number
  roles: string[]
}

export async function listUsers(params: {
  page?: number
  page_size?: number
  keyword?: string
}): Promise<AdminUserPage> {
  try {
    const resp = await client.get('/admin/users', { params })
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function createUser(payload: AdminUserCreatePayload): Promise<AdminUser> {
  try {
    const resp = await client.post('/admin/users', payload)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function updateUser(userId: number, payload: AdminUserUpdatePayload): Promise<AdminUser> {
  try {
    const resp = await client.put(`/admin/users/${userId}`, payload)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function resetUserPassword(userId: number, password: string): Promise<void> {
  try {
    const resp = await client.put(`/admin/users/${userId}/password`, { password })
    if (resp.data.code !== 0) throw new Error(resp.data.message)
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function deleteUser(userId: number): Promise<void> {
  try {
    const resp = await client.delete(`/admin/users/${userId}`)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

// ==================== 风险规则（《10》第 4 节）====================

export interface RiskRulePayload {
  code?: string
  name: string
  category: string
  severity: string
  keywords: string[]
  description: string
  suggestion: string
  enabled: boolean
  sort_order: number
}

export async function listRiskRules(params: {
  page?: number
  page_size?: number
  keyword?: string
  category?: string
  severity?: string
  enabled?: boolean
}): Promise<RiskRulePage> {
  try {
    const resp = await client.get('/admin/risk-rules', { params })
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function createRiskRule(payload: RiskRulePayload): Promise<RiskRule> {
  try {
    const resp = await client.post('/admin/risk-rules', payload)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function updateRiskRule(ruleId: number, payload: RiskRulePayload): Promise<RiskRule> {
  try {
    const resp = await client.put(`/admin/risk-rules/${ruleId}`, payload)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function deleteRiskRule(ruleId: number): Promise<void> {
  try {
    const resp = await client.delete(`/admin/risk-rules/${ruleId}`)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function importRiskRules(content: string): Promise<RiskRuleImportResult> {
  try {
    const resp = await client.post('/admin/risk-rules/import', { content })
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function exportRiskRules(): Promise<Blob> {
  try {
    const resp = await client.get('/admin/risk-rules/export', { responseType: 'blob' })
    return resp.data as Blob
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

// ==================== 个人风险规则（《10》第 5.2 节）====================

export async function listMyRiskRules(): Promise<RiskRule[]> {
  try {
    const resp = await client.get('/risk-rules')
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function updateMyRiskRule(code: string, payload: RiskRulePayload): Promise<RiskRule> {
  try {
    const resp = await client.put(`/risk-rules/me/${encodeURIComponent(code)}`, payload)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function deleteMyRiskRule(code: string): Promise<void> {
  try {
    const resp = await client.delete(`/risk-rules/me/${encodeURIComponent(code)}`)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function restoreMyRiskRules(): Promise<void> {
  try {
    const resp = await client.post('/risk-rules/me/restore-default')
    if (resp.data.code !== 0) throw new Error(resp.data.message)
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function listRoles(): Promise<Role[]> {
  try {
    const resp = await client.get('/admin/roles')
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}



// ==================== AI 配置（《11》第 2.2 节）====================

export interface AIConfigPayload {
  enabled: boolean
  api_base: string
  api_key: string
  model: string
  timeout_seconds: number
  context_chars: number
  max_findings: number
}

export async function getAIConfig(): Promise<AIConfig> {
  try {
    const resp = await client.get('/admin/configs/ai')
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function updateAIConfig(payload: AIConfigPayload): Promise<AIConfig> {
  try {
    const resp = await client.put('/admin/configs/ai', payload)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function testAIConfig(): Promise<AITestResult> {
  try {
    const resp = await client.post('/admin/configs/ai/test')
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}
