<template>
  <AppLayout>
    <div class="risk-rule-page">
      <el-card class="toolbar-card" shadow="never">
        <div class="toolbar">
          <div class="toolbar-left">
            <h3>合同风险规则</h3>
            <span class="toolbar-desc">维护合同风险扫描规则：支持在线编辑、Markdown 导入导出（仅超管）</span>
          </div>
          <div class="toolbar-right">
            <el-input
              v-model="keyword"
              placeholder="搜索编码 / 名称"
              clearable
              style="width: 200px"
              @keyup.enter="onSearch"
              @clear="onSearch"
            >
              <template #prefix><el-icon><search /></el-icon></template>
            </el-input>
            <el-select v-model="category" placeholder="分类" clearable style="width: 130px" @change="onSearch">
              <el-option v-for="(label, value) in categoryMap" :key="value" :label="label" :value="value" />
            </el-select>
            <el-select v-model="severity" placeholder="级别" clearable style="width: 110px" @change="onSearch">
              <el-option v-for="(label, value) in severityMap" :key="value" :label="label" :value="value" />
            </el-select>
            <el-button type="primary" :icon="Plus" @click="openCreate">新建规则</el-button>
            <el-button :icon="Upload" @click="openImport">导入</el-button>
            <el-button :icon="Download" :loading="exporting" @click="onExport">导出</el-button>
          </div>
        </div>
      </el-card>

      <el-card shadow="never">
        <el-table v-loading="loading" :data="rules" stripe>
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="code" label="编码" min-width="150" show-overflow-tooltip />
          <el-table-column prop="name" label="规则名称" min-width="160" show-overflow-tooltip />
          <el-table-column label="分类" width="110">
            <template #default="{ row }">{{ categoryMap[row.category] ?? row.category }}</template>
          </el-table-column>
          <el-table-column label="级别" width="90">
            <template #default="{ row }">
              <el-tag :type="severityType(row.severity)" size="small">
                {{ severityMap[row.severity] ?? row.severity }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="关键词" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.keywords.join(', ') || '-' }}</template>
          </el-table-column>
          <el-table-column label="启用" width="80">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
                {{ row.enabled ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sort_order" label="排序" width="70" />
          <el-table-column label="更新时间" min-width="150">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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
            @current-change="loadRules"
            @size-change="loadRules"
          />
        </div>
      </el-card>

      <!-- 新建/编辑 -->
      <el-dialog
        v-model="dialogVisible"
        :title="dialogMode === 'create' ? '新建规则' : '编辑规则'"
        width="560px"
        destroy-on-close
      >
        <el-form ref="formRef" :model="form" :rules="formRules" label-width="90px">
          <el-form-item label="编码" prop="code">
            <el-input v-model="form.code" :disabled="dialogMode === 'edit'" placeholder="大写字母/数字/下划线，如 PAYMENT_ABNORMAL" />
          </el-form-item>
          <el-form-item label="规则名称" prop="name">
            <el-input v-model="form.name" placeholder="如：付款条款异常" />
          </el-form-item>
          <el-form-item label="分类" prop="category">
            <el-select v-model="form.category" style="width: 100%">
              <el-option v-for="(label, value) in categoryMap" :key="value" :label="label" :value="value" />
            </el-select>
          </el-form-item>
          <el-form-item label="级别" prop="severity">
            <el-select v-model="form.severity" style="width: 100%">
              <el-option v-for="(label, value) in severityMap" :key="value" :label="label" :value="value" />
            </el-select>
          </el-form-item>
          <el-form-item label="关键词" prop="keywords">
            <el-input v-model="keywordsText" placeholder="多个关键词用逗号分隔，如：付款, 支付, 预付款" />
          </el-form-item>
          <el-form-item label="风险说明" prop="description">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="描述该规则识别什么风险" />
          </el-form-item>
          <el-form-item label="处置建议" prop="suggestion">
            <el-input v-model="form.suggestion" type="textarea" :rows="3" placeholder="给出风险处置/修改建议" />
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.enabled" />
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="submitDialog">保存</el-button>
        </template>
      </el-dialog>

      <!-- 导入 Markdown -->
      <el-dialog v-model="importVisible" title="导入规则（Markdown）" width="640px" destroy-on-close>
        <div class="import-tip">
          支持从「导出」生成的 Markdown 文件导入；规则按编码幂等更新。粘贴内容或选择 .md 文件。
        </div>
        <el-input v-model="importContent" type="textarea" :rows="12" placeholder="# 合同风险扫描规则 ..." />
        <div class="import-actions">
          <input ref="fileRef" type="file" accept=".md,.markdown,.txt" style="display: none" @change="onFileChange" />
          <el-button :icon="Upload" @click="fileRef?.click()">选择 .md 文件</el-button>
        </div>
        <template #footer>
          <el-button @click="importVisible = false">取消</el-button>
          <el-button type="primary" :loading="importing" @click="submitImport">开始导入</el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Download, Plus, Search, Upload } from '@element-plus/icons-vue'
import {
  createRiskRule,
  deleteRiskRule,
  exportRiskRules,
  importRiskRules,
  listRiskRules,
  updateRiskRule,
  type RiskRulePayload,
} from '@/api/admin'
import type { RiskRule } from '@/api/types'
import AppLayout from '@/components/AppLayout.vue'

const categoryMap: Record<string, string> = {
  payment: '付款条款',
  breach: '违约责任',
  subject: '合同主体',
  ip: '知识产权',
  dispute: '争议解决',
  other: '其他',
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

const loading = ref(false)
const exporting = ref(false)
const saving = ref(false)
const importing = ref(false)
const rules = ref<RiskRule[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const category = ref('')
const severity = ref('')

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const form = reactive({
  id: 0,
  code: '',
  name: '',
  category: 'payment',
  severity: 'medium',
  description: '',
  suggestion: '',
  enabled: true,
  sort_order: 0,
})
const keywordsText = ref('')

const importVisible = ref(false)
const importContent = ref('')
const fileRef = ref<HTMLInputElement>()

const formRules: FormRules = {
  code: [
    { required: true, message: '请输入规则编码', trigger: 'blur' },
    { pattern: /^[A-Z0-9_]+$/, message: '仅支持大写字母、数字、下划线', trigger: 'blur' },
  ],
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  severity: [{ required: true, message: '请选择级别', trigger: 'change' }],
  description: [{ required: true, message: '请输入风险说明', trigger: 'blur' }],
  suggestion: [{ required: true, message: '请输入处置建议', trigger: 'blur' }],
}

onMounted(loadRules)

async function loadRules() {
  loading.value = true
  try {
    const data = await listRiskRules({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      category: category.value || undefined,
      severity: severity.value || undefined,
    })
    rules.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  void loadRules()
}

function openCreate() {
  dialogMode.value = 'create'
  Object.assign(form, {
    id: 0, code: '', name: '', category: 'payment', severity: 'medium',
    description: '', suggestion: '', enabled: true, sort_order: 0,
  })
  keywordsText.value = ''
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function openEdit(row: RiskRule) {
  dialogMode.value = 'edit'
  Object.assign(form, {
    id: row.id, code: row.code, name: row.name, category: row.category,
    severity: row.severity, description: row.description, suggestion: row.suggestion,
    enabled: row.enabled, sort_order: row.sort_order,
  })
  keywordsText.value = row.keywords.join(', ')
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function buildPayload(): RiskRulePayload {
  const payload: RiskRulePayload = {
    name: form.name,
    category: form.category,
    severity: form.severity,
    keywords: keywordsText.value.split(',').map((s) => s.trim()).filter(Boolean),
    description: form.description,
    suggestion: form.suggestion,
    enabled: form.enabled,
    sort_order: form.sort_order,
  }
  if (dialogMode.value === 'create') payload.code = form.code
  return payload
}

async function submitDialog() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (dialogMode.value === 'create') {
      await createRiskRule(buildPayload())
      ElMessage.success('规则已创建')
    } else {
      await updateRiskRule(form.id, buildPayload())
      ElMessage.success('规则已更新')
    }
    dialogVisible.value = false
    await loadRules()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    saving.value = false
  }
}

async function onDelete(row: RiskRule) {
  try {
    await ElMessageBox.confirm(`确定删除规则「${row.name}」？`, '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteRiskRule(row.id)
    ElMessage.success('规则已删除')
    await loadRules()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

function openImport() {
  importContent.value = ''
  importVisible.value = true
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    importContent.value = String(reader.result ?? '')
  }
  reader.readAsText(file, 'utf-8')
  input.value = ''
}

async function submitImport() {
  if (!importContent.value.trim()) {
    ElMessage.warning('请先粘贴 Markdown 内容或选择文件')
    return
  }
  importing.value = true
  try {
    const result = await importRiskRules(importContent.value)
    ElMessage.success(`导入完成：新增 ${result.created}，更新 ${result.updated}，跳过 ${result.skipped}`)
    importVisible.value = false
    await loadRules()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    importing.value = false
  }
}

async function onExport() {
  exporting.value = true
  try {
    const blob = await exportRiskRules()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'contract-risk-rules.md'
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('规则已导出')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    exporting.value = false
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
.risk-rule-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-left h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #111827;
}
.toolbar-desc {
  font-size: 12px;
  color: #6b7280;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.import-tip {
  margin-bottom: 10px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
}
.import-actions {
  margin-top: 10px;
  display: flex;
  align-items: center;
}
</style>
