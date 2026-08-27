<template>
  <div class="login-page">
    <!-- 左侧品牌与核心价值区 -->
    <section class="brand-panel">
      <div class="brand-inner">
        <div class="brand-logo">
          <ContractIcon :size="34" color="#fff" />
        </div>
        <h1 class="brand-title">合同风险扫描系统</h1>
        <p class="brand-slogan">AI 驱动的企业级合同风险智能识别平台</p>

        <ul class="brand-features">
          <li class="feature-card">
            <span class="feature-icon"><Search /></span>
            <div>
              <strong>智能识别</strong>
              <small>AI 驱动 · 合同风险智能扫描</small>
            </div>
          </li>
          <li class="feature-card">
            <span class="feature-icon"><Document /></span>
            <div>
              <strong>高效协同</strong>
              <small>上传解析 · 全流程风险管控</small>
            </div>
          </li>
          <li class="feature-card">
            <span class="feature-icon"><Lock /></span>
            <div>
              <strong>安全可信</strong>
              <small>钉钉企业身份 · 全程审计留痕</small>
            </div>
          </li>
        </ul>
      </div>
    </section>

    <!-- 右侧登录区 -->
    <section class="form-panel">
      <div class="login-card" v-loading="loadingMethods">
        <!-- 钉钉扫码登录（默认内嵌官方二维码，不自动跳转） -->
        <template v-if="mode === 'dingtalk'">
          <div class="card-head center dingtalk-head">
            <DingTalkIcon :size="20" class="dingtalk-icon" />
            <h2>钉钉扫码登录</h2>
          </div>

          <div class="qr-area" v-loading="dingtalkLoading">
            <template v-if="qrError">
              <p class="qr-error">{{ qrError }}</p>
              <el-button size="small" :icon="RefreshRight" @click="onRetryQr">重新加载</el-button>
            </template>
            <DingtalkQrLogin
              v-else-if="authorizeUrl"
              :key="qrKey"
              :authorize-url="authorizeUrl"
              @success="onDingtalkSuccess"
              @error="onDingtalkError"
            />
          </div>

          <div class="switch-row">
            <button class="switch-pill" type="button" @click="onSwitchToLocal">
              <Lock class="switch-pill-icon" />
              超管登录
            </button>
          </div>
        </template>

        <!-- 超管本地登录 -->
        <template v-else>
          <div class="card-head center admin-head">
            <span class="admin-icon-wrap"><Lock /></span>
            <h2>管理员登录</h2>
            <p>账号仅限系统管理员使用</p>
          </div>
          <div class="form-divider"></div>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-position="top"
            size="large"
            @keyup.enter="onLogin"
          >
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" clearable />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                :prefix-icon="Lock"
                show-password
              />
            </el-form-item>
            <el-button type="primary" class="login-btn" size="large" :loading="loading" @click="onLogin">
              登 录
            </el-button>
          </el-form>
          <div v-if="dingtalkEnabled" class="switch-row">
            <a class="switch-link" @click="onSwitchToDingtalk">← 返回钉钉登录</a>
          </div>
        </template>
      </div>
      <div class="login-footer">&copy; 2026 合同风险扫描系统 · 企业版 v0.1.0</div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Document, Lock, RefreshRight, Search, User } from '@element-plus/icons-vue'
import {
  dingtalkCallback,
  getDingtalkAuthorizeUrl,
  getLoginMethods,
  login,
} from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import ContractIcon from '@/components/ContractIcon.vue'
import DingTalkIcon from '@/components/DingTalkIcon.vue'
import DingtalkQrLogin from '@/components/DingtalkQrLogin.vue'

type LoginMode = 'dingtalk' | 'local'

interface DingtalkLoginResult {
  redirectUrl: string
  authCode: string
  state: string
}

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const dingtalkLoading = ref(false)
const loadingMethods = ref(true)
const qrError = ref('')
const qrKey = ref(0)
const authorizeUrl = ref('')
const mode = ref<LoginMode>('local')
const dingtalkEnabled = ref(false)
const form = reactive({ username: '', password: '' })

/** 扫码回调处理中标记：防止重复消息触发多次登录请求 */
const processing = ref(false)

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

onMounted(async () => {
  try {
    const data = await getLoginMethods()
    dingtalkEnabled.value = data.dingtalk_enabled
    if (data.dingtalk_enabled) {
      mode.value = 'dingtalk'
      await initDingtalkQr()
    } else {
      mode.value = 'local'
    }
  } catch {
    mode.value = 'local'
  } finally {
    loadingMethods.value = false
  }
})

/**
 * 初始化内嵌二维码：获取钉钉授权 URL（含一次性 state）。
 * 组件在该 URL 上追加 iframe=true，在登录页内渲染官方二维码；扫码成功后
 * 组件回传 authCode，本页直接完成登录，不跳转页面。
 */
async function initDingtalkQr() {
  qrError.value = ''
  dingtalkLoading.value = true
  try {
    const data = await getDingtalkAuthorizeUrl()
    authorizeUrl.value = data.authorize_url
    qrKey.value += 1
    await nextTick()
  } catch (e) {
    qrError.value = (e as Error).message || '钉钉登录参数加载失败'
  } finally {
    dingtalkLoading.value = false
  }
}

/** 扫码成功：用 authCode + state 调用后端完成登录（不跳转页面） */
async function onDingtalkSuccess(result: DingtalkLoginResult) {
  if (processing.value) return
  processing.value = true
  try {
    const data = await dingtalkCallback(result.authCode, result.state)
    auth.setTokens(data)
    ElMessage.success('登录成功')
    router.push(
      data.user.must_change_password
        ? { name: 'change-password' }
        : (route.query.redirect as string) || '/',
    )
  } catch (e) {
    processing.value = false
    ElMessage.error((e as Error).message)
    void initDingtalkQr()
  }
}

