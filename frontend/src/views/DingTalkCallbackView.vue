<template>
  <div class="callback-page brand-gradient">
    <div class="callback-card">
      <div class="spin-logo">
        <el-icon :size="26" color="#fff"><document-checked /></el-icon>
      </div>
      <el-icon class="loading-icon" :size="28" color="#2563eb"><loading /></el-icon>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DocumentChecked, Loading } from '@element-plus/icons-vue'
import { dingtalkCallback } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

/**
/**
 * 钉钉授权回调页（顶层跳转流）：钉钉授权成功后带 authCode+state 回跳本页，
 * 本页读取 URL 参数调用后端完成登录。
 * 若被第三方 iframe 加载（防御性兼容），仅作静态承载页，不重复登录。
 */
const inIframe = window.self !== window.top
const hasError = Boolean(route.query.error)

/** iframe 内仅作承载页：根据回调参数展示准确状态（登录由父页面完成） */
const title = inIframe
  ? (hasError ? '授权未完成' : '授权成功')
  : '正在完成钉钉登录'
const description = inIframe
  ? (hasError ? '钉钉授权未完成，请在登录页重新扫码' : '正在为您完成登录，请勿关闭当前页面…')
  : '正在验证您的身份，请稍候…'

onMounted(async () => {
  if (inIframe) return

  // 传统跳转授权流：成功回跳携带 authCode+state，拒绝/失败携带 error
  const error = String(route.query.error ?? '')
  const authCode = String(route.query.authCode ?? '')
  const state = String(route.query.state ?? '')
  if (error) {
    ElMessage.error('钉钉授权未完成，请重试')
    router.replace({ name: 'login' })
    return
  }
  if (!authCode || !state) {
    ElMessage.error('钉钉登录回调参数缺失')
    router.replace({ name: 'login' })
    return
  }
  try {
    const data = await dingtalkCallback(authCode, state)
    auth.setTokens(data)
    ElMessage.success('登录成功')
    router.replace(
      data.user.must_change_password ? { name: 'change-password' } : { name: 'home' },
    )
  } catch (e) {
    ElMessage.error((e as Error).message)
    router.replace({ name: 'login' })
  }
})
</script>

<style scoped>
.callback-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.callback-card {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 16px;
  padding: 48px 36px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.3);
  position: relative;
}
.spin-logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 20px;
  border-radius: 14px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.4);
}
.loading-icon {
  position: absolute;
  right: 26px;
  top: 26px;
}
.callback-card h2 {
  margin: 0 0 8px;
  font-size: 20px;
  color: #111827;
}
.callback-card p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}
</style>
