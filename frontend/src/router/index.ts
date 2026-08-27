/**
 * 路由与守卫（《02-总体架构设计》第 5 节）：
 * - 未登录 → /login；
 * - must_change_password=true 时强制进入改密页；
 * - 页面级权限按 token 中 permissions 校验。
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/dingtalk/callback',
    name: 'dingtalk-callback',
    component: () => import('@/views/DingTalkCallbackView.vue'),
    meta: { public: true, title: '钉钉登录回调' },
  },
  {
    path: '/change-password',
    name: 'change-password',
    component: () => import('@/views/ChangePasswordView.vue'),
    meta: { requiresAuth: true, allowMustChange: true, title: '修改密码' },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { requiresAuth: true, title: '首页' },
  },
  {
    path: '/admin/config/dingtalk',
    name: 'dingtalk-config',
    component: () => import('@/views/DingTalkConfigView.vue'),
    meta: {
      requiresAuth: true,
      permission: 'config:dingtalk:read',
      title: '钉钉配置',
    },
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: () => import('@/views/AdminUserView.vue'),
    meta: {
      requiresAuth: true,
      permission: 'user:manage',
      title: '用户与角色',
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  // 页面刷新/重启：先用 refresh Cookie 静默恢复，避免强制重新登录
  if (!auth.isAuthenticated) {
    const restored = await auth.restoreSession()
    if (!restored) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }
  if (auth.mustChangePassword && !to.meta.allowMustChange) {
    return { name: 'change-password' }
  }
  const required = to.meta.permission as string | undefined
  if (required && !auth.isSuperAdmin && !auth.user?.permissions.includes(required)) {
    return { name: 'home' }
  }
  return true
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title ?? '')} - 合同风险扫描系统`
})

export default router