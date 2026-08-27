<template>
  <AppLayout>
    <div class="contract-page">
      <el-card shadow="never">
        <div class="page-head">
          <h3>合同风险识别</h3>
          <span class="page-desc">上传合同，自动提取文本并按「规则 + AI」识别风险</span>
        </div>
        <div class="upload-row">
          <input ref="fileRef" type="file" accept=".txt,.pdf,.docx" style="display: none" @change="onFileChange" />
          <el-button type="primary" :icon="Upload" :loading="uploading" @click="fileRef?.click()">
            选择合同文件（txt / pdf / docx）
          </el-button>
          <span class="upload-tip">单文件 ≤ 20MB；任务后台执行，可实时查看进度</span>
        </div>
      </el-card>

      <el-card shadow="never">
        <div class="list-toolbar">
          <div class="filters">
            <el-input v-model="keyword" placeholder="按文件名搜索" clearable style="width: 220px" @keyup.enter="onSearch" @clear="onSearch">
              <template #prefix><el-icon><search /></el-icon></template>
            </el-input>
            <el-select v-model="severity" placeholder="最高风险" clearable style="width: 130px" @change="onSearch">
              <el-option v-for="(label, value) in severityMap" :key="value" :label="label" :value="value" />
            </el-select>
          </div>
          <el-button :icon="Refresh" :loading="loading" @click="loadList">刷新</el-button>
        </div>

        <el-table v-loading="loading" :data="items" stripe>
          <el-table-column prop="file_name" label="文件名" min-width="220" show-overflow-tooltip />
          <el-table-column label="类型" width="90">
            <template #default="{ row }">{{ row.file_ext.toUpperCase() }}</template>
          </el-table-column>
          <el-table-column label="字符数" width="100">
            <template #default="{ row }">{{ row.total_chars }}</template>
          </el-table-column>
          <el-table-column label="风险" width="200">
            <template #default="{ row }">
              <el-tag type="danger" size="small">高 {{ row.high_count }}</el-tag>
              <el-tag type="warning" size="small" class="risk-tag">中 {{ row.medium_count }}</el-tag>
              <el-tag type="info" size="small" class="risk-tag">低 {{ row.low_count }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="上传时间" min-width="150">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDetail(row.id)">查看</el-button>
              <el-button link type="warning" @click="onRescan(row)">重扫</el-button>
              <el-button link type="danger" @click="onDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pager">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="loadList"
            @size-change="loadList"
          />
        </div>
      </el-card>

      <!-- 风险详情 -->
      <el-dialog v-model="detailVisible" title="合同风险识别结果" width="900px" top="5vh" destroy-on-close>
        <div v-loading="detailLoading">
          <div v-if="detail" class="detail-head">
            <div class="detail-file">{{ detail.contract.file_name }}</div>
            <div class="detail-meta">{{ detail.contract.total_chars }} 字符 · {{ detail.risks.length }} 项风险</div>
          </div>

          <div v-if="detail && detail.risks.length === 0" class="empty-risk">
            未识别到风险，合同内容较规范。
          </div>

          <div v-for="(group, dim) in groupedRisks" :key="dim" class="risk-group">
            <div class="group-title">{{ categoryMap[dim] ?? dim }}</div>
            <div v-for="risk in group" :key="risk.id" class="risk-card">
              <div class="risk-head">
                <el-tag :type="severityType(risk.severity)" size="small">
                  {{ severityMap[risk.severity] ?? risk.severity }}
                </el-tag>
                <el-tag :type="risk.risk_source === 'ai' ? 'primary' : 'info'" size="small" effect="plain">
                  {{ risk.risk_source === 'ai' ? 'AI' : '规则' }}
                </el-tag>
                <span class="risk-name">{{ risk.rule_name }}</span>
                <span class="risk-code">{{ risk.rule_code }}</span>
              </div>
              <div class="risk-kws">
                命中：
                <el-tag v-for="kw in risk.matched_keywords" :key="kw" size="small" type="info" effect="plain">{{ kw }}</el-tag>
              </div>
              <pre class="risk-snippet">{{ risk.snippet }}</pre>
              <div class="risk-desc">{{ risk.description }}</div>
              <div class="risk-suggest">建议：{{ risk.suggestion }}</div>
            </div>
          </div>
        </div>
        <template #footer>
          <el-button @click="detailVisible = false">关闭</el-button>
          <el-button type="warning" :loading="rescanning" @click="onRescanCurrent">重新扫描</el-button>
        </template>
      </el-dialog>

      <!-- 扫描进度（大模型思维式展示） -->
      <el-dialog v-model="scanVisible" title="合同风险识别中" width="620px" :close-on-click-modal="false" @closed="stopPolling" @open="startPollingState">
        <div class="scan-body">
          <div class="scan-stage">
            <span class="scan-stage-text">{{ scanJob?.stage_message || '正在启动任务...' }}</span>
            <span class="scan-dots">
              <i></i><i></i><i></i>
            </span>
          </div>
          <el-progress :percentage="scanJob?.progress ?? 0" :stroke-width="10" :show-text="false" />
          <div class="scan-steps">
            <div v-for="step in steps" :key="step.progress" class="scan-step" :class="{ active: (scanJob?.progress ?? 0) >= step.progress }">
              <span class="scan-step-icon">{{ (scanJob?.progress ?? 0) >= step.progress ? '✓' : '·' }}</span>
              <span>{{ step.label }}</span>
            </div>
          </div>
          <div v-if="scanJob?.status === 'failed'" class="scan-error">{{ scanJob.error || scanJob.stage_message }}</div>
        </div>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search, Upload } from '@element-plus/icons-vue'
