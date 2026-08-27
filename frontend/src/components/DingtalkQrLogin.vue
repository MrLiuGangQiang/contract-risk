<template>
  <div ref="containerRef" class="dingtalk-qr-container" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

/**
 * 钉钉内嵌二维码登录组件。
 *
 * 复用后端 /auth/dingtalk/authorize-url 返回的完整授权 URL，仅追加 iframe=true，
 * 由钉钉官方登录页在 iframe 内渲染二维码；监听 postMessage 协议获取 authCode。
 * 说明：钉钉 iframe 模式不会检测本机 PC 客户端（平台白名单限制），因此不会显示本机头像。
 */
interface DingtalkLoginResult {
  redirectUrl: string
  authCode: string
  state: string
}

const props = defineProps<{ authorizeUrl: string }>()
const emit = defineEmits<{
  success: [result: DingtalkLoginResult]
  error: [message: string]
}>()

const containerRef = ref<HTMLElement>()

/** 钉钉登录 iframe 固定来源（只接受该来源的消息） */
const DINGTALK_LOGIN_ORIGIN = 'https://login.dingtalk.com'
/** 二维码容器尺寸（需容纳二维码 / 钉钉页面提示区域） */
const QR_WIDTH = 300
const QR_HEIGHT = 400
/** 与钉钉新版 SDK 保持一致的 iframe name，部分新页面依赖该标记 */
const IFRAME_NAME = 'dingtalk-login_iframe-scan'

/** 从 URL 中解析查询参数（authCode/state/error） */
function parseParam(url: string, name: string): string {
  const match = url.match(new RegExp(`[?&]${name}=([^&]+)`))
  return match ? match[1] : ''
}

/** 处理来自钉钉登录页的消息，只识别官方协议消息 */
function onMessage(event: MessageEvent) {
  if (event.origin !== DINGTALK_LOGIN_ORIGIN) return
  const data = event.data as Record<string, unknown> | null
  if (!data || typeof data !== 'object') return

  if (import.meta.env.DEV) {
    console.debug('[dingtalk-login] iframe message:', data)
  }

  if (data.success === true && typeof data.redirectUrl === 'string') {
    const redirectUrl = data.redirectUrl
    const authCode = parseParam(redirectUrl, 'authCode') || parseParam(redirectUrl, 'code')
    const state = parseParam(redirectUrl, 'state')
    const error = parseParam(redirectUrl, 'error')
    if (authCode) {
      emit('success', { redirectUrl, authCode, state })
    } else {
      emit('error', error || '钉钉授权未完成，请重试')
    }
    return
  }

  // 明确失败时才上报；空原因/无关容器消息忽略，避免误伤可用二维码
  if (data.success === false) {
    if (typeof data.errorMsg === 'string' && data.errorMsg) {
      emit('error', data.errorMsg)
    }
    return
  }
}

/** 创建钉钉二维码 iframe：授权 URL + iframe=true */
function createFrame() {
  const container = containerRef.value
  if (!container) return
  container.innerHTML = ''
  const frame = document.createElement('iframe')
  const separator = props.authorizeUrl.includes('?') ? '&' : '?'
  frame.src = `${props.authorizeUrl}${separator}iframe=true`
  frame.width = String(QR_WIDTH)
  frame.height = String(QR_HEIGHT)
  frame.frameBorder = '0'
  frame.scrolling = 'no'
  frame.name = IFRAME_NAME
  container.appendChild(frame)
}

onMounted(() => {
  window.addEventListener('message', onMessage)
  createFrame()
})

onUnmounted(() => {
  window.removeEventListener('message', onMessage)
  if (containerRef.value) {
    containerRef.value.innerHTML = ''
  }
})
</script>

<style scoped>
.dingtalk-qr-container {
  width: 300px;
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
</style>
