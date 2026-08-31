<template>
  <div class="report-charts">
    <div class="chart-row">
      <div class="chart-card">
        <div class="chart-title">风险级别分布</div>
        <div ref="severityRef" class="chart-canvas"></div>
      </div>
      <div class="chart-card chart-card-wide">
        <div class="chart-title">风险维度分布</div>
        <div ref="categoryRef" class="chart-canvas"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { LegendComponent, TooltipComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ContractRisk } from '@/api/contractTypes'

echarts.use([PieChart, BarChart, LegendComponent, TooltipComponent, GridComponent, CanvasRenderer])

const props = defineProps<{ risks: ContractRisk[]; totalChars: number }>()

const severityRef = ref<HTMLDivElement>()
const categoryRef = ref<HTMLDivElement>()
const charts: ReturnType<typeof echarts.init>[] = []

const SEVERITY_COLOR: Record<string, string> = { high: '#ef4444', medium: '#f59e0b', low: '#10b981' }
const CATEGORY_LABEL: Record<string, string> = {
  project: '项目管理', technology: '技术风险', contract: '合同条款', general: '通用风险',
  subject: '主体与签署', payment: '付款与结算', delivery: '交付与验收', breach: '违约责任',
  ip: '知识产权', confidential: '保密与数据安全', dispute: '争议解决', tax: '税务与发票',
  warranty: '质保与售后', compliance: '合规审查',
}
const CATEGORY_COLOR: Record<string, string> = {
  project: '#7b9ac7', technology: '#7fb3ae', contract: '#8e9bb8', general: '#9aa4ae',
  subject: '#a391bd', payment: '#8fbc9a', delivery: '#d2a277', breach: '#cf9595',
  ip: '#bd9cbf', confidential: '#88b1cf', dispute: '#b19c8c', tax: '#8eb8a6',
  warranty: '#86a8d4', compliance: '#97c29a',
}

function buildSeverity() {
  if (!severityRef.value) return
  const chart = echarts.init(severityRef.value)
  charts.push(chart)
  const counts: Record<string, number> = { high: 0, medium: 0, low: 0 }
  props.risks.forEach((r) => { counts[r.severity] = (counts[r.severity] ?? 0) + 1 })
  const data = [
    { key: 'high', name: '高风险', value: counts.high },
    { key: 'medium', name: '中风险', value: counts.medium },
    { key: 'low', name: '低风险', value: counts.low },
  ].filter((d) => d.value > 0)
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 项 ({d}%)' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, textStyle: { color: '#64748b', fontSize: 11 } },
    series: [
      {
        type: 'pie',
        radius: ['52%', '72%'],
        center: ['50%', '44%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: data.length
          ? data.map((d) => ({ name: d.name, value: d.value, itemStyle: { color: SEVERITY_COLOR[d.key] } }))
          : [{ name: '无风险', value: 1, itemStyle: { color: '#d1fae5' } }],
      },
    ],
  })
}

function buildCategory() {
  if (!categoryRef.value) return
  const chart = echarts.init(categoryRef.value)
  charts.push(chart)
  const counter = new Map<string, number>()
  for (const risk of props.risks) {
    counter.set(risk.category, (counter.get(risk.category) ?? 0) + 1)
  }
  const entries = [...counter.entries()].sort((a, b) => b[1] - a[1])
  const names = entries.map(([k]) => (CATEGORY_LABEL[k] ?? k) || '未分类')
  const values = entries.map(([k, v]) => ({
    value: v,
    itemStyle: { color: CATEGORY_COLOR[k] ?? '#a6adb4' },
  }))
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 10, right: 20, top: 10, bottom: 10, containLabel: true },
    xAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: '#475569', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: values,
        barWidth: 14,
        itemStyle: {
          borderRadius: [0, 7, 7, 0],
        },
      },
    ],
  })
}

function buildAll() {
  charts.forEach((c) => c.dispose())
  charts.length = 0
  buildSeverity()
  buildCategory()
}

function onResize() {
  charts.forEach((c) => c.resize())
}

onMounted(() => {
  buildAll()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  charts.forEach((c) => c.dispose())
})
watch(() => props.risks, buildAll, { deep: true })
</script>

<style scoped>
.report-charts { margin-bottom: 16px; }
.chart-row {
  display: grid;
  grid-template-columns: 0.8fr 2fr;
  gap: 12px;
}
.chart-card {
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: #fff;
  padding: 12px 10px 6px;
  box-shadow: 0 4px 18px rgba(37, 99, 235, 0.05);
}
.chart-title {
  padding-left: 2px;
  font-size: 12.5px;
  font-weight: 700;
  color: #334155;
  letter-spacing: 0.5px;
}
.chart-canvas { height: 210px; }
@media (max-width: 900px) {
  .chart-row { grid-template-columns: 1fr; }
}
</style>
