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
          <el-button type="primary" :icon="UploadFilled" :loading="uploading" @click="fileRef?.click()">
            上传合同
          </el-button>
          <span class="upload-tip">支持 txt / pdf / docx · 单文件 ≤ 20MB</span>
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
          <el-table-column label="类型" width="80">
            <template #default="{ row }">{{ row.file_ext.toUpperCase() }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <span v-if="row.status === CONTRACT_STATUS_SCANNING" class="status-scanning">
                <span class="scan-pulse"></span>扫描中
              </span>
              <el-tag v-else-if="row.status === CONTRACT_STATUS_FAILED" type="danger" size="small" effect="light">失败</el-tag>
              <el-tag v-else type="success" size="small" effect="light">已完成</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="风险" width="210">
            <template #default="{ row }">
              <span v-if="row.status === CONTRACT_STATUS_SCANNING" class="risk-analyzing">AI + 规则分析中...</span>
              <span v-else-if="row.status === CONTRACT_STATUS_FAILED" class="risk-none">-</span>
              <template v-else>
                <el-tag type="danger" size="small">高 {{ row.high_count }}</el-tag>
                <el-tag type="warning" size="small" class="risk-tag">中 {{ row.medium_count }}</el-tag>
                <el-tag type="info" size="small" class="risk-tag">低 {{ row.low_count }}</el-tag>
              </template>
            </template>
          </el-table-column>
          <el-table-column label="上传时间" min-width="150">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="230" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === CONTRACT_STATUS_SCANNING">
                <el-button link type="primary" @click="openJobByContract(row)">进度</el-button>
              </template>
              <template v-else>
                <div class="row-actions">
                  <el-button v-if="row.status !== CONTRACT_STATUS_FAILED" link type="primary" @click="openReport(row.id)">报告</el-button>
                  <el-button v-if="row.status !== CONTRACT_STATUS_FAILED" link @click="openPreview(row)">预览</el-button>
                  <el-button link type="warning" @click="onRescan(row)">{{ row.status === CONTRACT_STATUS_FAILED ? '重新扫描' : '重扫' }}</el-button>
                  <el-button link type="danger" @click="onDelete(row)">删除</el-button>
                </div>
              </template>
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



      <!-- 扫描进度（后台任务：维度并发 + AI 流式） -->
      <el-dialog v-model="scanVisible" width="760px" top="6vh" @closed="onScanDialogClosed">
        <template #header>
          <div class="scan-dialog-head">
            <span class="scan-dialog-title">后台扫描进行中</span>
            <span class="scan-dialog-sub">关闭弹窗不影响扫描，任务在后台继续执行，可随时在列表查看进度</span>
          </div>
        </template>
        <ScanProgressPanel :job="scanJob" :stream-text="aiStreamText" />
      </el-dialog>
    </div>

    <el-drawer v-model="previewVisible" :title="previewName" size="56%" destroy-on-close>
      <div v-loading="previewLoading" class="preview-scroll">
        <pre class="preview-text">{{ previewText }}</pre>
      </div>
    </el-drawer>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search, UploadFilled } from '@element-plus/icons-vue'
import {
  deleteContract,
  getContractJob,
  getContractJobByContract,
  getContractJobStream,
  getContractPreview,
  listContracts,
  startContractRescan,
  startContractUpload,
} from '@/api/contract'
import type { Contract, ContractJob } from '@/api/contractTypes'
import { CONTRACT_STATUS_FAILED, CONTRACT_STATUS_SCANNING } from '@/api/contractTypes'
import AppLayout from '@/components/AppLayout.vue'
import ScanProgressPanel from '@/components/ScanProgressPanel.vue'

const router = useRouter()

/** 列表最高风险筛选下拉选项 */
const severityMap: Record<string, string> = {
  high: '含高风险',
  medium: '含中风险',
  low: '含低风险',
}

