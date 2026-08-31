<template>
  <AppLayout>
    <div v-loading="loading" class="report-page">
      <!-- 顶部导航：返回按钮 + 报告标题 -->
      <div class="report-nav">
        <el-button class="back-btn" :icon="ArrowLeft" round @click="goBack">
          返回合同列表
        </el-button>
        <span v-if="detail" class="nav-title">{{ detail.contract.file_name }}</span>
        <div v-if="detail" class="nav-actions">
          <el-tag v-if="detail.risks.length" type="danger" size="small" effect="light" round>
            {{ detail.risks.length }} 项风险
          </el-tag>
          <el-button size="small" :icon="Download" @click="exportReport()">导出网页</el-button>
          <el-button size="small" :icon="View" @click="openPreview()">合同预览</el-button>
          <el-button type="warning" size="small" :loading="rescanning" @click="onRescan">
            重新扫描
          </el-button>
        </div>
      </div>

      <template v-if="detail">
        <!-- 报告概览（卡片 + 图标） -->
        <div class="report-overview">
          <div class="ov-card ov-total">
            <span class="ov-icon"><el-icon><DataAnalysis /></el-icon></span>
            <div class="ov-meta"><b>{{ detail.risks.length }}</b><span>总风险</span></div>
          </div>
          <div class="ov-card ov-high">
            <span class="ov-icon"><el-icon><WarningFilled /></el-icon></span>
            <div class="ov-meta"><b>{{ highCount }}</b><span>高风险</span></div>
          </div>
          <div class="ov-card ov-medium">
            <span class="ov-icon"><el-icon><Warning /></el-icon></span>
            <div class="ov-meta"><b>{{ mediumCount }}</b><span>中风险</span></div>
          </div>
          <div class="ov-card ov-low">
            <span class="ov-icon"><el-icon><InfoFilled /></el-icon></span>
            <div class="ov-meta"><b>{{ lowCount }}</b><span>低风险</span></div>
          </div>
          <div class="ov-card ov-conclusion-card" :class="'ov-' + riskLevel">
            <span class="ov-icon">
              <el-icon><CircleCheckFilled v-if="riskLevel === 'good'" /><InfoFilled v-else-if="riskLevel === 'ok'" /><Warning v-else-if="riskLevel === 'warn'" /><CircleCloseFilled v-else /></el-icon>
            </span>
            <div class="ov-meta"><b class="ov-conclusion-text">{{ riskConclusion }}</b></div>
          </div>
        </div>

        <!-- 图表：严重度分布 + 维度分布 -->
        <RiskReportCharts :risks="detail.risks" :total-chars="detail.contract.total_chars" />

        <!-- 维度筛选 -->
        <div class="dim-filter-bar">
          <button
            class="dim-chip"
            :class="{ active: !activeDim }"
            type="button"
            @click="activeDim = ''"
          >
            <el-icon class="dim-chip-icon"><Grid /></el-icon>
            全部维度
            <span class="chip-count">{{ detail.risks.length }}</span>
          </button>
          <button
            v-for="dim in dimensionSummary"
            :key="dim.key"
            class="dim-chip"
            :class="{ active: activeDim === dim.key }"
            type="button"
            @click="toggleDim(dim.key)"
          >
            <el-icon class="dim-chip-icon"><component :is="dimensionIconOf(dim.key)" /></el-icon>
            {{ dim.label }}
            <span class="chip-count">{{ dim.count }}</span>
          </button>
        </div>

        <!-- 无风险 -->
        <div v-if="detail.risks.length === 0" class="empty-report">
          <el-icon :size="40" color="#10b981"><circle-check /></el-icon>
          <p>未识别到风险，合同内容较规范。</p>
        </div>

        <!-- 风险明细（高→中→低排序；级别徽章 + 原文高亮 + 说明建议） -->
        <div v-for="group in visibleGroups" :key="group.key" class="risk-section">
          <div class="section-head">
            <span class="section-title">{{ group.label }}</span>
            <span class="section-count">
              {{ group.risks.length }} 项风险
              <span v-if="groupHighCount(group)" class="section-high">{{ groupHighCount(group) }} 项高风险</span>
            </span>
          </div>
          <div v-for="risk in group.risks" :key="risk.id" class="risk-card" :class="'risk-' + risk.severity">
            <div class="risk-head">
              <span class="sev-badge" :class="'sev-badge-' + risk.severity">
                <span class="sev-badge-icon"><component :is="severityIcon(risk.severity)" /></span>
                {{ severityMap[risk.severity] }}风险
              </span>
              <span class="risk-title">{{ risk.rule_name }}</span>
            </div>
            <div v-if="risk.snippet" class="risk-snippet">
              <span class="block-label">合同原文 <em class="snippet-hint">问题点已标色</em>
                <el-button v-if="risk.snippet_start !== null" link type="primary" size="small" class="locate-btn" @click="locateRisk(risk)">在合同中定位</el-button>
              </span>
              <p
                class="snippet-text"
                :class="hasKeywordHit(risk) ? '' : 'snippet-full-' + risk.severity"
              >
                <template v-for="(seg, i) in highlight(risk)" :key="i">
                  <mark v-if="seg.hit" class="kw-mark" :class="'mark-' + risk.severity">{{ seg.text }}</mark>
                  <template v-else>{{ seg.text }}</template>
                </template>
              </p>
            </div>
            <div class="risk-info-grid">
              <div class="risk-desc">
                <span class="block-label">风险说明</span>
                <p>{{ risk.description }}</p>
              </div>
              <div class="risk-suggest">
                <span class="block-label">处理建议</span>
                <p>{{ risk.suggestion }}</p>
              </div>
            </div>
          </div>
        </div>

      </template>
    </div>

    <!-- 合同原文预览（支持风险点局部定位） -->
    <el-drawer
      v-model="previewVisible"
      :title="detail?.contract.file_name || '合同预览'"
      size="56%"
      destroy-on-close
    >
      <div class="preview-toolbar">
        <el-button size="small" @click="clearFocus">清除定位</el-button>
        <span v-if="focusLabel" class="focus-label">{{ focusLabel }}</span>
      </div>
      <div v-loading="previewLoading" class="preview-scroll" ref="previewScrollRef">
        <pre class="preview-text"><template v-for="(seg, i) in previewSegments" :key="i"><mark v-if="seg.focus" class="preview-mark">{{ seg.text }}</mark><template v-else>{{ seg.text }}</template></template></pre>
      </div>
    </el-drawer>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  CircleCheck,
  CircleCheckFilled,
  CircleCloseFilled,
  Collection,
  Cpu,
  DataAnalysis,
  Document,
  Download,
  Grid,
  InfoFilled,
  Lock,
  Location,
  Management,
  Money,
  Service,
  Stamp,
  Tickets,
  User,
  Van,
  View,
  Warning,
  WarningFilled,
} from '@element-plus/icons-vue'
import { getContract, getContractPreview, startContractRescan } from '@/api/contract'
import type { ContractDetail, ContractRisk } from '@/api/contractTypes'
import AppLayout from '@/components/AppLayout.vue'
import RiskReportCharts from '@/components/RiskReportCharts.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const rescanning = ref(false)
const detail = ref<ContractDetail | null>(null)
const activeDim = ref('')

