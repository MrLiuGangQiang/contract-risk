<template>
  <AppLayout>
    <div class="risk-rule-page">
      <el-card class="toolbar-card" shadow="never">
        <div class="toolbar">
          <div class="toolbar-left">
            <h3>合同风险扫描规则</h3>
            <span class="toolbar-desc">默认使用全局模板；可修改自己的规则副本，互不影响</span>
          </div>
        </div>
      </el-card>

      <el-tabs v-model="activeTab">
        <!-- ==================== 我的规则 ==================== -->
        <el-tab-pane label="我的规则" name="mine">
          <el-card shadow="never">
            <div class="tab-toolbar">
              <div class="tab-filters">
                <el-input v-model="mineKeyword" placeholder="搜索编码 / 名称" clearable style="width: 200px">
                  <template #prefix><el-icon><search /></el-icon></template>
                </el-input>
                <el-select v-model="mineCategory" placeholder="维度" clearable style="width: 130px">
                  <el-option v-for="(label, value) in categoryMap" :key="value" :label="label" :value="value" />
                </el-select>
                <el-select v-model="mineSeverity" placeholder="级别" clearable style="width: 110px">
                  <el-option v-for="(label, value) in severityMap" :key="value" :label="label" :value="value" />
                </el-select>
              </div>
              <el-button type="warning" plain :icon="RefreshLeft" :disabled="mineRules.every((r) => !r.is_custom)" @click="onRestoreAll">
                一键恢复默认
              </el-button>
            </div>

            <el-table v-loading="mineLoading" :data="filteredMine" stripe>
              <el-table-column label="来源" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.is_custom ? 'warning' : 'info'" size="small">
                    {{ row.is_custom ? '自定义' : '默认' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="code" label="编码" min-width="140" show-overflow-tooltip />
              <el-table-column prop="name" label="规则名称" min-width="150" show-overflow-tooltip />
              <el-table-column label="维度" width="110">
                <template #default="{ row }">{{ categoryMap[row.category] ?? row.category }}</template>
              </el-table-column>
              <el-table-column label="级别" width="90">
                <template #default="{ row }">
                  <el-tag :type="severityType(row.severity)" size="small">{{ severityMap[row.severity] ?? row.severity }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="关键词" min-width="180" show-overflow-tooltip>
                <template #default="{ row }">{{ row.keywords.join(', ') || '-' }}</template>
              </el-table-column>
              <el-table-column label="启用" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '启用' : '停用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="170" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openEditMine(row)">编辑</el-button>
                  <el-button v-if="row.is_custom" link type="warning" @click="onRestoreOne(row)">恢复默认</el-button>
                  <span v-else class="muted">跟随全局</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <!-- ==================== 全局模板（管理员） ==================== -->
        <el-tab-pane v-if="canManageGlobal" label="全局模板" name="global">
          <el-card shadow="never">
            <div class="tab-toolbar">
              <div class="tab-filters">
                <el-input v-model="globalKeyword" placeholder="搜索编码 / 名称" clearable style="width: 200px" @keyup.enter="loadGlobal" @clear="loadGlobal">
                  <template #prefix><el-icon><search /></el-icon></template>
                </el-input>
                <el-select v-model="globalCategory" placeholder="维度" clearable style="width: 130px" @change="loadGlobal">
                  <el-option v-for="(label, value) in categoryMap" :key="value" :label="label" :value="value" />
                </el-select>
                <el-select v-model="globalSeverity" placeholder="级别" clearable style="width: 110px" @change="loadGlobal">
                  <el-option v-for="(label, value) in severityMap" :key="value" :label="label" :value="value" />
                </el-select>
              </div>
              <div class="tab-actions">
                <el-button type="primary" :icon="Plus" @click="openCreateGlobal">新建规则</el-button>
                <el-button :icon="Upload" @click="openImport">导入</el-button>
                <el-button :icon="Download" :loading="exporting" @click="onExport">导出</el-button>
                <el-button :icon="EditPen" @click="openMdEditor">编辑模板 MD</el-button>
              </div>
            </div>

            <el-table v-loading="globalLoading" :data="globalRules" stripe>
              <el-table-column prop="code" label="编码" min-width="140" show-overflow-tooltip />
              <el-table-column prop="name" label="规则名称" min-width="150" show-overflow-tooltip />
              <el-table-column label="维度" width="110">
                <template #default="{ row }">{{ categoryMap[row.category] ?? row.category }}</template>
              </el-table-column>
              <el-table-column label="级别" width="90">
                <template #default="{ row }">
                  <el-tag :type="severityType(row.severity)" size="small">{{ severityMap[row.severity] ?? row.severity }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="关键词" min-width="180" show-overflow-tooltip>
                <template #default="{ row }">{{ row.keywords.join(', ') || '-' }}</template>
              </el-table-column>
              <el-table-column label="启用" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '启用' : '停用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="sort_order" label="排序" width="70" />
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openEditGlobal(row)">编辑</el-button>
                  <el-button link type="danger" @click="onDeleteGlobal(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pager">
              <el-pagination
                v-model:current-page="globalPage"
                v-model:page-size="globalPageSize"
                :total="globalTotal"
                :page-sizes="[10, 20, 50]"
                layout="total, sizes, prev, pager, next"
                @current-change="loadGlobal"
                @size-change="loadGlobal"
              />
            </div>
          </el-card>
        </el-tab-pane>
      </el-tabs>

      <!-- 编辑弹窗（个人/全局共用） -->
      <el-dialog
        v-model="dialogVisible"
        :title="dialogTitle"
        width="560px"
        destroy-on-close
      >
        <el-form ref="formRef" :model="form" :rules="formRules" label-width="90px">
          <el-form-item v-if="dialogKind === 'global-create'" label="编码" prop="code">
            <el-input v-model="form.code" placeholder="大写字母/数字/下划线，如 PAYMENT_ABNORMAL" />
          </el-form-item>
          <el-form-item label="规则名称" prop="name">
            <el-input v-model="form.name" placeholder="如：付款条款异常" />
          </el-form-item>
          <el-form-item label="维度" prop="category">
            <el-select v-model="form.category" style="width: 100%">
              <el-option v-for="(label, value) in categoryMap" :key="value" :label="label" :value="value" />
            </el-select>
          </el-form-item>
          <el-form-item label="级别" prop="severity">
            <el-select v-model="form.severity" style="width: 100%">
              <el-option v-for="(label, value) in severityMap" :key="value" :label="label" :value="value" />
            </el-select>
          </el-form-item>
          <el-form-item label="关键词">
            <el-input v-model="keywordsText" placeholder="多个关键词用逗号分隔，如：付款, 支付, 预付款" />
          </el-form-item>
          <el-form-item label="风险说明" prop="description">
            <el-input v-model="form.description" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="处置建议" prop="suggestion">
            <el-input v-model="form.suggestion" type="textarea" :rows="3" />
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
      <el-dialog v-model="importVisible" title="导入全局规则（Markdown）" width="640px" destroy-on-close>
        <div class="import-tip">支持从「导出」生成的 Markdown 导入；规则按编码幂等更新。粘贴内容或选择 .md 文件。</div>
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

      <!-- 直接编辑模板 Markdown -->
      <el-dialog v-model="mdEditorVisible" title="编辑全局模板 Markdown" width="920px" top="4vh" destroy-on-close>
        <div class="md-tip">直接编辑 Markdown，保存时后端校验格式并拆分为规则；校验失败不会保存。</div>
        <el-input v-model="mdContent" type="textarea" :rows="26" class="md-editor" spellcheck="false" />
        <div v-if="mdError" class="md-error">{{ mdError }}</div>
        <template #footer>
          <el-button @click="mdEditorVisible = false">取消</el-button>
          <el-button type="primary" :loading="mdSaving" @click="saveMdEditor">保存并校验</el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Download, EditPen, Plus, RefreshLeft, Search, Upload } from '@element-plus/icons-vue'
import {
  createRiskRule,
  deleteMyRiskRule,
  deleteRiskRule,
  exportRiskRules,
  importRiskRules,
  listMyRiskRules,
  listRiskRules,
  restoreMyRiskRules,
  updateMyRiskRule,
  updateRiskRule,
  type RiskRulePayload,
} from '@/api/admin'
import type { RiskRule } from '@/api/types'
import AppLayout from '@/components/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canManageGlobal = computed(
  () => auth.isSuperAdmin || auth.user?.permissions?.includes('risk:rule:manage') === true,
)

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

const activeTab = ref('mine')

// 我的规则
const mineLoading = ref(false)
const mineRules = ref<RiskRule[]>([])
const mineKeyword = ref('')
const mineCategory = ref('')
const mineSeverity = ref('')
const filteredMine = computed(() =>
  mineRules.value.filter((r) => {
    const kw = mineKeyword.value.trim().toLowerCase()
    const matchKw = !kw || r.code.toLowerCase().includes(kw) || r.name.toLowerCase().includes(kw)
    const matchCat = !mineCategory.value || r.category === mineCategory.value
    const matchSev = !mineSeverity.value || r.severity === mineSeverity.value
    return matchKw && matchCat && matchSev
  }),
)

// 全局模板
const globalLoading = ref(false)
const globalRules = ref<RiskRule[]>([])
const globalTotal = ref(0)
const globalPage = ref(1)
const globalPageSize = ref(20)
const globalKeyword = ref('')
const globalCategory = ref('')
const globalSeverity = ref('')

const dialogVisible = ref(false)
const dialogKind = ref<'mine' | 'global-create' | 'global-edit'>('mine')
const dialogTitle = computed(() => {
  if (dialogKind.value === 'global-create') return '新建全局规则'
  if (dialogKind.value === 'global-edit') return '编辑全局规则'
  return '编辑我的规则'
})
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
const saving = ref(false)

const importVisible = ref(false)
const importContent = ref('')
const importing = ref(false)
const fileRef = ref<HTMLInputElement>()
const exporting = ref(false)
const mdEditorVisible = ref(false)
const mdContent = ref('')
const mdSaving = ref(false)
const mdError = ref('')

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

onMounted(async () => {
  await loadMine()
  if (canManageGlobal.value) await loadGlobal()
})

async function loadMine() {
  mineLoading.value = true
  try {
    mineRules.value = await listMyRiskRules()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    mineLoading.value = false
  }
}

async function loadGlobal() {
  if (!canManageGlobal.value) return
  globalLoading.value = true
  globalPage.value = Math.max(1, globalPage.value)
  try {
    const data = await listRiskRules({
      page: globalPage.value,
      page_size: globalPageSize.value,
      keyword: globalKeyword.value || undefined,
      category: globalCategory.value || undefined,
      severity: globalSeverity.value || undefined,
    })
    globalRules.value = data.items
    globalTotal.value = data.total
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    globalLoading.value = false
  }
}

function fillForm(row: RiskRule) {
  Object.assign(form, {
    id: row.id,
    code: row.code,
    name: row.name,
    category: row.category,
    severity: row.severity,
    description: row.description,
    suggestion: row.suggestion,
    enabled: row.enabled,
    sort_order: row.sort_order,
  })
  keywordsText.value = row.keywords.join(', ')
}

function openEditMine(row: RiskRule) {
  dialogKind.value = 'mine'
  fillForm(row)
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function openCreateGlobal() {
  dialogKind.value = 'global-create'
  Object.assign(form, {
    id: 0, code: '', name: '', category: 'payment', severity: 'medium',
    description: '', suggestion: '', enabled: true, sort_order: 0,
  })
  keywordsText.value = ''
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function openEditGlobal(row: RiskRule) {
  dialogKind.value = 'global-edit'
  fillForm(row)
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function buildPayload(withCode: boolean): RiskRulePayload {
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
  if (withCode) payload.code = form.code
  return payload
}

async function submitDialog() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (dialogKind.value === 'mine') {
      await updateMyRiskRule(form.code, buildPayload(false))
      ElMessage.success('已保存到我的规则')
    } else if (dialogKind.value === 'global-create') {
      await createRiskRule(buildPayload(true))
      ElMessage.success('全局规则已创建')
    } else {
      await updateRiskRule(form.id, buildPayload(false))
      ElMessage.success('全局规则已更新')
    }
    dialogVisible.value = false
    await loadMine()
    if (canManageGlobal.value) await loadGlobal()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    saving.value = false
  }
}

async function onRestoreOne(row: RiskRule) {
  try {
    await ElMessageBox.confirm(`确定将「${row.name}」恢复为全局默认？`, '恢复默认', {
      type: 'warning', confirmButtonText: '恢复默认', cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteMyRiskRule(row.code)
    ElMessage.success('已恢复默认')
    await loadMine()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onRestoreAll() {
  try {
    await ElMessageBox.confirm('确定恢复为全局默认？你的全部自定义修改将被清除且不可恢复。', '一键恢复默认', {
      type: 'warning', confirmButtonText: '确认恢复', cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await restoreMyRiskRules()
    ElMessage.success('已恢复为全局默认')
    await loadMine()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onDeleteGlobal(row: RiskRule) {
  try {
    await ElMessageBox.confirm(`确定删除全局规则「${row.name}」？`, '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteRiskRule(row.id)
    ElMessage.success('全局规则已删除')
    await loadGlobal()
    await loadMine()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function loadExportMarkdown(): Promise<string> {
  const blob = await exportRiskRules()
  return await blob.text()
}

async function openMdEditor() {
  mdError.value = ''
  mdEditorVisible.value = true
  mdContent.value = '加载中...'
  try {
    mdContent.value = await loadExportMarkdown()
  } catch (e) {
    mdError.value = (e as Error).message
    mdContent.value = ''
  }
}

async function saveMdEditor() {
  if (!mdContent.value.trim()) {
    mdError.value = '内容为空，请先编辑 Markdown'
    return
  }
  mdSaving.value = true
  mdError.value = ''
  try {
    const result = await importRiskRules(mdContent.value)
    ElMessage.success(`已保存：新增 ${result.created}，更新 ${result.updated}`)
    mdEditorVisible.value = false
    await loadGlobal()
    await loadMine()
  } catch (e) {
    mdError.value = (e as Error).message
  } finally {
    mdSaving.value = false
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
    await loadGlobal()
    await loadMine()
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
    ElMessage.success('全局规则已导出')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    exporting.value = false
  }
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
.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}
.tab-filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.tab-actions {
  display: flex;
  align-items: center;
  gap: 10px;
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
.md-tip {
  margin-bottom: 10px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
}
.md-editor :deep(textarea) {
  font-family: Consolas, Menlo, monospace;
  font-size: 13px;
  line-height: 1.6;
}
.md-error {
  margin-top: 8px;
  color: #dc2626;
  white-space: pre-wrap;
  font-size: 12px;
  max-height: 120px;
  overflow: auto;
}
.muted {
  color: #9ca3af;
  font-size: 12px;
}
</style>