const loading = ref(false)
const items = ref<Contract[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const severity = ref('')

const uploading = ref(false)
const fileRef = ref<HTMLInputElement>()

const rescanning = ref(false)

const scanVisible = ref(false)
const scanJob = ref<ContractJob | null>(null)

// ===== 合同原文预览 =====
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewText = ref('')
const previewName = ref('')

async function openPreview(row: Contract) {
  previewVisible.value = true
  previewLoading.value = true
  previewName.value = row.file_name
  previewText.value = ''
  try {
    previewText.value = await getContractPreview(row.id)
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    previewLoading.value = false
  }
}
const currentJobId = ref('')
const aiStreamText = ref('')



const hasScanning = computed(() => items.value.some((c) => c.status === CONTRACT_STATUS_SCANNING))
let listTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  void loadList()
})

onBeforeUnmount(() => {
  if (listTimer) clearInterval(listTimer)
})

/** 存在后台扫描中的合同时，自动轮询列表刷新状态 */
watch(hasScanning, (scanning) => {
  if (listTimer) {
    clearInterval(listTimer)
    listTimer = null
  }
  if (scanning) {
    listTimer = setInterval(() => void loadList(true), 2500)
  }
})

async function loadList(silent = false) {
  if (!silent) loading.value = true
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
    if (!silent) ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  void loadList()
}

async function handleFile(file: File) {
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
    const { job_id: jobId } = await startContractUpload(file)
    await loadList()
    await pollJob(jobId)
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    uploading.value = false
  }
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  await handleFile(file)
}

/**
 * 轮询后台扫描任务：弹窗可随时关闭（扫描在后台继续），
 * 完成后提示 + 刷新列表，不强制打开详情。
 */
async function pollJob(jobId: string) {
  currentJobId.value = jobId
  aiStreamText.value = ''
  scanVisible.value = true
  scanJob.value = { status: 'running', progress: 0, stage: 'created', stage_message: '任务已创建' }
  while (currentJobId.value === jobId) {
    try {
      const job = await getContractJob(jobId)
      scanJob.value = job
      // AI 流式输出同步拉取（打字机效果）
      if (job.ai?.status === 'running') {
        try {
          aiStreamText.value = await getContractJobStream(jobId)
        } catch {
          /* 流尚未产生，忽略 */
        }
      }
      if (job.status === 'done') {
        try {
          aiStreamText.value = await getContractJobStream(jobId)
        } catch {
          /* ignore */
        }
        ElMessage.success(`扫描完成，识别到 ${job.risk_count ?? 0} 项风险`)
        await loadList()
        if (scanVisible.value && job.contract_id) {
          const cid = job.contract_id
          scanVisible.value = false
          await new Promise((r) => setTimeout(r, 250))
          openReport(cid)
        }
        currentJobId.value = ''
        return
      }
      if (job.status === 'failed') {
        ElMessage.error(job.error || job.stage_message || '扫描失败')
        await loadList()
        currentJobId.value = ''
        return
      }
    } catch (e) {
      // 任务记录过期（10 分钟 TTL）：静默退出并刷新列表
      currentJobId.value = ''
      await loadList()
      return
    }
    await new Promise((r) => setTimeout(r, 600))
  }
}

/** 从列表打开某合同的后台扫描进度 */
async function openJobByContract(row: Contract) {
  try {
    const job = await getContractJobByContract(row.id)
    aiStreamText.value = ''
    scanVisible.value = true
    scanJob.value = job
    if (job.status === 'running') {
      const tracking = job.job_id ?? ''
      currentJobId.value = tracking
      while (currentJobId.value === tracking) {
        await new Promise((r) => setTimeout(r, 600))
        try {
          const latest = await getContractJobByContract(row.id)
          scanJob.value = latest
          if (latest.ai?.status === 'running' && tracking) {
            try {
              aiStreamText.value = await getContractJobStream(tracking)
            } catch {
              /* ignore */
            }
          }
          if (latest.status !== 'running') {
            currentJobId.value = ''
            await loadList()
            if (latest.status === 'done') {
              ElMessage.success(`扫描完成，识别到 ${latest.risk_count ?? 0} 项风险`)
            }
            return
          }
        } catch {
          currentJobId.value = ''
          await loadList()
          return
        }
      }
    } else {
      // 已结束：仅展示最终状态
      await loadList()
    }
  } catch {
    ElMessage.info('该任务的进度记录已过期，请刷新列表查看结果')
    await loadList()
  }
}

