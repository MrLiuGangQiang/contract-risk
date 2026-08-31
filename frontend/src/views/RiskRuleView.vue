<template>
  <AppLayout>
    <div class="risk-rule-page">
      <el-card class="toolbar-card" shadow="never">
        <div class="toolbar">
          <div class="toolbar-left">
            <h3>合同风险扫描规则</h3>
            <span class="toolbar-desc">每条规则只需一句话；AI 会理解规则并逐条校验合同</span>
          </div>
        </div>
      </el-card>

      <el-tabs v-model="activeTab">
        <!-- ==================== 我的规则 ==================== -->
        <el-tab-pane label="我的规则" name="mine">
          <el-card shadow="never">
            <div class="tab-toolbar">
              <div class="tab-filters">
                <el-input v-model="mineKeyword" placeholder="搜索规则内容" clearable style="width: 220px" @input="mineExpanded = undefined">
                  <template #prefix><el-icon><search /></el-icon></template>
                </el-input>
                <el-select v-model="mineCategory" placeholder="维度" clearable style="width: 140px">
                  <el-option v-for="opt in categoryOptions" :key="opt" :label="categoryLabel(opt)" :value="opt" />
                </el-select>
              </div>
              <div class="tree-ctrl">
                <el-button size="small" @click="expandAll('mine')">全部展开</el-button>
                <el-button size="small" @click="collapseAll('mine')">全部折叠</el-button>
                <el-button type="warning" plain :icon="RefreshLeft" :disabled="mineRules.every((r) => !r.is_custom)" @click="onRestoreAll">
                  一键恢复默认
                </el-button>
              </div>
            </div>

            <RiskRuleTree :rules="filteredMine" :loading="mineLoading" :category-label="categoryLabel" :expanded-keys="mineExpanded">
              <template #actions="{ rule }">
                <el-button link type="primary" @click="openEditMine(rule)">编辑</el-button>
                <el-button v-if="rule.is_custom" link type="warning" @click="onRestoreOne(rule)">恢复默认</el-button>
              </template>
            </RiskRuleTree>
          </el-card>
        </el-tab-pane>

        <!-- ==================== 全局模板（管理员） ==================== -->
        <el-tab-pane v-if="canManageGlobal" label="全局模板" name="global">
          <el-card shadow="never">
            <div class="tab-toolbar">
              <div class="tab-filters">
                <el-input v-model="globalKeyword" placeholder="搜索规则内容" clearable style="width: 220px" @keyup.enter="loadGlobal" @clear="loadGlobal" @input="globalExpanded = undefined">
                  <template #prefix><el-icon><search /></el-icon></template>
                </el-input>
                <el-select v-model="globalCategory" placeholder="维度" clearable style="width: 140px" @change="loadGlobal">
                  <el-option v-for="opt in categoryOptions" :key="opt" :label="categoryLabel(opt)" :value="opt" />
                </el-select>
              </div>
              <div class="tab-actions">
                <el-button size="small" @click="expandAll('global')">展开</el-button>
                <el-button size="small" @click="collapseAll('global')">折叠</el-button>
                <el-button type="primary" :icon="Plus" @click="openCreateGlobal">新建规则</el-button>
                <el-button :icon="Upload" @click="openImport">导入</el-button>
                <el-button :icon="Download" :loading="exporting" @click="onExport">导出</el-button>
                <el-button :icon="EditPen" @click="openMdEditor">编辑模板 MD</el-button>
              </div>
            </div>

            <RiskRuleTree :rules="globalRules" :loading="globalLoading" :category-label="categoryLabel" :expanded-keys="globalExpanded">
              <template #actions="{ rule }">
                <el-button link type="primary" @click="openEditGlobal(rule)">编辑</el-button>
                <el-button link type="danger" @click="onDeleteGlobal(rule)">删除</el-button>
              </template>
            </RiskRuleTree>
          </el-card>
        </el-tab-pane>
      </el-tabs>

      <!-- 编辑弹窗（个人/全局共用） -->
      <el-dialog v-model="dialogVisible" :title="dialogTitle" width="620px" destroy-on-close>
        <el-form ref="formRef" :model="form" :rules="formRules" label-position="top">
          <el-form-item label="一句话规则" prop="rule_text" class="rule-text-item">
            <el-input
              v-model="form.rule_text"
              type="textarea"
              :rows="3"
              maxlength="2000"
              show-word-limit
              placeholder="用一句人话描述你想防止的风险，例如：付款不得约定一次性全额付款且无质保金"
            />
            <div class="form-tip">这是 AI 理解并逐条校验合同的唯一依据</div>
          </el-form-item>

          <el-form-item label="所属维度（可选）">
            <el-select
              v-model="form.category"
              filterable
              allow-create
              clearable
              default-first-option
              style="width: 100%"
              placeholder="不填则归入未分类"
            >
              <el-option v-for="opt in categoryOptions" :key="opt" :label="categoryLabel(opt)" :value="opt" />
            </el-select>
            <div class="form-tip">维度用于报告分组筛选，可自定义，如「财务风险」「知识产权」</div>
          </el-form-item>

          <el-form-item label="启用">
            <el-switch v-model="form.enabled" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="submitDialog">保存</el-button>
        </template>
      </el-dialog>

      <!-- 导入 Markdown -->
      <el-dialog v-model="importVisible" title="导入全局规则（Markdown）" width="640px" destroy-on-close>
        <div class="import-tip">格式：`# 维度` 下每行 `- 一句话规则`。支持从「导出」生成的 Markdown 直接粘贴。</div>
        <el-input v-model="importContent" type="textarea" :rows="14" placeholder="# 财务风险&#10;- 付款不得一次性全额支付且无质保金" />
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
        <div class="md-tip">`# 维度` 标题下，每行 `- 一句话规则`；保存时校验，重复/空行会报错。</div>
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
import RiskRuleTree from '@/components/RiskRuleTree.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canManageGlobal = computed(
  () => auth.isSuperAdmin || auth.user?.permissions?.includes('risk:rule:manage') === true,
)