// ===== 合同预览 =====
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewText = ref('')
const previewScrollRef = ref<HTMLElement>()
const focusStart = ref<number | null>(null)
const focusEnd = ref<number | null>(null)
const focusLabel = ref('')

const previewSegments = computed(() => {
  if (focusStart.value === null || focusEnd.value === null) {
    return [{ text: previewText.value, focus: false }]
  }
  return [
    { text: previewText.value.slice(0, focusStart.value), focus: false },
    { text: previewText.value.slice(focusStart.value, focusEnd.value), focus: true },
    { text: previewText.value.slice(focusEnd.value), focus: false },
  ]
})

async function openPreview() {
  if (!detail.value) return
  previewVisible.value = true
  previewLoading.value = true
  clearFocus()
  try {
    previewText.value = await getContractPreview(detail.value.contract.id)
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    previewLoading.value = false
  }
}

function locateRisk(risk: ContractRisk) {
  const id = detail.value?.contract.id
  if (!id) return
  previewVisible.value = true
  previewLoading.value = true
  focusLabel.value = risk.rule_name
  focusStart.value = risk.snippet_start
  focusEnd.value = risk.snippet_end
  getContractPreview(id)
    .then((text) => {
      previewText.value = text
    })
    .catch((e) => ElMessage.error((e as Error).message))
    .finally(() => {
      previewLoading.value = false
      setTimeout(() => {
        previewScrollRef.value?.querySelector('.preview-mark')?.scrollIntoView({ block: 'center', behavior: 'smooth' })
      }, 120)
    })
}

function clearFocus() {
  focusStart.value = null
  focusEnd.value = null
  focusLabel.value = ''
}

