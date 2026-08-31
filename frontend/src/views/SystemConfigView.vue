<template>
  <AppLayout>
    <!-- 英雄横幅 -->
    <div class="sys-hero">
      <div class="hero-glow glow-1"></div>
      <div class="hero-glow glow-2"></div>
      <div class="hero-grid"></div>
      <div class="hero-content">
        <div class="hero-left">
          <div class="hero-badge"><el-icon><setting /></el-icon> 平台核心配置</div>
          <h1 class="hero-title">系统配置</h1>
          <p class="hero-sub">由超级管理员维护 · 钉钉企业身份接入与 AI 大模型增强识别</p>
        </div>
        <div class="hero-stats">
          <div class="hero-stat">
            <span class="stat-dot" :class="dingtalk.enabled ? 'on' : 'off'"></span>
            <div><b>钉钉登录</b><small>{{ dingtalk.enabled ? '已启用' : '未启用' }}</small></div>
          </div>
          <div class="hero-stat">
            <span class="stat-dot" :class="ai.enabled ? 'on' : 'off'"></span>
            <div><b>AI 识别</b><small>{{ ai.enabled ? '已启用' : '未启用' }}</small></div>
          </div>
        </div>
      </div>
    </div>

    <div class="sys-body">
      <!-- 左侧导航 -->
      <aside class="sys-nav">
        <button class="nav-item" :class="{ active: tab === 'dingtalk' }" type="button" @click="tab = 'dingtalk'">
          <span class="nav-icon"><DingTalkIcon :size="30" /></span>
          <span class="nav-text">
            <strong>钉钉登录</strong>
            <small>扫码登录 · 企业统一身份</small>
          </span>
        </button>
        <button class="nav-item" :class="{ active: tab === 'ai' }" type="button" @click="tab = 'ai'">
          <span class="nav-icon"><el-icon :size="28" color="#7c3aed"><magic-stick /></el-icon></span>
          <span class="nav-text">
            <strong>AI 大模型</strong>
            <small>智能增强识别引擎</small>
          </span>
        </button>
        <div class="nav-tip">
          <el-icon><info-filled /></el-icon>
          <span>密钥均加密存储，读取时脱敏展示</span>
        </div>
      </aside>

      <!-- ==================== 钉钉登录 ==================== -->
      <section v-show="tab === 'dingtalk'" class="sys-main">
        <div class="main-grid">
          <el-card class="glass-card" shadow="never">
            <template #header>
              <div class="card-title">
                <el-icon :size="18" color="#2563eb"><key /></el-icon>
                <span>应用凭证</span>
                <el-tag :type="dingtalk.enabled ? 'success' : 'info'" size="small" effect="light" round class="title-tag">
                  {{ dingtalk.enabled ? '已启用' : '未启用' }}
                </el-tag>
              </div>
            </template>

            <el-form ref="dtFormRef" :model="dingtalk" :rules="dtRules" label-position="top">
              <el-form-item label="Client ID" prop="client_id">
                <el-input v-model="dingtalk.client_id" placeholder="钉钉开发者后台应用的 Client ID（原 AppKey）" clearable />
                <div class="form-tip">在开发者后台「基础信息 → 凭证与基础信息」获取</div>
              </el-form-item>
              <el-form-item label="Client Secret" prop="client_secret">
                <el-input
                  v-model="dingtalk.client_secret"
                  type="password"
                  :placeholder="secretPlaceholder || '请输入应用 Client Secret（原 AppSecret）'"
                  show-password
                  clearable
                />
                <div class="form-tip">
                  必须填应用详情「基础信息 → 凭证与基础信息」中的 <b>Client Secret</b>；<b>不要填企业 CorpSecret</b>。
                  已加密存储；留空表示沿用旧值（当前：{{ secretPlaceholder || '未设置' }}）
                </div>
              </el-form-item>
              <el-form-item label="企业组织 ID（CorpId）" prop="corp_id">
                <el-input v-model="dingtalk.corp_id" placeholder="钉钉企业组织 ID（CorpId）" clearable />
                <div class="form-tip">在钉钉开发者后台首页或应用详情「基础信息 → 凭证与基础信息」获取；连通性测试需要</div>
              </el-form-item>
              <el-form-item label="回调地址" prop="redirect_uri">
                <el-input v-model="dingtalk.redirect_uri" placeholder="https://your-domain/dingtalk/callback" clearable />
                <div class="form-tip">需与开发者后台「重定向URL（回调域名）」同源；本系统回调路径固定为 /dingtalk/callback</div>
              </el-form-item>
              <el-form-item label="启用钉钉登录">
                <div class="enable-row">
                  <el-switch v-model="dingtalk.enabled" />
                  <span class="enable-desc">启用后，企业员工可通过钉钉扫码登录本系统</span>
                </div>
              </el-form-item>
              <el-form-item class="action-row">
                <el-button type="primary" :loading="dtSaving" @click="onSaveDingtalk">保存配置</el-button>
                <el-button :loading="dtTesting" @click="onTestDingtalk">连通性测试</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <div class="side-col">
            <transition name="fade-up">
              <el-card v-if="dtTestResult" class="glass-card test-card" shadow="never">
                <template #header>
                  <div class="card-title">
                    <el-icon :size="18" :color="dtTestResult.ok ? '#10b981' : '#ef4444'">
                      <circle-check v-if="dtTestResult.ok" /><circle-close v-else />
                    </el-icon>
                    <span>测试结果</span>
                  </div>
                </template>
                <div class="test-body">
                  <el-tag :type="dtTestResult.ok ? 'success' : 'danger'" effect="dark" round>
                    {{ dtTestResult.ok ? '配置有效' : '配置无效' }}
                  </el-tag>
                  <p class="test-detail">{{ dtTestResult.detail }}</p>
                </div>
              </el-card>
            </transition>

            <el-card class="glass-card" shadow="never">
              <template #header>
                <div class="card-title">
                  <el-icon :size="18" color="#06b6d4"><guide /></el-icon>
                  <span>配置指引（官方流程）</span>
                </div>
              </template>
              <ol class="steps">
                <li>登录<a href="https://open-dev.dingtalk.com" target="_blank" rel="noopener">钉钉开发者后台</a> → 应用开发 → 企业内部应用 → 创建应用</li>
                <li>在「基础信息 → 凭证与基础信息」获取 Client ID、应用 Client Secret（原 AppSecret）与企业组织 ID（CorpId）；Client Secret 不要填成企业 CorpSecret</li>
                <li>在「开发配置 → 权限管理」申请 Contact.User.Read（必须）、Contact.User.mobile（按需），并确保应用已发布、具备基础调用权限（获取应用凭证必需）</li>
                <li>在「开发配置 → 安全设置 → 重定向URL（回调域名）」配置前端域名（如 http://localhost:5173）</li>
                <li>在「应用发布 → 版本管理与发布」创建版本并发布（非管理员需企业管理员审批）；若后台提示“版本发布后，当前修改才能生效”，必须先发布再测试</li>
                <li>返回本页填写凭证并保存，点击「连通性测试」验证，启用开关后员工即可扫码登录</li>
              </ol>
              <div class="dev-tip">
                本地调试：重定向URL（回调域名）可填 <code>http://localhost:5173</code>，
                回调地址填 <code>http://localhost:5173/dingtalk/callback</code>；
                生产环境必须替换为公网 HTTPS 域名。
              </div>
            </el-card>
          </div>
        </div>
      </section>

      <!-- ==================== AI 大模型 ==================== -->
      <section v-show="tab === 'ai'" class="sys-main">
        <div class="main-grid">
          <el-card class="glass-card" shadow="never">
            <template #header>
              <div class="card-title">
                <el-icon :size="18" color="#7c3aed"><cpu /></el-icon>
                <span>模型接入</span>
                <el-tag :type="ai.enabled ? 'success' : 'info'" size="small" effect="light" round class="title-tag">
                  {{ ai.enabled ? '已启用' : '未启用' }}
                </el-tag>
              </div>
            </template>

            <el-form ref="aiFormRef" :model="ai" :rules="aiRules" label-position="top">
              <el-form-item label="启用 AI 增强识别">
                <div class="enable-row">
                  <el-switch v-model="ai.enabled" />
                  <span class="enable-desc">开启后合同扫描叠加 AI 风险识别；未配置或调用失败时自动降级为纯规则识别</span>
                </div>
              </el-form-item>
              <el-form-item label="API 地址" prop="api_base">
                <el-input v-model="ai.api_base" placeholder="https://api.openai.com/v1" clearable />
                <div class="form-tip">OpenAI 兼容 Chat Completions 接口（含 /v1），企业私有化模型同样适用</div>
              </el-form-item>
              <el-form-item label="API Key" prop="api_key">
                <el-input
                  v-model="ai.api_key"
                  type="password"
                  show-password
                  clearable
                  :placeholder="apiKeyPlaceholder || '请输入 API Key'"
                />
                <div class="form-tip">加密存储、读取脱敏；留空表示沿用旧值（当前：{{ apiKeyPlaceholder || '未设置' }}）</div>
              </el-form-item>
              <el-form-item label="模型名称" prop="model">
                <el-input v-model="ai.model" placeholder="gpt-4o-mini" clearable />
              </el-form-item>

              <div class="section-divider"><span>高级参数</span></div>

              <div class="num-grid">
                <el-form-item label="超时（秒）" prop="timeout_seconds">
                  <el-input-number v-model="ai.timeout_seconds" :min="5" :max="300" controls-position="right" style="width: 100%" />
                </el-form-item>
                <el-form-item label="上下文长度（字符）" prop="context_chars">
                  <el-input-number v-model="ai.context_chars" :min="1000" :max="200000" :step="1000" controls-position="right" style="width: 100%" />
                </el-form-item>
                <el-form-item label="最大发现数" prop="max_findings">
                  <el-input-number v-model="ai.max_findings" :min="1" :max="100" controls-position="right" style="width: 100%" />
                </el-form-item>
              </div>

              <el-form-item class="action-row">
                <el-button type="primary" :loading="aiSaving" @click="onSaveAI">保存配置</el-button>
                <el-button :loading="aiTesting" @click="onTestAI">连通性测试</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <div class="side-col">
            <transition name="fade-up">
              <el-card v-if="aiTestMessage" class="glass-card test-card" shadow="never">
                <template #header>
                  <div class="card-title">
                    <el-icon :size="18" :color="aiTestOk ? '#10b981' : '#ef4444'">
                      <circle-check v-if="aiTestOk" /><circle-close v-else />
                    </el-icon>
                    <span>测试结果</span>
                  </div>
                </template>
                <div class="test-body">
                  <el-tag :type="aiTestOk ? 'success' : 'danger'" effect="dark" round>
                    {{ aiTestOk ? '连接成功' : '连接失败' }}
                  </el-tag>
                  <p class="test-detail">{{ aiTestMessage }}</p>
                </div>
              </el-card>
            </transition>

            <el-card class="glass-card" shadow="never">
              <template #header>
                <div class="card-title">
                  <el-icon :size="18" color="#7c3aed"><magic-stick /></el-icon>
                  <span>AI 识别工作机制</span>
                </div>
              </template>
              <ul class="mech-list">
                <li>
                  <span class="mech-dot dot-purple"></span>
                  <div><b>双引擎识别</b><small>规则关键词匹配为基础层，AI 在此之上补充语义级风险</small></div>
                </li>
                <li>
                  <span class="mech-dot dot-blue"></span>
                  <div><b>结构化输出</b><small>返回风险级别 / 命中内容 / 上下文 / 整改建议</small></div>
                </li>
                <li>
                  <span class="mech-dot dot-cyan"></span>
                  <div><b>安全降级</b><small>未配置 / 超时 / 异常时自动回退纯规则，扫描不中断</small></div>
                </li>
                <li>
                  <span class="mech-dot dot-amber"></span>
                  <div><b>数据合规</b><small>合同文本将发送给模型服务，生产建议使用企业私有化模型</small></div>
                </li>
              </ul>
            </el-card>
          </div>
        </div>
      </section>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  CircleCheck,
  CircleClose,
  Cpu,
  Guide,
  InfoFilled,
  Key,
  MagicStick,
  Setting,
} from '@element-plus/icons-vue'
import {
  getAIConfig,
  getDingtalkConfig,
  testAIConfig,
  testDingtalkConfig,
  updateAIConfig,
  updateDingtalkConfig,
} from '@/api/admin'
import type { DingTalkTestResult } from '@/api/types'
import AppLayout from '@/components/AppLayout.vue'
import DingTalkIcon from '@/components/DingTalkIcon.vue'

