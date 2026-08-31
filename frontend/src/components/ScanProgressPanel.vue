<template>
  <div class="scan-progress">
    <!-- 总进度 -->
    <div class="progress-head">
      <div class="progress-title">
        <span class="stage-text">{{ job?.stage_message || '正在启动任务...' }}</span>
        <span v-if="job?.status === 'running'" class="scan-dots"><i></i><i></i><i></i></span>
        <el-icon v-else-if="job?.status === 'done'" class="done-icon"><circle-check /></el-icon>
        <el-icon v-else-if="job?.status === 'failed'" class="fail-icon"><circle-close /></el-icon>
      </div>
      <el-progress
        :percentage="job?.progress ?? 0"
        :stroke-width="8"
        :show-text="false"
        :color="progressColors"
      />
    </div>

    <!-- 维度并发任务卡片（开放维度：按任务清单动态渲染） -->
    <div class="task-grid">
      <div v-if="!categoryKeys.length" class="task-empty">
        正在分析规则维度...
      </div>
      <div
        v-for="cat in categoryKeys"
        :key="cat"
        class="task-card"
        :class="[taskStatus(cat)]"
      >
        <div class="task-head">
          <span class="task-dot"></span>
          <span class="task-label">{{ taskLabel(cat) }}</span>
        </div>
        <div class="task-meta">
          <template v-if="taskStatus(cat) === 'done'">
            <span class="task-hits">{{ taskHits(cat) }} 项风险</span>
            <span class="task-rules">{{ taskRuleCount(cat) }} 条规则</span>
          </template>
          <template v-else-if="taskStatus(cat) === 'running'">
            <span class="task-running">扫描中</span>
            <span class="task-rules">{{ taskRuleCount(cat) }} 条规则</span>
          </template>
          <template v-else>
            <span class="task-waiting">排队中</span>
          </template>
        </div>
      </div>
    </div>

    <!-- 逐条规则理解 + 并发校验（每条规则一个 AI 任务） -->
    <div v-if="ruleChecks.length" class="rule-check-panel">
      <div class="rc-head">
        <span class="rc-title">规则理解与并发校验</span>
        <span class="rc-count">已完成 {{ ruleChecks.filter(r => ['matched','clean','failed'].includes(r.status)).length }} / {{ ruleChecks.length }} 条</span>
      </div>
      <div class="rc-grid">
        <div
          v-for="rc in ruleChecks"
          :key="rc.code"
          class="rc-item"
          :class="'rc-' + rc.status"
        >
          <span class="rc-dot"></span>
          <span class="rc-status">
            {{ rcStatusText(rc) }}
          </span>
          <span v-if="rc.detail" class="rc-text" :title="rc.detail">{{ rc.detail }}</span>
        </div>
      </div>
    </div>

    <!-- AI 流式分析 -->
    <div class="ai-panel" :class="[aiStatus]">
      <div class="ai-head">
        <span class="ai-badge">AI</span>
        <span class="ai-title">大模型深度分析</span>
        <span class="ai-state">
          <template v-if="aiStatus === 'running'"><span class="scan-dots small"><i></i><i></i><i></i></span> 实时输出中</template>
          <template v-else-if="aiStatus === 'done'">✓ 完成 · {{ job?.ai?.findings ?? 0 }} 项语义风险</template>
          <template v-else-if="aiStatus === 'skipped'">未启用（纯规则识别）</template>
          <template v-else-if="aiStatus === 'failed'">已降级（纯规则识别）</template>
          <template v-else>等待启动</template>
        </span>
      </div>
      <div v-if="streamText" ref="streamRef" class="ai-stream">
        <div class="ai-analysis">
          <p
            v-for="(line, i) in analysisLines"
            :key="i"
            class="analysis-line"
            :class="{ 'is-heading': line.heading, 'is-empty': !line.text }"
          >
            {{ line.text }}
          </p>
          <span v-if="aiStatus === 'running' && !resultStarted" class="cursor">▍</span>
        </div>
        <div v-if="resultStarted" class="result-hint">
          <span class="scan-dots small" v-if="aiStatus === 'running'"><i></i><i></i><i></i></span>
          {{ aiStatus === 'running' ? '正在生成结构化风险清单（用于落库，已自动折叠）' : '结构化风险清单已生成，见最终报告' }}
        </div>
      </div>
    </div>

    <!-- 事件时间线 -->
    <div class="timeline">
      <div class="timeline-title">执行日志</div>
      <div ref="logRef" class="timeline-body">
        <div
          v-for="(ev, i) in job?.events || []"
          :key="i"
          class="timeline-line"
          :class="{ error: ev.level === 'error' }"
        >
          <span class="tl-time">{{ ev.time }}</span>
          <span class="tl-dot"></span>
          <span class="tl-msg">{{ ev.message }}</span>
        </div>
      </div>
    </div>

    <div v-if="job?.status === 'failed'" class="scan-error">
      {{ job.error || job.stage_message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { CircleCheck, CircleClose } from '@element-plus/icons-vue'
import type { ContractJob } from '@/api/contractTypes'

const props = defineProps<{
  job: ContractJob | null
  streamText: string
}>()

/** 维度清单为开放格式：从任务状态动态获取 */
const categoryKeys = computed<string[]>(() => Object.keys(props.job?.tasks ?? {}))

/** 逐条规则校验状态（按后端写入顺序展示） */
const ruleChecks = computed(() => Object.values(props.job?.rule_checks ?? {}))

function rcStatusText(rc: { status: string; detail: string }): string {
  switch (rc.status) {
    case 'pending':
      return '待校验'
    case 'running':
      return '校验中…'
    case 'matched':
      return '⚠ 命中风险'
    case 'clean':
      return '✓ 无风险'
    case 'failed':
      return '⚠ 降级匹配'
    default:
      return rc.status
  }
}
const progressColors = [
  { color: '#2563eb', percentage: 55 },
  { color: '#7c3aed', percentage: 90 },
  { color: '#10b981', percentage: 100 },
]

const streamRef = ref<HTMLDivElement>()
const logRef = ref<HTMLDivElement>()

const aiStatus = computed(() => props.job?.ai?.status ?? '')

const RESULT_MARKERS = ['== 结果 ==', '==结果==']

/** 流式输出拆分：结果标记之前 = 可读分析思路 */
const analysisPart = computed(() => {
  const text = props.streamText
  for (const marker of RESULT_MARKERS) {
    const index = text.indexOf(marker)
    if (index !== -1) return text.slice(0, index)
  }
  return text
})
const resultStarted = computed(() => RESULT_MARKERS.some((m) => props.streamText.includes(m)))

interface AnalysisLine {
  text: string
  heading: boolean
}
/** 简单排版：识别标题行（含“分析”“结论”或短小粗体行）与条目行 */
const analysisLines = computed<AnalysisLine[]>(() => {
  return analysisPart.value
    .split('\n')
    .map((raw) => raw.trim())
    .filter((raw, i, arr) => !(raw === '' && arr[i - 1] === ''))
    .map((raw) => ({
      text: raw.replace(/^==\s*分析\s*==$/, '分析思路'),
      heading:
        /(^|=)\s*(分析|整体结论|总体结论|综合结论)/.test(raw) && raw.length < 24,
    }))
})

function taskStatus(cat: string) {
  return props.job?.tasks?.[cat]?.status ?? 'pending'
}
function taskLabel(cat: string) {
  return props.job?.tasks?.[cat]?.label ?? cat
}
function taskHits(cat: string) {
  return props.job?.tasks?.[cat]?.hits ?? 0
}
function taskRuleCount(cat: string) {
  return props.job?.tasks?.[cat]?.rule_count ?? 0
}

watch(
  () => props.streamText,
  () => {
    streamRef.value?.scrollTo({ top: streamRef.value.scrollHeight })
  },
)
watch(
  () => props.job?.events?.length,
  () => {
    logRef.value?.scrollTo({ top: logRef.value.scrollHeight })
  },
)
</script>

<style scoped>
.scan-progress {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 总进度 */
.progress-head {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.progress-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: #1e3a8a;
}
.done-icon { color: #10b981; font-size: 18px; }
.fail-icon { color: #ef4444; font-size: 18px; }

/* 维度任务卡 */
.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}
.task-empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 14px;
  font-size: 12.5px;
  color: #94a3b8;
}
.task-card {
  border-radius: 12px;
  border: 1px solid #e8edf5;
  background: #fbfcfe;
  padding: 12px;
  transition: all 0.25s ease;
}
.task-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
}
.task-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cbd5e1;
  flex-shrink: 0;
}
.task-card.running .task-dot {
  background: #2563eb;
  animation: pulse-dot 1.2s ease-in-out infinite;
}
.task-card.done .task-dot {
  background: #10b981;
}
@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.35); }
  50% { box-shadow: 0 0 0 5px rgba(37, 99, 235, 0); }
}
.task-label {
  font-size: 12.5px;
  font-weight: 700;
  color: #334155;
}
.task-card.running {
  border-color: rgba(37, 99, 235, 0.4);
  background: rgba(37, 99, 235, 0.05);
}
.task-card.done {
  border-color: rgba(16, 185, 129, 0.35);
  background: rgba(16, 185, 129, 0.05);
}
.task-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
}
.task-hits { color: #ef4444; font-weight: 700; }
.task-rules { color: #94a3b8; }
.task-running { color: #2563eb; font-weight: 600; }
.task-waiting { color: #94a3b8; }

/* AI 面板 */
.rule-check-panel {
  border-radius: 12px;
  border: 1px solid #e8edf5;
  background: #fff;
  overflow: hidden;
}
.rc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  background: linear-gradient(90deg, rgba(6, 182, 212, 0.06), rgba(37, 99, 235, 0.04));
  border-bottom: 1px solid #eef1f6;
}
.rc-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}
.rc-count {
  font-size: 12px;
  color: #64748b;
}
.rc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px;
  padding: 12px 14px;
  max-height: 220px;
  overflow-y: auto;
}
.rc-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 9px;
  background: #fbfcfe;
  border: 1px solid #eef1f6;
  font-size: 12px;
  transition: all 0.2s ease;
}
.rc-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #cbd5e1;
}
.rc-running .rc-dot {
  background: #2563eb;
  animation: pulse-dot 1.2s ease-in-out infinite;
}
.rc-matched .rc-dot { background: #ef4444; }
.rc-matched { border-color: rgba(239, 68, 68, 0.35); background: rgba(239, 68, 68, 0.05); }
.rc-clean .rc-dot { background: #10b981; }
.rc-failed .rc-dot { background: #f59e0b; }
.rc-text {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}
.rc-status {
  margin-left: auto;
  font-weight: 600;
  white-space: nowrap;
  color: #475569;
  flex-shrink: 0;
}
.rc-matched .rc-status { color: #dc2626; }
.rc-clean .rc-status { color: #059669; }
.rc-failed .rc-status { color: #b45309; }
@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.35); }
  50% { box-shadow: 0 0 0 5px rgba(37, 99, 235, 0); }
}

.ai-panel {
  border-radius: 12px;
  border: 1px solid #e8edf5;
  background: #fff;
  overflow: hidden;
}
.ai-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.06), rgba(124, 58, 237, 0.06));
  border-bottom: 1px solid #eef1f6;
}
.ai-badge {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #fff;
  background: linear-gradient(120deg, #2563eb, #7c3aed);
}
.ai-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}
.ai-state {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}
.ai-panel.done .ai-state { color: #10b981; }
.ai-panel.failed .ai-state { color: #f59e0b; }
.ai-stream {
  max-height: 240px;
  overflow-y: auto;
  padding: 12px 14px;
  background: #fbfcff;
}
.ai-analysis {
  font-size: 13px;
  line-height: 1.9;
  color: #334155;
}
.analysis-line {
  margin: 0 0 4px;
  word-break: break-all;
}
.analysis-line.is-heading {
  font-weight: 700;
  color: #1d4ed8;
}
.analysis-line.is-empty {
  height: 6px;
}
.result-hint {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(124, 58, 237, 0.06);
  border: 1px dashed rgba(124, 58, 237, 0.25);
  color: #6d28d9;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.cursor {
  color: #2563eb;
  animation: blink 1s step-end infinite;
}
@keyframes blink {
  50% { opacity: 0; }
}

/* 时间线 */
.timeline {
  border-radius: 12px;
  border: 1px solid #e8edf5;
  background: #fff;
}
.timeline-title {
  padding: 10px 14px;
  font-size: 12.5px;
  font-weight: 700;
  color: #334155;
  border-bottom: 1px solid #eef1f6;
}
.timeline-body {
  max-height: 190px;
  overflow-y: auto;
  padding: 10px 14px;
}
.timeline-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 3px 0;
  font-size: 12.5px;
}
.tl-time {
  flex-shrink: 0;
  color: #94a3b8;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
}
.tl-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2563eb;
  transform: translateY(-1px);
}
.timeline-line.error .tl-dot { background: #ef4444; }
.tl-msg {
  color: #475569;
  line-height: 1.6;
}
.timeline-line.error .tl-msg { color: #dc2626; }

.scan-error {
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #dc2626;
  font-size: 13px;
  white-space: pre-wrap;
}

/* 动画点 */
.scan-dots {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}
.scan-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2563eb;
  animation: blinkdots 1s infinite;
}
.scan-dots.small i { width: 4px; height: 4px; }
.scan-dots i:nth-child(2) { animation-delay: 0.2s; }
.scan-dots i:nth-child(3) { animation-delay: 0.4s; }
@keyframes blinkdots {
  0%, 80%, 100% { opacity: 0.2; }
  40% { opacity: 1; }
}


</style>