/** 二维码/授权失败（仅展示带具体原因的错误） */
function onDingtalkError(message: string) {
  qrError.value = message
}

function onSwitchToLocal() {
  mode.value = 'local'
}

async function onSwitchToDingtalk() {
  mode.value = 'dingtalk'
  await initDingtalkQr()
}

function onRetryQr() {
  void initDingtalkQr()
}

async function onLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const data = await login(form.username, form.password)
    auth.setTokens(data)
    ElMessage.success('登录成功')
    router.push(
      data.user.must_change_password
        ? { name: 'change-password' }
        : (route.query.redirect as string) || '/',
    )
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ===== 页面：浅色未来科技感背景（网格 + 光晕） ===== */
.login-page {
  position: relative;
  overflow: hidden;
  min-height: 100vh;
  display: flex;
  background:
    radial-gradient(720px 460px at 12% 18%, rgba(59, 130, 246, 0.16), transparent 62%),
    radial-gradient(620px 460px at 88% 82%, rgba(124, 58, 237, 0.12), transparent 62%),
    linear-gradient(135deg, #f7faff 0%, #eef4ff 48%, #f8fafc 100%);
  color: #0f172a;
}
.login-page::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(37, 99, 235, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(37, 99, 235, 0.05) 1px, transparent 1px);
  background-size: 42px 42px;
  pointer-events: none;
}

/* ===== 左侧品牌与核心价值 ===== */
.brand-panel {
  position: relative;
  flex: 1.15;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 40px;
}
.brand-inner {
  width: 100%;
  max-width: 460px;
}
.brand-logo {
  width: 62px;
  height: 62px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 22px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow: 0 14px 34px rgba(37, 99, 235, 0.32);
}
.brand-title {
  margin: 0 0 10px;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: 2px;
  background: linear-gradient(90deg, #1e3a8a, #2563eb);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.brand-slogan {
  margin: 0 0 32px;
  font-size: 14px;
  color: #64748b;
  letter-spacing: 1px;
}

.brand-features {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}
.feature-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.62);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
}
.feature-icon {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  background: rgba(37, 99, 235, 0.1);
}
.feature-card strong {
  display: block;
  font-size: 13.5px;
  color: #0f172a;
}
.feature-card small {
  display: block;
  margin-top: 2px;
  font-size: 11.5px;
  color: #64748b;
}

/* ===== 右侧登录区 ===== */
.form-panel {
  position: relative;
  flex: 0.8;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.login-card {
  width: 100%;
  max-width: 364px;
  padding: 26px 32px 20px;
  background: #fff;
  border-radius: 18px;
  box-shadow:
    0 0 0 1px rgba(37, 99, 235, 0.06),
    0 24px 64px rgba(37, 99, 235, 0.12);
}
.card-head {
  margin-bottom: 14px;
}
.card-head.center {
  text-align: center;
}
.dingtalk-head {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 10px;
  line-height: 1;
}
.dingtalk-head h2 {
  margin: 0;
  font-size: 16px;
  line-height: 1;
}
.dingtalk-icon {
  display: block;
}
.card-head h2 {
  margin: 10px 0 4px;
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #0f172a;
}
.card-head p {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}
.admin-head {
  margin-bottom: 14px;
}
.admin-head h2 {
  font-size: 21px;
  letter-spacing: 2px;
}
.admin-icon-wrap {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow:
    0 0 0 8px rgba(37, 99, 235, 0.08),
    0 14px 28px rgba(37, 99, 235, 0.28);
}
.form-divider {
  height: 1px;
  margin: 0 0 16px;
  background: linear-gradient(90deg, transparent, #e2e8f0 18%, #e2e8f0 82%, transparent);
}

/* ===== 二维码区域 ===== */
.qr-area {
  min-height: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 12px;
}
.qr-error {
  margin: 0 0 14px;
  font-size: 13px;
  color: #dc2626;
  text-align: center;
  word-break: break-all;
}

/* ===== 超管入口（胶囊按钮） ===== */
.switch-row {
  margin-top: 14px;
  text-align: center;
}
.switch-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  line-height: 1;
  padding: 10px 22px;
  border: none;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}
.switch-pill:hover {
  background: rgba(37, 99, 235, 0.16);
  color: #1d4ed8;
}
.switch-pill-icon {
  width: 16px;
  height: 16px;
}

/* ===== 表单与按钮 ===== */
.login-card :deep(.el-form-item) {
  margin-bottom: 16px;
}
.login-card :deep(.el-form-item__label) {
  padding-bottom: 4px;
  font-size: 12.5px;
  color: #64748b;
  font-weight: 500;
}
.login-card :deep(.el-input__wrapper) {
  border-radius: 10px;
  background: #f8fafc;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
}
.login-card :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #bfdbfe inset;
}
.login-card :deep(.el-input__wrapper) {
  border-radius: 10px;
  background: #f8fafc;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
}
.login-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #2563eb inset;
}
.login-btn {
  width: 100%;
  height: 44px;
  margin-top: 6px;
  border: none;
  border-radius: 12px;
  letter-spacing: 4px;
  background: linear-gradient(90deg, #2563eb, #7c3aed);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.28);
}
.login-btn:hover {
  background: linear-gradient(90deg, #1d4ed8, #6d28d9);
}

.login-footer {
  margin-top: 18px;
  font-size: 12px;
  color: #94a3b8;
}

@media (max-width: 860px) {
  .login-page {
    flex-direction: column;
  }
  .brand-panel {
    display: none;
  }
}
</style>

