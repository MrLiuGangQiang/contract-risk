<template>
  <AppLayout>
    <div class="page-header">
      <div class="title">钉钉登录配置</div>
      <div class="subtitle">由超级管理员维护 · 保存并启用后，企业员工即可通过钉钉扫码登录</div>
    </div>

    <div class="config-grid">
      <!-- 配置表单 -->
      <el-card class="brand-card form-card">
        <template #header>
          <div class="card-title">
            <el-icon :size="18" color="#2563eb"><setting /></el-icon>
            <span>应用参数</span>
          </div>
        </template>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
        >
          <el-form-item label="Client ID" prop="client_id">
            <el-input v-model="form.client_id" placeholder="钉钉开发者后台应用的 Client ID（原 AppKey）" clearable />
            <div class="form-tip">在开发者后台「基础信息 → 凭证与基础信息」获取</div>
          </el-form-item>
          <el-form-item label="Client Secret" prop="client_secret">
            <el-input
              v-model="form.client_secret"
              type="password"
              :placeholder="secretPlaceholder || '请输入应用 Client Secret（原 AppSecret）'"
              show-password
              clearable
            />
            <div class="form-tip">必须填应用详情「基础信息 → 凭证与基础信息」中的 <b>Client Secret</b>；<b>不要填企业 CorpSecret</b>。已加密存储；留空表示沿用旧值（当前：{{ secretPlaceholder || '未设置' }}）</div>
          </el-form-item>
          <el-form-item label="企业组织 ID（CorpId）" prop="corp_id">
            <el-input v-model="form.corp_id" placeholder="钉钉企业组织 ID（CorpId）" clearable />
            <div class="form-tip">在钉钉开发者后台首页或应用详情「基础信息 → 凭证与基础信息」获取；连通性测试需要</div>
          </el-form-item>
          <el-form-item label="回调地址" prop="redirect_uri">
            <el-input v-model="form.redirect_uri" placeholder="https://your-domain/dingtalk/callback" clearable />
            <div class="form-tip">需与开发者后台「重定向URL（回调域名）」同源；本系统回调路径固定为 /dingtalk/callback</div>
          </el-form-item>
          <el-form-item label="启用钉钉登录">
            <div class="enable-row">
              <el-switch v-model="form.enabled" />
              <el-tag :type="form.enabled ? 'success' : 'info'" size="small" effect="light">
                {{ form.enabled ? '已启用' : '未启用' }}
              </el-tag>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="onSave">保存配置</el-button>
            <el-button :loading="testing" @click="onTest">连通性测试</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 右侧说明 + 测试结果 -->
      <div class="side-col">
        <el-card class="brand-card side-card">
          <template #header>
            <div class="card-title">
              <el-icon :size="18" color="#10b981"><info-filled /></el-icon>
              <span>配置说明（最新官方流程）</span>
            </div>
          </template>
          <ol class="steps">
            <li>登录<a href="https://open-dev.dingtalk.com" target="_blank" rel="noopener">钉钉开发者后台</a> → 应用开发 → 企业内部应用 → 创建应用</li>
            <li>在「基础信息 → 凭证与基础信息」获取 Client ID、应用 Client Secret（原 AppSecret）与企业组织 ID（CorpId）；Client Secret 不要填成企业 CorpSecret</li>
            <li>在「开发配置 → 权限管理」申请 Contact.User.Read（必须）、Contact.User.mobile（按需），并确保应用已发布、具备基础调用权限（获取应用凭证必需）</li>
            <li>在「开发配置 → 安全设置 → 重定向URL（回调域名）」配置前端域名（如 http://localhost:5173）</li>
            <li>在「应用发布 → 版本管理与发布」创建版本并发布（非管理员需企业管理员审批）；若后台提示“版本发布后，当前修改才能生效”，必须先发布再测试</li>
            <li>返回本页填写 Client ID / Client Secret / CorpId / 回调地址并保存</li>
            <li>点击「连通性测试」验证，启用开关后员工即可扫码登录</li>
          </ol>
          <div class="dev-tip">
            本地调试：重定向URL（回调域名）可填 <code>http://localhost:5173</code>，
            回调地址填 <code>http://localhost:5173/dingtalk/callback</code>；
            生产环境必须替换为公网 HTTPS 域名。
          </div>
        </el-card>

        <el-card v-if="testResult" class="brand-card side-card test-card">
          <template #header>
            <div class="card-title">
              <el-icon :size="18" :color="testResult.ok ? '#10b981' : '#ef4444'">
                <circle-check v-if="testResult.ok" /><circle-close v-else />
              </el-icon>
              <span>测试结果</span>
            </div>
          </template>
          <div class="test-body">
            <el-tag :type="testResult.ok ? 'success' : 'danger'" effect="dark" round>
              {{ testResult.ok ? '配置有效' : '配置无效' }}
            </el-tag>
            <p class="test-detail">{{ testResult.detail }}</p>
          </div>
        </el-card>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { CircleCheck, CircleClose, InfoFilled, Setting } from '@element-plus/icons-vue'
import { getDingtalkConfig, testDingtalkConfig, updateDingtalkConfig } from '@/api/admin'
import type { DingTalkTestResult } from '@/api/types'
import AppLayout from '@/components/AppLayout.vue'

const formRef = ref<FormInstance>()
const saving = ref(false)
const testing = ref(false)
const testResult = ref<DingTalkTestResult | null>(null)
const secretPlaceholder = ref('')

const form = reactive({
  client_id: '',
  client_secret: '',
  corp_id: '',
  redirect_uri: '',
  enabled: false,
})

const rules: FormRules = {
  client_id: [{ required: true, message: '请输入 Client ID', trigger: 'blur' }],
  redirect_uri: [{ required: true, message: '请输入回调地址', trigger: 'blur' }],
}

onMounted(async () => {
  try {
    const data = await getDingtalkConfig()
    form.client_id = data.client_id
    form.corp_id = data.corp_id
    form.redirect_uri = data.redirect_uri
    form.enabled = data.enabled
    secretPlaceholder.value = data.client_secret_masked
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
})

async function onSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const data = await updateDingtalkConfig({ ...form })
    secretPlaceholder.value = data.client_secret_masked
    form.client_secret = ''
    ElMessage.success('配置已保存')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    saving.value = false
  }
}

async function onTest() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await testDingtalkConfig()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.config-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 20px;
  align-items: start;
}
.form-card {
  padding: 4px 8px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.6;
}
.enable-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.side-col {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.steps {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #4b5563;
  line-height: 2.1;
}
.steps a {
  color: var(--brand-primary);
  text-decoration: none;
}
.dev-tip {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
  font-size: 12px;
  line-height: 1.8;
}
.dev-tip code {
  padding: 1px 4px;
  border-radius: 4px;
  background: #dbeafe;
  font-size: 12px;
}
.test-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.test-detail {
  margin: 0;
  font-size: 13px;
  color: #4b5563;
  line-height: 1.7;
}

@media (max-width: 1000px) {
  .config-grid { grid-template-columns: 1fr; }
}
</style>
