<template>
  <div class="login-page">
    <!-- 左侧品牌区（浅色，说明系统用途） -->
    <section class="brand-panel">
      <div class="brand-inner">
        <div class="brand-logo">
          <ContractIcon :size="34" color="#fff" />
        </div>
        <h1 class="brand-title">合同风险扫描系统</h1>
        <p class="brand-slogan">智能识别合同风险 · 守护企业权益</p>
        <ul class="brand-features">
          <li>
            <span class="feature-dot" />
            <span>钉钉企业身份一键登录</span>
          </li>
          <li>
            <span class="feature-dot" />
            <span>合同上传解析 · 风险智能扫描</span>
          </li>
          <li>
            <span class="feature-dot" />
            <span>企业级安全 · 全程审计留痕</span>
          </li>
        </ul>
      </div>
    </section>

    <!-- 右侧登录区（浅色卡片，无边框） -->
    <section class="form-panel">
      <div class="login-card" v-loading="loadingMethods">
        <!-- 钉钉扫码登录（默认内嵌官方二维码，不自动跳转） -->
        <template v-if="mode === 'dingtalk'">
          <div class="card-head center">
            <DingTalkIcon :size="56" class="dingtalk-icon" />
            <h2>钉钉扫码登录</h2>
            <p>使用企业钉钉账号扫码登录</p>
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
            <a class="switch-link" @click="onSwitchToLocal">超管登录 →</a>
          </div>
        </template>

        <!-- 超管本地登录 -->
        <template v-else>
          <div class="card-head">
            <h2>超管登录</h2>
            <p>使用管理员账号登录系统</p>
          </div>
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
import { Lock, RefreshRight, User } from '@element-plus/icons-vue'
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
.login-page {
  min-height: 100vh;
  display: flex;
  background: linear-gradient(135deg, #eef4ff 0%, #f8fafc 55%, #f1f5f9 100%);
  color: #0f172a;
}

/* ===== 左侧品牌区（浅色，高级感） ===== */
.brand-panel {
  flex: 1.1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #eaf2ff 0%, #f8fbff 100%);
}
.brand-inner {
  max-width: 440px;
  padding: 40px;
}
.brand-logo {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.25);
}
.brand-title {
  margin: 0 0 10px;
  font-size: 30px;
  font-weight: 700;
  color: #0f172a;
}
.brand-slogan {
  margin: 0 0 36px;
  font-size: 14px;
  color: #64748b;
  letter-spacing: 1px;
}
.brand-features {
  list-style: none;
  margin: 0;
  padding: 0;
}
.brand-features li {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #475569;
}
.feature-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #3b82f6;
}

/* ===== 右侧登录区（浅色卡片，无边框） ===== */
.form-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.login-card {
  width: 100%;
  max-width: 420px;
  padding: 40px 40px 20px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
}
.card-head {
  margin-bottom: 20px;
}
.card-head.center {
  text-align: center;
}
.card-head h2 {
  margin: 12px 0 6px;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}
.card-head p {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
}
.dingtalk-icon {
  display: inline-block;
}

/* ===== 二维码区域（无边框） ===== */
.qr-area {
  min-height: 380px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.qr-error {
  margin: 0 0 14px;
  font-size: 13px;
  color: #dc2626;
  text-align: center;
  word-break: break-all;
}

.login-card :deep(.el-form-item__label) {
  color: #334155;
}
.login-btn {
  width: 100%;
  margin-top: 8px;
  border-radius: 10px;
  letter-spacing: 4px;
  background: linear-gradient(90deg, #2563eb, #3b82f6);
  border: none;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.22);
}
.login-btn:hover {
  background: linear-gradient(90deg, #1d4ed8, #2563eb);
}
.switch-row {
  margin-top: 18px;
  text-align: center;
}
.switch-link {
  font-size: 13px;
  color: #3b82f6;
  cursor: pointer;
  text-decoration: none;
}
.switch-link:hover {
  color: #2563eb;
  text-decoration: underline;
}
.login-footer {
  margin-top: 20px;
  font-size: 12px;
  color: #94a3b8;
}
</style>