type Tab = 'dingtalk' | 'ai'
const tab = ref<Tab>('dingtalk')

/* ==================== 钉钉 ==================== */
const dtFormRef = ref<FormInstance>()
const dtSaving = ref(false)
const dtTesting = ref(false)
const dtTestResult = ref<DingTalkTestResult | null>(null)
const secretPlaceholder = ref('')

const dingtalk = reactive({
  client_id: '',
  client_secret: '',
  corp_id: '',
  redirect_uri: '',
  enabled: false,
})

const dtRules: FormRules = {
  client_id: [{ required: true, message: '请输入 Client ID', trigger: 'blur' }],
  redirect_uri: [{ required: true, message: '请输入回调地址', trigger: 'blur' }],
}

async function loadDingtalk() {
  try {
    const data = await getDingtalkConfig()
    dingtalk.client_id = data.client_id
    dingtalk.corp_id = data.corp_id
    dingtalk.redirect_uri = data.redirect_uri
    dingtalk.enabled = data.enabled
    secretPlaceholder.value = data.client_secret_masked
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onSaveDingtalk() {
  const valid = await dtFormRef.value?.validate().catch(() => false)
  if (!valid) return
  dtSaving.value = true
  try {
    const data = await updateDingtalkConfig({ ...dingtalk })
    secretPlaceholder.value = data.client_secret_masked
    dingtalk.client_secret = ''
    ElMessage.success('钉钉配置已保存')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    dtSaving.value = false
  }
}

async function onTestDingtalk() {
  dtTesting.value = true
  dtTestResult.value = null
  try {
    dtTestResult.value = await testDingtalkConfig()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    dtTesting.value = false
  }
}

/* ==================== AI ==================== */
const aiFormRef = ref<FormInstance>()
const aiSaving = ref(false)
const aiTesting = ref(false)
const aiTestMessage = ref('')
const aiTestOk = ref(false)
const apiKeyOldMasked = ref('')

const ai = reactive({
  enabled: false,
  api_base: 'https://api.openai.com/v1',
  api_key: '',
  model: 'gpt-4o-mini',
  timeout_seconds: 30,
  context_chars: 30000,
  max_findings: 50,
})

const apiKeyPlaceholder = computed(() => apiKeyOldMasked.value)

const aiRules: FormRules = {
  api_base: [{ required: true, message: '请输入 API 地址', trigger: 'blur' }],
  model: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
}

async function loadAI() {
  try {
    const data = await getAIConfig()
    ai.enabled = data.enabled
    ai.api_base = data.api_base
    ai.model = data.model
    ai.timeout_seconds = data.timeout_seconds
    ai.context_chars = data.context_chars
    ai.max_findings = data.max_findings
    apiKeyOldMasked.value = data.api_key_masked
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onSaveAI() {
  const valid = await aiFormRef.value?.validate().catch(() => false)
  if (!valid) return
  aiSaving.value = true
  try {
    const data = await updateAIConfig({
      enabled: ai.enabled,
      api_base: ai.api_base,
      api_key: ai.api_key,
      model: ai.model,
      timeout_seconds: ai.timeout_seconds,
      context_chars: ai.context_chars,
      max_findings: ai.max_findings,
    })
    apiKeyOldMasked.value = data.api_key_masked
    ai.api_key = ''
    aiTestMessage.value = ''
    ElMessage.success('AI 配置已保存')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    aiSaving.value = false
  }
}

async function onTestAI() {
  aiTesting.value = true
  aiTestMessage.value = ''
  try {
    const result = await testAIConfig()
    aiTestOk.value = result.ok
    aiTestMessage.value = result.detail
  } catch (e) {
    aiTestOk.value = false
    aiTestMessage.value = (e as Error).message
  } finally {
    aiTesting.value = false
  }
}

onMounted(() => {
  void loadDingtalk()
  void loadAI()
})
</script>

<style scoped>
/* ==================== 英雄横幅 ==================== */
.sys-hero {
  position: relative;
  border-radius: 18px;
  padding: 34px 38px;
  margin-bottom: 24px;
  overflow: hidden;
  background:
    radial-gradient(520px 260px at 88% -30%, rgba(124, 58, 237, 0.14), transparent 62%),
    radial-gradient(480px 260px at 6% 140%, rgba(6, 182, 212, 0.13), transparent 62%),
    linear-gradient(120deg, #eef4ff 0%, #f5f8ff 55%, #faf7ff 100%);
  border: 1px solid rgba(37, 99, 235, 0.14);
  box-shadow: 0 10px 30px rgba(37, 99, 235, 0.08);
}
.hero-glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}
.glow-1 {
  width: 320px;
  height: 320px;
  right: -70px;
  top: -140px;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.12), transparent 65%);
}
.glow-2 {
  width: 240px;
  height: 240px;
  left: -50px;
  bottom: -130px;
  background: radial-gradient(circle, rgba(124, 58, 237, 0.10), transparent 65%);
}
.hero-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(37, 99, 235, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(37, 99, 235, 0.05) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: radial-gradient(640px 300px at 30% 0%, #000, transparent 80%);
  pointer-events: none;
}
.hero-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.09);
  border: 1px solid rgba(37, 99, 235, 0.2);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1px;
  backdrop-filter: blur(6px);
}
.hero-title {
  margin: 12px 0 8px;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: 2px;
  background: linear-gradient(90deg, #1d4ed8, #7c3aed);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.hero-sub {
  margin: 0;
  font-size: 13.5px;
  color: #64748b;
  letter-spacing: 0.5px;
}
.hero-stats {
  display: flex;
  gap: 14px;
}
.hero-stat {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(37, 99, 235, 0.14);
  backdrop-filter: blur(8px);
  color: #0f172a;
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.07);
}
.hero-stat b {
  display: block;
  font-size: 14px;
  font-weight: 700;
}
.hero-stat small {
  display: block;
  margin-top: 2px;
  font-size: 11.5px;
  color: #64748b;
}
.stat-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.stat-dot.on {
  background: #10b981;
  box-shadow: 0 0 0 5px rgba(16, 185, 129, 0.15);
}
.stat-dot.off {
  background: #cbd5e1;
}

/* ==================== 主体布局 ==================== */
.sys-body {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 20px;
  align-items: start;
}

/* 左侧导航 */
.sys-nav {
  position: sticky;
  top: 80px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.85);
  cursor: pointer;
  text-align: left;
  transition: all 0.22s ease;
  position: relative;
  overflow: hidden;
}
.nav-item:hover {
  border-color: rgba(37, 99, 235, 0.35);
  box-shadow: 0 8px 22px rgba(37, 99, 235, 0.1);
}
.nav-item.active {
  background: linear-gradient(120deg, rgba(37, 99, 235, 0.09), rgba(124, 58, 237, 0.07));
  border-color: rgba(37, 99, 235, 0.4);
  box-shadow: 0 10px 26px rgba(37, 99, 235, 0.13);
}
.nav-icon {
  width: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.nav-text strong {
  display: block;
  font-size: 14.5px;
  color: #0f172a;
  font-weight: 700;
}
.nav-text small {
  display: block;
  margin-top: 3px;
  font-size: 11.5px;
  color: #94a3b8;
}
.nav-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 12px;
  background: linear-gradient(120deg, rgba(6, 182, 212, 0.08), rgba(37, 99, 235, 0.06));
  border: 1px solid rgba(6, 182, 212, 0.18);
  color: #0e7490;
  font-size: 12px;
  line-height: 1.6;
}
.nav-tip .el-icon {
  margin-top: 2px;
  flex-shrink: 0;
}

