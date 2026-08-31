/**
 * 合同风险识别接口（《11-合同风险识别核心功能设计》第 5 节）。
 */
import client from './client'
import type { ContractDetail, ContractJob, ContractPage } from './contractTypes'

function errorMessage(e: unknown): string {
  const err = e as { response?: { data?: { message?: string } }; message?: string }
  return err.response?.data?.message ?? err.message ?? '请求失败，请稍后再试'
}

export async function startContractUpload(
  file: File,
): Promise<{ job_id: string; contract_id: number }> {
  try {
    const form = new FormData()
    form.append('file', file)
    const resp = await client.post('/contracts/upload', form)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data as { job_id: string; contract_id: number }
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function startContractRescan(contractId: number): Promise<string> {
  try {
    const resp = await client.post(`/contracts/${contractId}/rescan`)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data.job_id as string
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function getContractJob(jobId: string): Promise<ContractJob> {
  try {
    const resp = await client.get(`/contracts/jobs/${jobId}`)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

/** 拉取 AI 流式输出全文（打字机效果数据源） */
export async function getContractJobStream(jobId: string): Promise<string> {
  try {
    const resp = await client.get(`/contracts/jobs/${jobId}/stream`)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return (resp.data.data as { content: string }).content
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function getContractJobByContract(contractId: number): Promise<ContractJob> {
  try {
    const resp = await client.get(`/contracts/${contractId}/job`)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function listContracts(params: {
  page?: number
  page_size?: number
  keyword?: string
  severity?: string
}): Promise<ContractPage> {
  try {
    const resp = await client.get('/contracts', { params })
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function getContractPreview(id: number): Promise<string> {
  try {
    const resp = await client.get(`/contracts/${id}/preview`)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return (resp.data.data as { text: string }).text
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}

export async function getContract(id: number): Promise<ContractDetail> {
  try {
    const resp = await client.get(`/contracts/${id}`)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
    return resp.data.data
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}


export async function deleteContract(id: number): Promise<void> {
  try {
    const resp = await client.delete(`/contracts/${id}`)
    if (resp.data.code !== 0) throw new Error(resp.data.message)
  } catch (e) {
    throw new Error(errorMessage(e))
  }
}