const categoryMap: Record<string, string> = {
  project: '项目管理',
  technology: '技术风险',
  contract: '合同条款',
  general: '通用风险',
  subject: '主体与签署',
  payment: '付款与结算',
  delivery: '交付与验收',
  breach: '违约责任',
  ip: '知识产权',
  confidential: '保密与数据安全',
  dispute: '争议解决',
  tax: '税务与发票',
  warranty: '质保与售后',
  compliance: '合规审查',
}
const severityMap: Record<string, string> = { high: '高', medium: '中', low: '低' }
/* ===== 风险概览：计数 + 定性结论（不使用无依据的数字评分） ===== */
const highCount = computed(() => (detail.value?.risks ?? []).filter((r) => r.severity === 'high').length)
const mediumCount = computed(() => (detail.value?.risks ?? []).filter((r) => r.severity === 'medium').length)
const lowCount = computed(() => (detail.value?.risks ?? []).filter((r) => r.severity === 'low').length)
const riskLevel = computed<'good' | 'ok' | 'warn' | 'bad'>(() => {
  const h = highCount.value
  const m = mediumCount.value
  if (h === 0 && m === 0) return 'good'
  if (h === 0 && m <= 3) return 'ok'
  if (h <= 3) return 'warn'
  return 'bad'
})
const riskConclusion = computed(() => {
  switch (riskLevel.value) {
    case 'good':
      return '未发现明显风险，合同内容较规范，可正常签署'
    case 'ok':
      return '存在少量中低风险，建议修订相关条款后签署'
    case 'warn':
      return '存在高风险条款，建议谨慎处理并与对方协商修改'
    case 'bad':
      return '高风险条款较多，建议暂缓签署并咨询法务'
  }
})

/* ===== 维度摘要（开放维度：从风险结果动态聚合） ===== */
interface DimSummary {
  key: string
  label: string
  count: number
  high: number
  medium: number
  low: number
}
const dimensionSummary = computed<DimSummary[]>(() => {
  const counter = new Map<string, { high: number; medium: number; low: number }>()
  for (const risk of detail.value?.risks ?? []) {
    const entry = counter.get(risk.category) ?? { high: 0, medium: 0, low: 0 }
    if (risk.severity === 'high') entry.high += 1
    else if (risk.severity === 'medium') entry.medium += 1
    else entry.low += 1
    counter.set(risk.category, entry)
  }
  const dims = [...counter.entries()].map(([key, sev]) => ({
    key,
    label: categoryMap[key] ?? key,
    count: sev.high + sev.medium + sev.low,
    high: sev.high,
    medium: sev.medium,
    low: sev.low,
  }))
  // 排序：内置四维度在前（保持熟悉顺序），自定义维度按风险数降序
  const knownOrder = [
    'project', 'technology', 'contract', 'general',
    'subject', 'payment', 'delivery', 'breach', 'ip',
    'confidential', 'dispute', 'tax', 'warranty', 'compliance',
  ]
  return dims.sort((a, b) => {
    const ia = knownOrder.indexOf(a.key)
    const ib = knownOrder.indexOf(b.key)
    if (ia !== -1 && ib !== -1) return ia - ib
    if (ia !== -1) return -1
    if (ib !== -1) return 1
    return b.count - a.count
  })
})

const SEVERITY_RANK: Record<string, number> = { high: 0, medium: 1, low: 2 }

/** 组内风险按 高→中→低 排序 */
function sortRisks(risks: ContractRisk[]): ContractRisk[] {
  return [...risks].sort((a, b) => (SEVERITY_RANK[a.severity] ?? 3) - (SEVERITY_RANK[b.severity] ?? 3))
}

const visibleGroups = computed(() => {
  const dims = activeDim.value
    ? [activeDim.value]
    : dimensionSummary.value.map((d) => d.key)
  return dims
    .map((key) => ({
      key,
      label: categoryMap[key] ?? key,
      risks: sortRisks((detail.value?.risks ?? []).filter((r) => r.category === key)),
    }))
    .filter((g) => g.risks.length > 0)
    // 维度组之间也按最高严重度从高到低排列
    .sort((a, b) => (SEVERITY_RANK[a.risks[0]?.severity] ?? 3) - (SEVERITY_RANK[b.risks[0]?.severity] ?? 3))
})

function severityIcon(severity: string): Component {
  if (severity === 'high') return WarningFilled
  if (severity === 'medium') return Warning
  return InfoFilled
}

const dimensionIconMap: Record<string, Component> = {
  project: Management,
  technology: Cpu,
  contract: Document,
  general: Collection,
  subject: User,
  payment: Money,
  delivery: Van,
  breach: Warning,
  ip: Stamp,
  confidential: Lock,
  dispute: Location,
  tax: Tickets,
  warranty: Service,
  compliance: CircleCheck,
}
function dimensionIconOf(key: string): Component {
  return dimensionIconMap[key] ?? Collection
}