/* ==================== 内容区 ==================== */
.main-grid {
  display: grid;
  grid-template-columns: 1.45fr 1fr;
  gap: 20px;
  align-items: start;
}
.glass-card {
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px);
  padding: 4px 8px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #0f172a;
  font-size: 14px;
}
.title-tag {
  margin-left: auto;
}
.enable-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.enable-desc {
  font-size: 12.5px;
  color: #64748b;
}
.action-row {
  margin-top: 6px;
  margin-bottom: 0;
}
.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.6;
}

/* 高级参数分隔线 */
.section-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 6px 0 16px;
  color: #94a3b8;
  font-size: 12px;
  letter-spacing: 2px;
}
.section-divider::before,
.section-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(148, 163, 184, 0.35), transparent);
}
.num-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

/* ==================== 右侧说明列 ==================== */
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
  line-height: 2.05;
}
.steps a {
  color: var(--brand-primary);
  text-decoration: none;
}
.dev-tip {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: linear-gradient(120deg, #eff6ff, #f5f3ff);
  border: 1px solid rgba(191, 219, 254, 0.8);
  color: #1e40af;
  font-size: 12px;
  line-height: 1.8;
}
.dev-tip code {
  padding: 1px 5px;
  border-radius: 5px;
  background: rgba(37, 99, 235, 0.1);
  font-size: 12px;
}

/* 测试结果卡 */
.test-card {
  border: 1px solid rgba(37, 99, 235, 0.2);
  background: linear-gradient(140deg, #ffffff, #f8faff);
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.08);
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
  word-break: break-all;
}

/* AI 机制说明 */
.mech-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.mech-list li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.mech-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 4px;
  flex-shrink: 0;
}
.dot-purple { background: #7c3aed; box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.12); }
.dot-blue { background: #2563eb; box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12); }
.dot-cyan { background: #06b6d4; box-shadow: 0 0 0 4px rgba(6, 182, 212, 0.12); }
.dot-amber { background: #f59e0b; box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.12); }
.mech-list b {
  display: block;
  font-size: 13.5px;
  color: #0f172a;
}
.mech-list small {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}

/* 过渡动画 */
.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.3s ease;
}
.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 1100px) {
  .sys-body { grid-template-columns: 1fr; }
  .sys-nav { position: static; flex-direction: row; flex-wrap: wrap; }
  .nav-item { flex: 1; min-width: 220px; }
  .nav-tip { display: none; }
  .main-grid { grid-template-columns: 1fr; }
  .num-grid { grid-template-columns: 1fr; }
  .hero-stats { width: 100%; }
  .hero-stat { flex: 1; }
}
</style>
