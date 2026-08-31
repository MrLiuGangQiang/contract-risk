export interface ContractRisk {
  id: number
  rule_code: string | null
  snippet_start: number | null
  snippet_end: number | null
  rule_name: string
  category: string
  severity: string
  matched_keywords: string[]
  risk_source: 'rule' | 'ai'
  snippet: string
  description: string
  suggestion: string
  sort_order: number
  created_at: string | null
}

export interface Contract {
  id: number
  user_id: number
  file_name: string
  file_ext: string
  file_size: number
  total_chars: number
  status: number
  risk_count: number
  high_count: number
  medium_count: number
  low_count: number
  created_at: string | null
}

export interface ContractPage {
  items: Contract[]
  total: number
  page: number
  page_size: number
}

export interface ContractDetail {
  contract: Contract
  risks: ContractRisk[]
}

export type ContractJobStatus = 'running' | 'done' | 'failed'

export interface ContractJobEvent {
  time: string
  level: 'info' | 'error'
  message: string
}

/** 维度并发任务状态 */
export interface ScanTaskState {
  label: string
  status: 'pending' | 'running' | 'done'
  rule_count: number
  hits: number
}

export type AiScanStatus = 'running' | 'skipped' | 'done' | 'failed'

export interface ContractJob {
  job_id?: string
  status: ContractJobStatus
  progress: number
  stage: string
  stage_message: string
  contract_id?: number
  risk_count?: number
  user_id?: number
  file_name?: string
  error?: string
  events?: ContractJobEvent[]
  /** 维度并发任务（key = category） */
  tasks?: Record<string, ScanTaskState>
  /** AI 分析状态 */
  ai?: { status: AiScanStatus; findings: number }
  /** 逐条规则校验状态（每条规则一个并发 AI 任务） */
  rule_checks?: Record<string, { code: string; status: string; detail: string }>
}

/** 合同状态：1=已完成 2=失败 3=扫描中（后台任务执行） */
export type ContractStatus = 1 | 2 | 3

export const CONTRACT_STATUS_DONE = 1
export const CONTRACT_STATUS_FAILED = 2
export const CONTRACT_STATUS_SCANNING = 3