const DEFAULT_CATEGORY_MAP: Record<string, string> = {
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
function categoryLabel(key: string): string {
  return DEFAULT_CATEGORY_MAP[key] ?? key
}

const categoryOptions = computed<string[]>(() => {
  const set = new Set<string>(Object.keys(DEFAULT_CATEGORY_MAP))
  for (const rule of [...mineRules.value, ...globalRules.value]) {
    if (rule.category) set.add(rule.category)
  }
  return [...set]
})

const activeTab = ref('mine')

// 我的规则
const mineLoading = ref(false)
const mineRules = ref<RiskRule[]>([])
const mineKeyword = ref('')
const mineCategory = ref('')
const mineExpanded = ref<string[] | undefined>(undefined)
const filteredMine = computed(() =>
  mineRules.value.filter((r) => {
    const kw = mineKeyword.value.trim().toLowerCase()
    const matchKw = !kw || r.rule_text.toLowerCase().includes(kw)
    const matchCat = !mineCategory.value || r.category === mineCategory.value
    return matchKw && matchCat
  }),
)

// 全局模板
const globalLoading = ref(false)
const globalRules = ref<RiskRule[]>([])
const globalKeyword = ref('')
const globalCategory = ref('')
const globalExpanded = ref<string[] | undefined>(undefined)

function expandAll(target: 'mine' | 'global') {
  if (target === 'mine') mineExpanded.value = undefined
  else globalExpanded.value = undefined
}
function collapseAll(target: 'mine' | 'global') {
  if (target === 'mine') mineExpanded.value = []
  else globalExpanded.value = []
}

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
  rule_text: '',
  category: '',
  enabled: true,
})
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
  rule_text: [{ required: true, message: '请输入一句话规则', trigger: 'blur' }],
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
  try {
    const data = await listRiskRules({
      page: 1,
      page_size: 100,
      keyword: globalKeyword.value || undefined,
      category: globalCategory.value || undefined,
    })
    globalRules.value = data.items
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    globalLoading.value = false
  }
}

function fillForm(row: RiskRule) {
  Object.assign(form, {
    id: row.id,
    rule_text: row.rule_text || '',
    category: row.category || '',
    enabled: row.enabled,
  })
}

function openEditMine(row: RiskRule) {
  dialogKind.value = 'mine'
  fillForm(row)
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function openCreateGlobal() {
  dialogKind.value = 'global-create'
  Object.assign(form, { id: 0, rule_text: '', category: '', enabled: true })
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function openEditGlobal(row: RiskRule) {
  dialogKind.value = 'global-edit'
  fillForm(row)
  dialogVisible.value = true
  void nextTick(() => formRef.value?.clearValidate())
}

function buildPayload(): RiskRulePayload {
  return {
    rule_text: form.rule_text.trim(),
    category: form.category || null,
    enabled: form.enabled,
  }
}

async function submitDialog() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (dialogKind.value === 'mine') {
      await updateMyRiskRule(form.id, buildPayload())
      ElMessage.success('已保存到我的规则')
    } else if (dialogKind.value === 'global-create') {
      await createRiskRule(buildPayload())
      ElMessage.success('全局规则已创建')
    } else {
      await updateRiskRule(form.id, buildPayload())
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
    await ElMessageBox.confirm(`确定将「${row.rule_text.slice(0, 30)}」恢复为全局默认？`, '恢复默认', {
      type: 'warning', confirmButtonText: '恢复默认', cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteMyRiskRule(row.id)
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
    await ElMessageBox.confirm(`确定删除全局规则「${row.rule_text.slice(0, 30)}」？`, '删除确认', {
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
    ElMessage.success(`导入完成：新增 ${result.created}，更新 ${result.updated}`)
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
.toolbar-card {
  padding: 4px 6px;
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
  gap: 10px;
  flex-wrap: wrap;
}
.tab-actions,
.tree-ctrl {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.rule-text-item :deep(.el-form-item__label) {
  font-weight: 700;
}
.form-tip {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.6;
}
.import-tip,
.md-tip {
  margin-bottom: 10px;
  font-size: 12.5px;
  color: #64748b;
  line-height: 1.7;
}
.import-actions {
  margin-top: 10px;
}
.md-error {
  margin-top: 10px;
  color: #dc2626;
  font-size: 13px;
  white-space: pre-wrap;
}
.md-editor :deep(textarea) {
  font-family: Consolas, Menlo, monospace;
  font-size: 13px;
  line-height: 1.7;
}
</style>