import {
  deleteContract,
  getContract,
  getContractJob,
  listContracts,
  startContractRescan,
  startContractUpload,
} from '@/api/contract'
import type { Contract, ContractDetail, ContractJob, ContractRisk } from '@/api/contractTypes'
import AppLayout from '@/components/AppLayout.vue'

const categoryMap: Record<string, string> = {
  project: '项目管理风险',
  technology: '技术风险',
  contract: '合同条款风险',
  general: '通用风险',
}
const severityMap: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
}
function severityType(severity: string): 'danger' | 'warning' | 'info' {
  if (severity === 'high') return 'danger'
  if (severity === 'medium') return 'warning'
  return 'info'
}

const steps = [
  { progress: 20, label: '提取合同文本' },
  { progress: 45, label: '规则匹配' },
  { progress: 70, label: 'AI 深度分析' },
  { progress: 90, label: '生成风险结果' },
]

const loading = ref(false)
const items = ref<Contract[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const severity = ref('')

const uploading = ref(false)
const fileRef = ref<HTMLInputElement>()

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<ContractDetail | null>(null)
const rescanning = ref(false)
const currentDetailId = ref(0)

const scanVisible = ref(false)
const scanJob = ref<ContractJob | null>(null)
let polling = false

const groupedRisks = computed<Record<string, ContractRisk[]>>(() => {
  const groups: Record<string, ContractRisk[]> = {}
  for (const risk of detail.value?.risks ?? []) {
    if (!groups[risk.category]) groups[risk.category] = []
    groups[risk.category].push(risk)
  }
  return groups
})

onMounted(loadList)

async function loadList() {
  loading.value = true
  try {
    const data = await listContracts({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      severity: severity.value || undefined,
    })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  void loadList()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (!['txt', 'pdf', 'docx'].includes(ext)) {
    ElMessage.warning('仅支持 txt / pdf / docx 文件')
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.warning('文件不能超过 20MB')
    return
  }
  uploading.value = true
  try {
    const jobId = await startContractUpload(file)
    await pollJob(jobId)
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    uploading.value = false
  }
}

async function pollJob(jobId: string) {
  scanVisible.value = true
  scanJob.value = { status: 'running', progress: 0, stage: 'created', stage_message: '任务已创建' }
  polling = true
  while (polling) {
    try {
      const job = await getContractJob(jobId)
      scanJob.value = job
      if (job.status === 'done') {
        polling = false
        scanVisible.value = false
        await new Promise((r) => setTimeout(r, 300))
        if (job.contract_id) {
          await openDetail(job.contract_id)
        }
        ElMessage.success(`扫描完成，识别到 ${job.risk_count ?? 0} 项风险`)
        await loadList()
        return
      }
      if (job.status === 'failed') {
        polling = false
        ElMessage.error(job.error || job.stage_message || '扫描失败')
        return
      }
    } catch (e) {
      polling = false
      ElMessage.error((e as Error).message)
      return
    }
    await new Promise((r) => setTimeout(r, 800))
  }
}

function startPollingState() {
  scanJob.value = { status: 'running', progress: 0, stage: 'created', stage_message: '任务已创建' }
}

function stopPolling() {
  polling = false
}

async function openDetail(id: number) {
  detailVisible.value = true
  detailLoading.value = true
  currentDetailId.value = id
  try {
    detail.value = await getContract(id)
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    detailLoading.value = false
  }
}

async function onRescan(row: Contract) {
  rescanning.value = true
  try {
    const jobId = await startContractRescan(row.id)
    await pollJob(jobId)
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    rescanning.value = false
  }
}

async function onRescanCurrent() {
  if (!currentDetailId.value) return
  rescanning.value = true
  try {
    const jobId = await startContractRescan(currentDetailId.value)
    await pollJob(jobId)
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    rescanning.value = false
  }
}

async function onDelete(row: Contract) {
  try {
    await ElMessageBox.confirm(`确定删除合同「${row.file_name}」？删除后风险结果一并清除。`, '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteContract(row.id)
    ElMessage.success('合同已删除')
    await loadList()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

function formatTime(value: string | null): string {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  return d.toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.contract-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.page-head {
  margin-bottom: 12px;
}
.page-head h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #111827;
}
.page-desc {
  font-size: 12px;
  color: #6b7280;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.upload-tip {
  font-size: 12px;
  color: #94a3b8;
}
.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.risk-tag {
  margin-left: 6px;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.detail-head {
  margin-bottom: 12px;
}
.detail-file {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  word-break: break-all;
}
.detail-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}
.empty-risk {
  padding: 40px 0;
  text-align: center;
  color: #10b981;
  font-size: 14px;
}
.risk-group {
  margin-bottom: 18px;
}
.group-title {
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #2563eb;
}
.risk-card {
  padding: 14px 16px;
  margin-bottom: 12px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
}
.risk-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.risk-name {
  font-weight: 600;
  color: #111827;
}
.risk-code {
  font-size: 12px;
  color: #94a3b8;
}
.risk-kws {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.risk-snippet {
  margin: 8px 0 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  font-size: 12px;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-all;
}
.risk-desc {
  margin-top: 10px;
  font-size: 13px;
  color: #475569;
}
.risk-suggest {
  margin-top: 6px;
  font-size: 13px;
  color: #b45309;
}
.scan-body {
  padding: 4px 8px 8px;
}
.scan-stage {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 600;
  color: #1e40af;
}
.scan-dots {
  display: inline-flex;
  gap: 4px;
}
.scan-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2563eb;
  animation: blink 1s infinite;
}
.scan-dots i:nth-child(2) {
  animation-delay: 0.2s;
}
.scan-dots i:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes blink {
  0%, 80%, 100% { opacity: 0.2; }
  40% { opacity: 1; }
}
.scan-steps {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.scan-step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f8fafc;
  color: #94a3b8;
  font-size: 12px;
}
.scan-step.active {
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  font-weight: 600;
}
.scan-step-icon {
  font-weight: 700;
}
.scan-error {
  margin-top: 12px;
  color: #dc2626;
  font-size: 13px;
  white-space: pre-wrap;
}
</style>