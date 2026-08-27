<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <div class="logo-icon">
          <ContractIcon :size="22" color="#fff" />
        </div>
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
        <el-menu-item v-if="auth.isSuperAdmin" index="/admin/config/dingtalk">
          <el-icon><setting /></el-icon>
          <span>钉钉配置</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isSuperAdmin || auth.user?.permissions?.includes('user:manage')" index="/admin/users">
          <el-icon><user-filled /></el-icon>
          <span>用户与角色</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isSuperAdmin || auth.user?.permissions?.includes('risk:rule:manage')" index="/admin/risk-rules">
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
}

/* ===== 侧边栏 ===== */
.sidebar {
  width: 220px;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #0f172a 0%, #111c34 100%);
  color: #cbd5e1;
  position: sticky;
  top: 0;
  height: 100vh;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px;
}
.logo-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.45);
}
.logo-title {
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.logo-sub {
  margin-top: 2px;
  font-size: 10px;
  color: #64748b;
  letter-spacing: 1px;
}
.side-menu {
  flex: 1;
  background: transparent;
  padding: 8px 10px;
}
.side-menu :deep(.el-menu-item) {
  height: 44px;
  margin-bottom: 4px;
  border-radius: 8px;
  color: #94a3b8;
}
.side-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.06);
  color: #e2e8f0;
}
.side-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.35), rgba(37, 99, 235, 0.12));
  color: #fff;
}
.sidebar-footer {
  padding: 16px;
  font-size: 11px;
  color: #475569;
  text-align: center;
}

/* ===== 顶栏 ===== */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #eef0f4;
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
  font-weight: 600;
  color: #111827;
}
.user-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;
}
.user-entry:hover {
  background: #f3f4f6;
}
.user-avatar {
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  font-weight: 600;
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