function groupHighCount(group: { risks: ContractRisk[] }): number {
  return group.risks.filter((r) => r.severity === 'high').length
}

/** 原文中是否存在可高亮的关键词命中（无命中时整段着色标注问题区域） */
function hasKeywordHit(risk: ContractRisk): boolean {
  return risk.matched_keywords.some((k) => k && risk.snippet.includes(k))
}

/** 维度筛选切换（再次点击已选维度 = 取消筛选，恢复全部） */
function toggleDim(key: string) {
  activeDim.value = activeDim.value === key ? '' : key
}

/* ===== 命中关键词高亮（图文结合核心） ===== */
interface Segment {
  text: string
  hit: boolean
}
function highlight(risk: ContractRisk): Segment[] {
  const keywords = risk.matched_keywords.filter((k) => k && risk.snippet.includes(k))
  if (!keywords.length) return [{ text: risk.snippet, hit: false }]
  const pattern = new RegExp(`(${keywords.map(escapeRegExp).join('|')})`, 'gi')
  return risk.snippet
    .split(pattern)
    .filter((part) => part)
    .map((part) => ({
      text: part,
      hit: keywords.some((k) => k.toLowerCase() === part.toLowerCase()),
    }))
}
function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/* ===== 数据加载与操作 ===== */
async function load() {
  const id = Number(route.params.id)
  if (!id) return
  loading.value = true
  try {
    detail.value = await getContract(id)
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

async function onRescan() {
  if (!detail.value) return
  rescanning.value = true
  try {
    const jobId = await startContractRescan(detail.value.contract.id)
    ElMessage.info('重新扫描已加入后台任务')
    router.push({ name: 'contracts' })
    void jobId
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    rescanning.value = false
  }
}

function goBack() {
  router.push({ name: 'contracts' })
}

/* ===== 原样导出报告（自包含可点击 HTML） ===== */
function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

const dimensionEmoji: Record<string, string> = {
  project: '📐', technology: '💻', contract: '📄', general: '📋',
  subject: '🏢', payment: '💰', delivery: '🚚', breach: '🚨',
  ip: '📑', confidential: '🔒', dispute: '⚖️', tax: '🧾',
  warranty: '🛡️', compliance: '✅',
}
const severityEmoji: Record<string, string> = { high: '🔴', medium: '🟠', low: '🟢' }
const sevLabel: Record<string, string> = { high: '高风险', medium: '中风险', low: '低风险' }
const dimensionColor: Record<string, string> = {
  project: '#7b9ac7', technology: '#7fb3ae', contract: '#8e9bb8', general: '#9aa4ae',
  subject: '#a391bd', payment: '#8fbc9a', delivery: '#d2a277', breach: '#cf9595',
  ip: '#bd9cbf', confidential: '#88b1cf', dispute: '#b19c8c', tax: '#8eb8a6',
  warranty: '#86a8d4', compliance: '#97c29a',
}

function exportReport() {
  if (!detail.value) return
  const { contract, risks } = detail.value
  const total = risks.length
  const exportedAt = new Date().toLocaleString('zh-CN')
  const conclusion = riskConclusion.value

  const groups = dimensionSummary.value
    .map((dim) => ({
      key: dim.key,
      label: dim.label,
      risks: sortRisks(risks.filter((r) => r.category === dim.key)),
    }))
    .filter((g) => g.risks.length > 0)

  const maxDim = Math.max(1, ...groups.map((g) => g.risks.length))

  const sevBars = (['high', 'medium', 'low'] as const)
    .map((s) => {
      const n = s === 'high' ? highCount.value : s === 'medium' ? mediumCount.value : lowCount.value
      const pct = total ? Math.round((n / total) * 100) : 0
      return `<div class="bar-row"><span class="bar-label">${severityEmoji[s]} ${sevLabel[s]}</span><span class="bar-track"><span class="bar-fill sev-${s}" style="width:${pct}%"></span></span><span class="bar-val">${n}</span></div>`
    })
    .join('')

  const dimBars = groups
    .map((g) => {
      const pct = Math.round((g.risks.length / maxDim) * 100)
      const color = dimensionColor[g.key] ?? '#a6adb4'
      return `<div class="bar-row"><span class="bar-label">${dimensionEmoji[g.key] ?? '📌'} ${escapeHtml(g.label)}</span><span class="bar-track"><span class="bar-fill" style="width:${pct}%;background:${color}"></span></span><span class="bar-val">${g.risks.length}</span></div>`
    })
    .join('')

  const filterChips = groups
    .map((g) => `<button class="filter-btn" data-dim="${escapeHtml(g.key)}">${dimensionEmoji[g.key] ?? '📌'} ${escapeHtml(g.label)}<span class="chip-n">${g.risks.length}</span></button>`)
    .join('')

  const riskSections = groups
    .map((g) => {
      const cards = g.risks
        .map((r) => {
          const sev = r.severity
          const snippetBlock = r.snippet
            ? `<div class="block"><div class="block-title">📄 合同原文</div><pre class="snippet">${escapeHtml(r.snippet)}</pre></div>`
            : ''
          const descBlock = r.description
            ? `<div class="block"><div class="block-title">💡 风险说明</div><p>${escapeHtml(r.description)}</p></div>`
            : ''
          const sugBlock = r.suggestion
            ? `<div class="block suggest"><div class="block-title">✅ 处理建议</div><p>${escapeHtml(r.suggestion)}</p></div>`
            : ''
          return `<div class="risk-card" data-sev="${sev}"><div class="risk-head"><span class="badge sev-${sev}">${severityEmoji[sev] ?? ''} ${sevLabel[sev] ?? sev}</span><span class="risk-title">${escapeHtml(r.rule_name)}</span><span class="fold-icon">▾</span></div><div class="risk-body">${snippetBlock}${descBlock}${sugBlock}</div></div>`
        })
        .join('')
      return `<section class="risk-group" data-dim="${escapeHtml(g.key)}"><h2 class="group-title">${dimensionEmoji[g.key] ?? '📌'} ${escapeHtml(g.label)}<span class="group-n">${g.risks.length} 项</span></h2>${cards}</section>`
    })
    .join('')

  const overview = `
  <div class="stat total"><span class="stat-ico">📋</span><div><b>${total}</b><span>总风险</span></div></div>
  <div class="stat high"><span class="stat-ico">🔴</span><div><b>${highCount.value}</b><span>高风险</span></div></div>
  <div class="stat medium"><span class="stat-ico">🟠</span><div><b>${mediumCount.value}</b><span>中风险</span></div></div>
  <div class="stat low"><span class="stat-ico">🟢</span><div><b>${lowCount.value}</b><span>低风险</span></div></div>
  <div class="conclusion">${escapeHtml(conclusion)}</div>`

  const css = `*{box-sizing:border-box}
body{margin:0;font-family:'PingFang SC','Microsoft YaHei',sans-serif;background:#f4f6fb;color:#0f172a;-webkit-text-size-adjust:100%}
.wrap{max-width:1080px;margin:0 auto;padding:24px 20px 60px}
header{background:#fff;border:1px solid #eef1f6;border-radius:16px;padding:20px 24px;margin-bottom:16px}
header h1{margin:0 0 8px;font-size:20px;line-height:1.4}
header .meta{font-size:13px;color:#64748b}
.overview{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.stat{display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:12px;background:#fff;border:1px solid #eef1f6}
.stat .stat-ico{font-size:22px;line-height:1}
.stat b{font-size:22px;font-weight:800;display:block;line-height:1.1}
.stat span{display:block;font-size:12px;color:#64748b;margin-top:2px}
.stat.total b{color:#0f172a}.stat.high b{color:#dc2626}.stat.medium b{color:#b45309}.stat.low b{color:#047857}
.conclusion{flex:1;min-width:220px;display:flex;align-items:center;padding:12px 18px;border-radius:12px;background:#eef2ff;color:#1d4ed8;font-weight:700;font-size:13px;line-height:1.6}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
.chart-card{background:#fff;border:1px solid #eef1f6;border-radius:14px;padding:14px 16px}
.chart-card h3{margin:0 0 12px;font-size:13px;color:#334155}
.bar-row{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.bar-label{width:132px;font-size:12px;color:#475569;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-track{flex:1;height:10px;border-radius:999px;background:#eef2f7;overflow:hidden}
.bar-fill{display:block;height:100%;border-radius:999px}
.sev-high{background:#ef4444}.sev-medium{background:#f59e0b}.sev-low{background:#10b981}
.bar-fill.dim{background:linear-gradient(90deg,#2563eb,#7c3aed)}
.bar-val{width:30px;text-align:right;font-size:12px;font-weight:700;color:#0f172a}
.toolbar{display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
.toolbar button,.filter-btn{border:1px solid #e2e8f0;background:#fff;color:#475569;border-radius:999px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer}
.toolbar button:hover,.filter-btn:hover{border-color:#2563eb;color:#2563eb}
.filter-bar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}
.filter-btn.active{background:linear-gradient(120deg,#2563eb,#7c3aed);color:#fff;border-color:transparent}
.chip-n{display:inline-block;min-width:20px;padding:0 5px;border-radius:999px;background:rgba(100,116,139,.15);font-size:11px;font-weight:700;margin-left:6px;text-align:center}
.filter-btn.active .chip-n{background:rgba(255,255,255,.3)}
.risk-group{margin-bottom:24px}
.group-title{font-size:16px;font-weight:800;margin:0 0 12px;padding-bottom:8px;border-bottom:2px solid #eef1f6}
.group-n{margin-left:8px;font-size:12px;font-weight:600;color:#94a3b8}
.risk-card{background:#fff;border:1px solid #e8edf5;border-left:5px solid #cbd5e1;border-radius:12px;margin-bottom:10px;overflow:hidden}
.risk-card[data-sev="high"]{border-left-color:#ef4444}
.risk-card[data-sev="medium"]{border-left-color:#f59e0b}
.risk-card[data-sev="low"]{border-left-color:#10b981}
.risk-head{display:flex;align-items:center;gap:10px;padding:14px 16px;cursor:pointer;user-select:none}
.risk-title{font-size:14.5px;font-weight:700;flex:1;line-height:1.5}
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:800;flex-shrink:0}
.badge.sev-high{color:#dc2626;background:rgba(239,68,68,.1)}
.badge.sev-medium{color:#b45309;background:rgba(245,158,11,.12)}
.badge.sev-low{color:#047857;background:rgba(16,185,129,.1)}
.fold-icon{color:#94a3b8;transition:transform .2s;flex-shrink:0}
.risk-card.open .fold-icon{transform:rotate(180deg)}
.risk-body{display:none;padding:0 16px 14px}
.risk-card.open .risk-body{display:block}
.block{margin-bottom:12px}
.block-title{font-size:11.5px;font-weight:800;color:#94a3b8;letter-spacing:1px;margin-bottom:6px}
.snippet{margin:0;padding:12px 14px;border-radius:10px;background:#f8fafc;border:1px solid #eef2f7;border-left:3px solid #cbd5e1;font-size:13px;line-height:1.9;color:#334155;white-space:pre-wrap;word-break:break-all;font-family:inherit}
.block p{margin:0;font-size:13px;line-height:1.8;color:#475569}
.block.suggest{padding:10px 14px;border-radius:10px;background:rgba(37,99,235,.05);border:1px dashed rgba(37,99,235,.3)}
.block.suggest p{color:#1e40af}
@media(max-width:760px){.charts{grid-template-columns:1fr}.bar-label{width:96px}}`

  const script = `(function(){var btns=Array.prototype.slice.call(document.querySelectorAll('.filter-btn'));btns.forEach(function(btn){btn.addEventListener('click',function(){var dim=btn.getAttribute('data-dim');btns.forEach(function(b){b.classList.remove('active')});btn.classList.add('active');var groups=document.querySelectorAll('.risk-group');Array.prototype.forEach.call(groups,function(g){g.style.display=(dim==='all'||g.getAttribute('data-dim')===dim)?'':'none'})})});Array.prototype.forEach.call(document.querySelectorAll('.risk-head'),function(head){head.addEventListener('click',function(){head.parentElement.classList.toggle('open')})});var ea=document.getElementById('expand-all');if(ea)ea.addEventListener('click',function(){Array.prototype.forEach.call(document.querySelectorAll('.risk-card'),function(c){c.classList.add('open')})});var ca=document.getElementById('collapse-all');if(ca)ca.addEventListener('click',function(){Array.prototype.forEach.call(document.querySelectorAll('.risk-card'),function(c){c.classList.remove('open')})})})();`

  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escapeHtml(contract.file_name)} 合同风险报告</title>
<style>${css}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>${escapeHtml(contract.file_name)} 合同风险报告</h1>
    <div class="meta">导出时间：${escapeHtml(exportedAt)} · 风险总数 ${total} 项（高风险 ${highCount.value} / 中风险 ${mediumCount.value} / 低风险 ${lowCount.value}）</div>
  </header>
  <div class="overview">${overview}</div>
  <div class="charts">
    <div class="chart-card"><h3>🔻 风险级别分布</h3>${sevBars}</div>
    <div class="chart-card"><h3>🧩 风险维度分布</h3>${dimBars}</div>
  </div>
  <div class="toolbar"><button id="expand-all">全部展开</button><button id="collapse-all">全部收起</button></div>
  <div class="filter-bar"><button class="filter-btn active" data-dim="all">📌 全部维度<span class="chip-n">${total}</span></button>${filterChips}</div>
  ${riskSections}
</div>
<script>${script}<\/script>
</body>
</html>`

  const base = contract.file_name.replace(/\.[^.]+$/, '') || '合同'
  downloadText(`${base}_风险报告.html`, html)
  ElMessage.success('报告已导出为网页')
}

function downloadText(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<style scoped>
.report-page {
  width: 100%;
}

/* ===== 顶部返回导航（粘性） ===== */
.report-nav {
  position: sticky;
  top: 60px; /* 避开全局顶栏高度 */
  z-index: 15;
  display: flex;
  align-items: center;
  gap: 14px;
  margin: -24px -24px 20px;
  padding: 12px 24px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #eef1f6;
}
.back-btn {
  flex-shrink: 0;
}
.nav-title {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nav-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* ===== 报告概览（卡片 + 图标） ===== */
.report-overview {
  display: flex;
  align-items: stretch;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.ov-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #eef1f6;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
}
.ov-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.ov-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.ov-meta b {
  font-size: 20px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: #0f172a;
}
.ov-meta span {
  font-size: 12px;
  color: #64748b;
}
.ov-total .ov-icon { background: rgba(100, 116, 139, 0.1); color: #475569; }
.ov-high .ov-icon { background: rgba(239, 68, 68, 0.1); color: #dc2626; }
.ov-medium .ov-icon { background: rgba(245, 158, 11, 0.12); color: #b45309; }
.ov-low .ov-icon { background: rgba(16, 185, 129, 0.1); color: #047857; }
.ov-conclusion-card { flex: 1; min-width: 240px; }
.ov-conclusion-card .ov-icon { background: rgba(37, 99, 235, 0.1); color: #2563eb; }
.ov-conclusion-card .ov-meta b { font-size: 13px; font-weight: 700; color: #1d4ed8; }
.ov-good { color: #047857; }
.ov-ok { color: #1d4ed8; }
.ov-warn { color: #b45309; }
.ov-bad { color: #b91c1c; }
.ov-conclusion-card.ov-good .ov-icon { background: rgba(16, 185, 129, 0.1); color: #047857; }
.ov-conclusion-card.ov-good .ov-meta b { color: #047857; }
.ov-conclusion-card.ov-warn .ov-icon { background: rgba(245, 158, 11, 0.12); color: #b45309; }
.ov-conclusion-card.ov-warn .ov-meta b { color: #b45309; }
.ov-conclusion-card.ov-bad .ov-icon { background: rgba(239, 68, 68, 0.1); color: #b91c1c; }
.ov-conclusion-card.ov-bad .ov-meta b { color: #b91c1c; }

/* ===== 维度筛选条 ===== */
.dim-filter-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.dim-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 16px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}
.dim-chip:hover {
  border-color: rgba(37, 99, 235, 0.4);
  color: #2563eb;
}
.dim-chip.active {
  border-color: transparent;
  color: #fff;
  background: linear-gradient(120deg, #2563eb, #7c3aed);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.28);
}
.chip-count {
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11.5px;
  font-weight: 700;
  background: rgba(100, 116, 139, 0.12);
  color: inherit;
}
.dim-chip.active .chip-count {
  background: rgba(255, 255, 255, 0.25);
}
.dim-chip-icon {
  font-size: 14px;
}

/* ===== 空报告 ===== */
.empty-report {
  padding: 60px 0;
  text-align: center;
  color: #059669;
  font-size: 14px;
}

/* ===== 风险明细 ===== */
.risk-section {
  margin-bottom: 30px;
}
.section-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 2px solid #eef1f6;
}
.section-title {
  font-size: 17px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: 0.5px;
}
.section-count {
  font-size: 12.5px;
  color: #94a3b8;
}
.section-high {
  margin-left: 8px;
  padding: 1px 8px;
  border-radius: 999px;
  font-weight: 700;
  color: #dc2626;
  background: rgba(239, 68, 68, 0.09);
}

/* 风险卡片：级别色氛围 + 左侧色条 */
.risk-card {
  padding: 18px 22px;
  margin-bottom: 14px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #e8edf5;
  border-left: 5px solid #cbd5e1;
  transition: all 0.2s ease;
}
.risk-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
}
.risk-high {
  border-left-color: #ef4444;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.035), #fff 40%);
}
.risk-medium {
  border-left-color: #f59e0b;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.045), #fff 40%);
}
.risk-low {
  border-left-color: #10b981;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.04), #fff 40%);
}

/* 卡片头：级别徽章 + 序号 + 标题 */
.risk-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.sev-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px 4px 6px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 800;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}
.sev-badge-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 900;
  color: #fff;
}
.sev-badge-high {
  color: #dc2626;
  background: rgba(239, 68, 68, 0.1);
}
.sev-badge-high .sev-badge-icon { background: #ef4444; }
.sev-badge-medium {
  color: #b45309;
  background: rgba(245, 158, 11, 0.12);
}
.sev-badge-medium .sev-badge-icon { background: #f59e0b; }
.sev-badge-low {
  color: #047857;
  background: rgba(16, 185, 129, 0.1);
}
.sev-badge-low .sev-badge-icon { background: #10b981; }
.sev-badge-icon svg {
  width: 11px;
  height: 11px;
}
.risk-index {
  font-size: 12px;
  font-weight: 800;
  color: #cbd5e1;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.risk-title {
  font-size: 15.5px;
  font-weight: 800;
  color: #0f172a;
}

/* 命中关键词 */
.risk-keywords {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
}
.kw-label {
  font-size: 11.5px;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 1px;
}
.kw {
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #7c3aed;
  background: rgba(124, 58, 237, 0.09);
  border: 1px solid rgba(124, 58, 237, 0.16);
}

/* 合同原文引用块 */
.risk-snippet {
  margin-top: 12px;
}
.block-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 6px;
  font-size: 11.5px;
  font-weight: 800;
  color: #94a3b8;
  letter-spacing: 1.5px;
}
.block-label::before {
  content: '';
  width: 3px;
  height: 11px;
  border-radius: 2px;
  background: linear-gradient(180deg, #2563eb, #7c3aed);
}
.snippet-text {
  margin: 0;
  padding: 12px 14px 12px 16px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-left: 3px solid #cbd5e1;
  font-size: 13px;
  line-height: 1.9;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-all;
}
.risk-high .snippet-text { border-left-color: rgba(239, 68, 68, 0.5); }
.risk-medium .snippet-text { border-left-color: rgba(245, 158, 11, 0.55); }
.risk-low .snippet-text { border-left-color: rgba(16, 185, 129, 0.5); }
.snippet-hint {
  margin-left: 8px;
  font-size: 11px;
  font-style: normal;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 0.5px;
}
.kw-mark {
  padding: 0 4px;
  border-radius: 4px;
  font-weight: 700;
}
.mark-high {
  background: rgba(239, 68, 68, 0.16);
  color: #b91c1c;
  box-shadow: inset 0 -2px 0 rgba(239, 68, 68, 0.55);
}
.mark-medium {
  background: rgba(245, 158, 11, 0.18);
  color: #b45309;
  box-shadow: inset 0 -2px 0 rgba(245, 158, 11, 0.5);
}
.mark-low {
  background: rgba(16, 185, 129, 0.15);
  color: #047857;
  box-shadow: inset 0 -2px 0 rgba(16, 185, 129, 0.5);
}
/* 无关键词命中（如 AI 语义识别）：整段按级别着色，标注问题区域 */
.snippet-full-high {
  background: rgba(239, 68, 68, 0.06);
  border-left-color: #ef4444;
}
.snippet-full-medium {
  background: rgba(245, 158, 11, 0.07);
  border-left-color: #f59e0b;
}
.snippet-full-low {
  background: rgba(16, 185, 129, 0.06);
  border-left-color: #10b981;
}

/* 说明 + 建议 双栏 */
.risk-info-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.risk-desc p,
.risk-suggest p {
  margin: 0;
  font-size: 13px;
  line-height: 1.85;
}
.risk-desc p {
  color: #475569;
}
.risk-suggest {
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.05);
  border: 1px dashed rgba(37, 99, 235, 0.3);
}
.risk-suggest .block-label {
  color: #2563eb;
}
.risk-suggest .block-label::before {
  background: linear-gradient(180deg, #2563eb, #06b6d4);
}
.risk-suggest p {
  color: #1e40af;
}

.locate-btn {
  margin-left: 6px;
}
.preview-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.focus-label {
  font-size: 12.5px;
  color: #b45309;
  font-weight: 600;
}
.preview-scroll {
  height: calc(100vh - 140px);
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
.preview-mark {
  padding: 1px 3px;
  border-radius: 4px;
  background: rgba(245, 158, 11, 0.25);
  color: #b45309;
  font-weight: 700;
  box-shadow: inset 0 -2px 0 rgba(245, 158, 11, 0.5);
}

@media (max-width: 900px) {
  .risk-info-grid { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .risk-info-grid { grid-template-columns: 1fr; }
}
/* ===== 底部操作 ===== */
.report-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding: 26px 0 10px;
}

@media (max-width: 900px) {
  .report-hero { flex-direction: column; align-items: flex-start; }
  .hero-overview { width: 100%; }
  .dim-grid { grid-template-columns: repeat(2, 1fr) !important; }
  .risk-item { flex-direction: column; gap: 10px; }
  .risk-side { flex-direction: row; }
  .nav-title { display: none; }
  .report-nav { margin: -24px -24px 14px; }
}
</style>