/** 关闭进度弹窗：扫描继续在后台执行，列表自动轮询状态 */
function onScanDialogClosed() {
  if (scanJob.value?.status === 'running') {
    ElMessage.info('扫描已在后台继续，可随时在列表查看进度')
  }
  currentJobId.value = ''
}

/** 打开风险报告页 */
function openReport(id: number) {
  router.push({ name: 'contract-report', params: { id } })
}

async function onRescan(row: Contract) {
  rescanning.value = true
  try {
    const jobId = await startContractRescan(row.id)
    await loadList(true)
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
  flex-wrap: nowrap;
}
.upload-tip {
  font-size: 12.5px;
  color: #94a3b8;
  white-space: nowrap;
}
.row-actions {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
}
.row-actions .el-button {
  margin-left: 0;
  padding: 4px 6px;
}
.upload-zone {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 34px 20px;
  border-radius: 16px;
  border: 2px dashed rgba(37, 99, 235, 0.35);
  background:
    radial-gradient(420px 200px at 80% 0%, rgba(124, 58, 237, 0.06), transparent 60%),
    radial-gradient(420px 200px at 20% 100%, rgba(6, 182, 212, 0.07), transparent 60%),
    linear-gradient(160deg, #fbfdff, #f4f8ff);
  cursor: pointer;
  transition: all 0.25s ease;
  overflow: hidden;
}
.upload-zone::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(120deg, transparent 30%, rgba(37, 99, 235, 0.06) 50%, transparent 70%);
  transform: translateX(-100%);
  animation: zone-shine 4.5s ease-in-out infinite;
}
@keyframes zone-shine {
  0% { transform: translateX(-100%); }
  55%, 100% { transform: translateX(100%); }
}
.upload-zone:hover,
.upload-zone.dragging {
  border-color: #2563eb;
  background:
    radial-gradient(420px 200px at 80% 0%, rgba(124, 58, 237, 0.10), transparent 60%),
    radial-gradient(420px 200px at 20% 100%, rgba(6, 182, 212, 0.10), transparent 60%),
    linear-gradient(160deg, #f6f9ff, #eef4ff);
  box-shadow: 0 10px 30px rgba(37, 99, 235, 0.12);
}
.upload-zone-icon {
  display: block;
}
.upload-zone-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}
.upload-zone-title em {
  font-style: normal;
  color: #2563eb;
}
.upload-zone-tip {
  font-size: 12px;
  color: #94a3b8;
  letter-spacing: 0.4px;
}
.upload-zone-formats {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.upload-zone-formats .fmt {
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #2563eb;
  background: rgba(37, 99, 235, 0.08);
  border: 1px solid rgba(37, 99, 235, 0.16);
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
.status-scanning {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: #2563eb;
}
.scan-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2563eb;
  animation: pulse-dot 1.2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.35); }
  50% { box-shadow: 0 0 0 5px rgba(37, 99, 235, 0); }
}
.risk-analyzing {
  font-size: 12.5px;
  color: #7c3aed;
  font-weight: 600;
}
.risk-none {
  color: #94a3b8;
}
.scan-dialog-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.preview-scroll {
  height: calc(100vh - 120px);
  overflow-y: auto;
  border: 1px solid #eef1f6;
  border-radius: 12px;
  padding: 16px 18px;
  background: #fbfcfe;
}
.preview-text {
  margin: 0;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 13.5px;
  line-height: 2;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-all;
}
.scan-dialog-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.scan-dialog-sub {
  font-size: 12px;
  color: #94a3b8;
}
</style>