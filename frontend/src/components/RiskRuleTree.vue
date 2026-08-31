<template>
  <div v-loading="loading" class="rule-tree">
    <div v-if="!groups.length" class="tree-empty">暂无匹配规则</div>

    <div v-for="group in groups" :key="group.key" class="dim-group">
      <!-- 一级节点：维度 -->
      <div class="dim-head" @click="toggle(group.key)">
        <el-icon class="caret" :class="{ rotated: isOpen(group.key) }"><arrow-right /></el-icon>
        <span class="dim-name">{{ group.label }}</span>
        <span class="dim-count">{{ group.rules.length }} 条规则</span>
      </div>

      <!-- 二级节点：规则（一句话） -->
      <div v-show="isOpen(group.key)" class="dim-body">
        <div v-for="rule in group.rules" :key="rule.id" class="rule-row" :class="{ disabled: !rule.enabled }">
          <span class="rule-text">{{ rule.rule_text }}</span>
          <el-tag v-if="rule.is_custom" type="warning" size="small" effect="plain" class="rule-src">自定义</el-tag>
          <el-tag v-if="!rule.enabled" type="info" size="small" effect="plain" class="rule-src">停用</el-tag>
          <div class="rule-actions">
            <slot name="actions" :rule="rule"></slot>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import type { RiskRule } from '@/api/types'

const props = defineProps<{
  rules: RiskRule[]
  loading?: boolean
  categoryLabel: (key: string) => string
  expandedKeys?: string[]
}>()

const KNOWN_ORDER = [
  'project', 'technology', 'contract', 'general',
  'subject', 'payment', 'delivery', 'breach', 'ip',
  'confidential', 'dispute', 'tax', 'warranty', 'compliance',
]

const expandedOverride = reactive<{ keys: string[] | null }>({ keys: null })

function toggle(key: string) {
  const current = new Set(props.expandedKeys ?? expandedOverride.keys ?? groups.value.map((g) => g.key))
  if (current.has(key)) current.delete(key)
  else current.add(key)
  expandedOverride.keys = [...current]
}

function isOpen(key: string): boolean {
  if (props.expandedKeys) return props.expandedKeys.includes(key)
  if (expandedOverride.keys) return expandedOverride.keys.includes(key)
  return true
}

interface DimGroup {
  key: string
  label: string
  rules: RiskRule[]
}

const groups = computed<DimGroup[]>(() => {
  const byCat = new Map<string, RiskRule[]>()
  for (const rule of props.rules) {
    const key = rule.category || ''
    if (!byCat.has(key)) byCat.set(key, [])
    byCat.get(key)!.push(rule)
  }
  const list: DimGroup[] = []
  for (const [key, rules] of byCat) {
    list.push({
      key,
      label: key ? props.categoryLabel(key) : '未分类',
      rules: [...rules].sort((a, b) => a.sort_order - b.sort_order),
    })
  }
  return list.sort((a, b) => {
    const ia = KNOWN_ORDER.indexOf(a.key)
    const ib = KNOWN_ORDER.indexOf(b.key)
    if (ia !== -1 && ib !== -1) return ia - ib
    if (ia !== -1) return -1
    if (ib !== -1) return 1
    return a.label.localeCompare(b.label, 'zh-CN')
  })
})
</script>

<style scoped>
.rule-tree {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 120px;
}
.tree-empty {
  padding: 40px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}
.dim-group {
  border: 1px solid #e8edf5;
  border-radius: 14px;
  background: #fff;
  overflow: hidden;
}
.dim-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  cursor: pointer;
  background: linear-gradient(120deg, rgba(37, 99, 235, 0.05), rgba(124, 58, 237, 0.03));
  transition: background 0.2s ease;
  flex-wrap: wrap;
}
.dim-head:hover {
  background: linear-gradient(120deg, rgba(37, 99, 235, 0.09), rgba(124, 58, 237, 0.06));
}
.caret {
  color: #64748b;
  font-size: 13px;
  transition: transform 0.2s ease;
  flex-shrink: 0;
}
.caret.rotated {
  transform: rotate(90deg);
}
.dim-name {
  font-size: 14.5px;
  font-weight: 800;
  color: #0f172a;
}
.dim-count {
  font-size: 12px;
  color: #94a3b8;
}
.dim-body {
  padding: 8px 14px 12px 34px;
}
.rule-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  margin: 3px 0;
  border-radius: 10px;
  background: #fbfcfe;
  border: 1px solid #eef1f6;
  transition: all 0.15s ease;
  flex-wrap: wrap;
}
.rule-row:hover {
  border-color: rgba(37, 99, 235, 0.35);
  background: #f8faff;
}
.rule-row.disabled {
  opacity: 0.55;
}
.rule-text {
  flex: 1;
  min-width: 220px;
  font-size: 13.5px;
  font-weight: 600;
  line-height: 1.6;
  color: #1e293b;
}
.rule-src {
  flex-shrink: 0;
}
.rule-actions {
  margin-left: auto;
  flex-shrink: 0;
}
@media (max-width: 900px) {
  .dim-body { padding-left: 14px; }
  .rule-actions { margin-left: 0; width: 100%; }
}
</style>
