export interface ContractRisk {
  id: number
  rule_code: string
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

export interface ContractJob {
  job_id?: string
  status: ContractJobStatus
  progress: number
  stage: string
  stage_message: string
  contract_id?: number
  risk_count?: number
  user_id?: number
  error?: string
}
