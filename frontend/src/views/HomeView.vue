<template>
  <AppLayout>
    <!-- 欢迎横幅 -->
    <div class="welcome-banner brand-gradient">
      <div class="welcome-text">
        <div class="welcome-title">你好，{{ auth.user?.display_name ?? auth.user?.username }} 👋</div>
        <div class="welcome-sub">欢迎使用合同风险扫描系统，祝工作顺利！</div>
      </div>
      <div class="welcome-badge">
        <el-tag v-if="auth.isSuperAdmin" effect="dark" round>超级管理员</el-tag>
        <el-tag v-else type="info" effect="plain" round>普通用户</el-tag>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats">
      <div class="stat-card">
        <div class="stat-icon blue"><ContractIcon :size="22" color="#fff" /></div>
        <div class="stat-meta">
          <div class="stat-value">--</div>
          <div class="stat-label">合同总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon orange"><el-icon :size="22"><warning /></el-icon></div>
        <div class="stat-meta">
          <div class="stat-value">--</div>
          <div class="stat-label">风险项</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon green"><el-icon :size="22"><circle-check /></el-icon></div>
        <div class="stat-meta">
          <div class="stat-value">--</div>
          <div class="stat-label">已完成扫描</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon purple"><el-icon :size="22"><monitor /></el-icon></div>
        <div class="stat-meta">
          <div class="stat-value ok">正常</div>
          <div class="stat-label">系统状态</div>
        </div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-grid">
      <el-card v-if="auth.isSuperAdmin" class="brand-card quick-card" shadow="hover">
        <div class="quick-head">
          <el-icon :size="20" color="#2563eb"><setting /></el-icon>
          <span>钉钉登录配置</span>
        </div>
        <p class="quick-desc">配置企业钉钉应用的 Client ID / Client Secret，启用后员工可通过钉钉扫码登录。</p>
        <el-button type="primary" plain @click="router.push({ name: 'dingtalk-config' })">
          前往配置
        </el-button>
      </el-card>

      <el-card class="brand-card quick-card" shadow="hover">
        <div class="quick-head">
          <ContractIcon :size="20" color="#f59e0b" />
          <span>合同风险识别</span>
        </div>
        <p class="quick-desc">上传 txt / PDF / Word 合同，自动识别项目管理、技术、合同条款与通用风险。</p>
        <el-button type="primary" plain @click="router.push({ name: 'contracts' })">前往识别</el-button>
      </el-card>

      <el-card class="brand-card quick-card" shadow="hover">
        <div class="quick-head">
          <el-icon :size="20" color="#10b981"><trend-charts /></el-icon>
          <span>风险报告（即将上线）</span>
        </div>
        <p class="quick-desc">风险扫描结果汇总与报告导出，支持钉钉消息通知。</p>
        <el-button disabled>敬请期待</el-button>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  CircleCheck,
  Monitor,
  Setting,
  TrendCharts,
  Warning,
} from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import ContractIcon from '@/components/ContractIcon.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
</script>

<style scoped>
/* 欢迎横幅 */
.welcome-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-radius: var(--card-radius);
  padding: 28px 32px;
  color: #fff;
  box-shadow: var(--card-shadow);
  margin-bottom: 20px;
  position: relative;
  overflow: hidden;
}
.welcome-banner::after {
  content: '';
  position: absolute;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  right: -60px;
  top: -120px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.14), transparent 65%);
}
.welcome-title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.welcome-sub {
  margin-top: 6px;
  font-size: 13px;
  opacity: 0.85;
}

/* 统计卡 */
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  background: #fff;
  border-radius: var(--card-radius);
  box-shadow: var(--card-shadow);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--card-shadow-hover);
}
.stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.stat-icon.blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.stat-icon.orange { background: linear-gradient(135deg, #fbbf24, #f59e0b); }
.stat-icon.green { background: linear-gradient(135deg, #34d399, #10b981); }
.stat-icon.purple { background: linear-gradient(135deg, #a78bfa, #8b5cf6); }
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
}
.stat-value.ok {
  font-size: 18px;
  color: #10b981;
}
.stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

/* 快捷操作 */
.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.quick-card {
  padding: 4px;
}
.quick-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}
.quick-desc {
  margin: 12px 0 16px;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.7;
  min-height: 44px;
}

@media (max-width: 1100px) {
  .stats { grid-template-columns: repeat(2, 1fr); }
  .quick-grid { grid-template-columns: 1fr; }
}
</style>