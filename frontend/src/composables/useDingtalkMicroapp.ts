/**
 * 钉钉 H5 微应用免登（《04-认证与授权设计》第 3.6 节）。
 *
 * 适用场景：页面在钉钉客户端内以 H5 微应用打开（工作台入口）时，客户端注入钉钉 JSAPI
 * （window.dd），可通过 requestAuthCode 免扫码获取一次性免登码；普通浏览器没有该能力，
 * 调用方应回退到内嵌二维码/官方页登录。
 */

interface DingtalkJsApi {
  ready(callback: () => void): void
  runtime: {
    permission: {
      requestAuthCode(options: {
        corpId: string
        onSuccess: (result: { code: string }) => void
        onFail: (error: unknown) => void
      }): void
    }
  }
}

declare global {
  interface Window {
    dd?: DingtalkJsApi
  }
}

/** 钉钉官方 JSAPI SDK（仅在钉钉容器内按需加载） */
const DINGTALK_JSAPI_SDK_URL =
  'https://g.alicdn.com/dingding/dingtalk-jsapi/3.0.25/dingtalk.open.js'
/** dd.ready / requestAuthCode 等待上限（毫秒），超时回退扫码登录 */
const DINGTALK_READY_TIMEOUT_MS = 8000
const DINGTALK_AUTH_CODE_TIMEOUT_MS = 8000

/** 是否运行在钉钉客户端容器内（UA 含 DingTalk） */
export function isDingTalkContainer(): boolean {
  return typeof navigator !== 'undefined' && /DingTalk/i.test(navigator.userAgent)
}

/** 加载钉钉 JSAPI SDK；window.dd 已注入时直接返回 */
function loadDingtalkSdk(): Promise<void> {
  return new Promise((resolve) => {
    if (window.dd) {
      resolve()
      return
    }
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${DINGTALK_JSAPI_SDK_URL}"]`,
    )
    if (existing) {
      // 脚本已在加载中：等待 window.dd 出现（waitReady 内有轮询与超时兜底）
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = DINGTALK_JSAPI_SDK_URL
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => resolve() // 加载失败交给 waitReady 超时兜底，避免卡死
    document.head.appendChild(script)
  })
}

/** 等待 dd.ready（客户端容器初始化完成），超时抛错 */
function waitReady(timeoutMs: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error('钉钉 JSAPI 初始化超时'))
    }, timeoutMs)
    const poll = () => {
      if (window.dd) {
        window.dd.ready(() => {
          window.clearTimeout(timer)
          resolve()
        })
        return
      }
      window.setTimeout(poll, 100)
    }
    poll()
  })
}

/**
 * 获取一次性微应用免登码（5 分钟有效，只能用一次）。
 * 仅在钉钉客户端内调用；失败抛出 Error，由调用方回退到扫码登录。
 */
export async function requestDingtalkAuthCode(corpId: string): Promise<string> {
  if (!isDingTalkContainer()) {
    throw new Error('当前不在钉钉客户端内，无法免登')
  }
  await loadDingtalkSdk()
  await waitReady(DINGTALK_READY_TIMEOUT_MS)
  return new Promise<string>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error('获取钉钉免登码超时，请重试'))
    }, DINGTALK_AUTH_CODE_TIMEOUT_MS)
    window.dd?.runtime.permission.requestAuthCode({
      corpId,
      onSuccess: (result) => {
        window.clearTimeout(timer)
        if (result.code) {
          resolve(result.code)
        } else {
          reject(new Error('钉钉未返回免登码'))
        }
      },
      onFail: () => {
        window.clearTimeout(timer)
        reject(new Error('获取钉钉免登码失败'))
      },
    })
  })
}

