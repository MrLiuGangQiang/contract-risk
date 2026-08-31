<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <ContractIcon class="logo-icon" :size="30" color="#2563eb" />
        <div class="logo-text">
          <div class="logo-title">合同风险扫描</div>
          <div class="logo-sub">Contract Risk</div>
        </div>
      </div>
      <el-menu :default-active="activeMenu" router class="side-menu">
        <el-menu-item index="/">
          <el-icon><home-filled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/contracts">
          <el-icon><document /></el-icon>
          <span>合同识别</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isSuperAdmin" index="/admin/config">
          <el-icon><setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isSuperAdmin || auth.user?.permissions?.includes('user:manage')" index="/admin/users">
          <el-icon><user-filled /></el-icon>
          <span>用户与角色</span>
        </el-menu-item>
        <el-menu-item index="/risk-rules">
          <el-icon><warning /></el-icon>
          <span>风险规则</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">v0.1.0</div>
    </aside>

    <!-- 主区域 -->
    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <el-icon class="crumb-icon"><arrow-right /></el-icon>
          <span class="crumb">{{ pageTitle }}</span>
        </div>
        <div class="topbar-right">
          <el-dropdown trigger="click" @command="onCommand">
            <span class="user-entry">
              <el-avatar :size="32" class="user-avatar">
                {{ avatarText }}
              </el-avatar>
              <span class="user-name">{{ auth.user?.display_name ?? auth.user?.username }}</span>
              <el-icon class="user-caret"><arrow-down /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="change-password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main class="content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  ArrowRight,
  Document,
  HomeFilled,
  Setting,
  UserFilled,
  Warning,
} from '@element-plus/icons-vue'
import { logout as apiLogout } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import ContractIcon from '@/components/ContractIcon.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => route.path)
const pageTitle = computed(() => String(route.meta.title ?? ''))

const avatarText = computed(() => {
  const name = auth.user?.display_name ?? auth.user?.username ?? 'U'
  return name.slice(0, 1).toUpperCase()
})

async function onCommand(command: string) {
  if (command === 'change-password') {
    router.push({ name: 'change-password' })
  } else if (command === 'logout') {
    await apiLogout()
    auth.clear()
    router.replace({ name: 'login' })
  }
}
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  position: relative;
}
/* 全局浅色光斑背景（克制） */
.app-layout::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(640px 420px at 88% -8%, rgba(37, 99, 235, 0.06), transparent 62%),
    radial-gradient(560px 420px at -6% 42%, rgba(124, 58, 237, 0.05), transparent 60%);
}

/* ===== 侧边栏（浅色玻璃拟态） ===== */
.sidebar {
  width: 224px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #eef1f6;
  color: #475569;
  position: sticky;
  top: 0;
  height: 100vh;
  z-index: 20;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px;
}
.logo-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}
.logo-title {
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.logo-sub {
  margin-top: 2px;
  font-size: 10px;
  color: #94a3b8;
  letter-spacing: 1.5px;
}
.side-menu {
  flex: 1;
  background: transparent;
  padding: 8px 12px;
}
.side-menu :deep(.el-menu-item) {
  height: 44px;
  margin-bottom: 6px;
  border-radius: 10px;
  color: #64748b;
  transition: all 0.2s ease;
}
.side-menu :deep(.el-menu-item:hover) {
  background: rgba(37, 99, 235, 0.07);
  color: #2563eb;
}
.side-menu :deep(.el-menu-item.is-active) {
  background: rgba(37, 99, 235, 0.09);
  color: #1d4ed8;
  font-weight: 600;
}
.side-menu :deep(.el-menu-item.is-active .el-icon) {
  color: #2563eb;
}
.sidebar-footer {
  padding: 16px;
  font-size: 11px;
  color: #94a3b8;
  text-align: center;
  letter-spacing: 1px;
}

/* ===== 顶栏 ===== */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  z-index: 1;
}
.topbar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #eef1f6;
  position: sticky;
  top: 0;
  z-index: 10;
}
.topbar-left {
  display: flex;
  align-items: center;
  gap: 6px;
}
.crumb-icon {
  color: #9ca3af;
  font-size: 14px;
}
.crumb {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0.5px;
}
.user-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 10px;
  transition: background 0.2s;
}
.user-entry:hover {
  background: rgba(37, 99, 235, 0.07);
}
.user-avatar {
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  font-weight: 600;
  box-shadow: 0 3px 10px rgba(37, 99, 235, 0.3);
}
.user-name {
  font-size: 14px;
  color: #1f2937;
}
.user-caret {
  color: #9ca3af;
  font-size: 12px;
}

/* ===== 内容区 ===== */
.content {
  flex: 1;
  padding: 24px;
}
</style>