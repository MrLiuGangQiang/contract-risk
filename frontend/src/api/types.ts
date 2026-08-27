/**
 * 鍚庣 API 绫诲瀷瀹氫箟锛堜笌銆?5-API璁捐瑙勮寖銆嬩繚鎸佷竴鑷达紝snake_case锛夈€?
 */

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T | null
  request_id: string | null
  timestamp: number
}

export interface UserInfo {
  id: number
  username: string
  display_name: string
  avatar_url: string | null
  is_super_admin: boolean
  must_change_password: boolean
  roles: string[]
  permissions: string[]
}

export interface TokenData {
  access_token: string
  expires_in: number
  token_type: string
  user: UserInfo
}

export interface DingTalkConfig {
  client_id: string
  client_secret_masked: string
  corp_id: string
  redirect_uri: string
  enabled: boolean
  updated_at: string | null
}

export interface DingTalkAuthorizeUrl {
  authorize_url: string
  state: string
}

export interface DingTalkTestResult {
  ok: boolean
  detail: string
}

export interface LoginMethods {
  dingtalk_enabled: boolean
}

export interface RiskRule {
  id: number
  code: string
  name: string
  category: string
  severity: string
  keywords: string[]
  description: string
  suggestion: string
  enabled: boolean
  sort_order: number
  created_at: string | null
  updated_at: string | null
}

export interface RiskRulePage {
  items: RiskRule[]
  total: number
  page: number
  page_size: number
}

export interface RiskRuleImportResult {
  created: number
  updated: number
  skipped: number
}

export interface Role {
  id: number
  code: string
  name: string
  description: string | null
  is_builtin: boolean
  status: number
}

export interface AdminUser {
  id: number
  username: string
  display_name: string
  status: number
  is_super_admin: boolean
  must_change_password: boolean
  roles: Role[]
  created_at: string | null
  last_login_at: string | null
}

export interface AdminUserPage {
  items: AdminUser[]
  total: number
  page: number
  page_size: number
}
