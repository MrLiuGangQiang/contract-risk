<template>
  <AppLayout>
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="welcome-text">
        <div class="welcome-title">你好，{{ auth.user?.display_name ?? auth.user?.username }} 👋</div>
        <div class="welcome-sub">欢迎使用合同风险扫描系统，祝工作顺利！</div>
      </div>
      <div class="welcome-badge">
        <span v-if="auth.isSuperAdmin" class="role-pill role-super">超级管理员</span>
        <span v-else-if="auth.user?.roles?.includes('admin')" class="role-pill role-admin">管理员</span>
        <span v-else class="role-pill role-user">普通用户</span>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats">
      <div class="stat-card">
        <ContractIcon class="stat-icon" :size="26" color="#2563eb" />
        <div class="stat-meta">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">我的合同</div>
        </div>
        <div class="stat-spark spark-blue"></div>
      </div>
      <div class="stat-card">
        <el-icon class="stat-icon" :size="26" color="#f59e0b"><warning /></el-icon>
        <div class="stat-meta">
          <div class="stat-value">{{ stats.risks }}</div>
          <div class="stat-label">累计风险项</div>
        </div>
        <div class="stat-spark spark-orange"></div>
      </div>
      <div class="stat-card">
        <el-icon class="stat-icon" :size="26" color="#ef4444"><flag /></el-icon>
        <div class="stat-meta">
          <div class="stat-value">{{ stats.high }}</div>
          <div class="stat-label">高风险项</div>
        </div>
        <div class="stat-spark spark-red"></div>
      </div>
      <div class="stat-card">
        <el-icon class="stat-icon" :size="26" color="#10b981"><circle-check /></el-icon>
        <div class="stat-meta">
          <div class="stat-value ok">{{ stats.scanned }}</div>
          <div class="stat-label">已完成扫描</div>
        </div>
        <div class="stat-spark spark-green"></div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-grid">
      <el-card v-if="auth.isSuperAdmin" class="brand-card quick-card" shadow="hover">
        <div class="quick-head">
          <el-icon :size="20" color="#2563eb"><setting /></el-icon>
          <span>系统配置</span>
        </div>
        <p class="quick-desc">配置钉钉企业登录与 AI 大模型，启用后员工扫码登录、合同智能识别即刻生效。</p>
        <el-button type="primary" plain @click="router.push({ name: 'system-config' })">
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
          <el-icon :size="20" color="#7c3aed"><magic-stick /></el-icon>
          <span>我的风险规则</span>
        </div>
        <p class="quick-desc">查看生效规则，个性化调整风险识别维度与关键词，可随时恢复默认模板。</p>
        <el-button type="primary" plain @click="router.push({ name: 'risk-rules' })">前往配置</el-button>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import {
  CircleCheck,
  Flag,
  MagicStick,
  Setting,
  Warning,
} from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import ContractIcon from '@/components/ContractIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { listContracts } from '@/api/contract'

const router = useRouter()
const auth = useAuthStore()

const stats = reactive({ total: 0, risks: 0, high: 0, scanned: 0 })

onMounted(async () => {
  try {
    const data = await listContracts({ page: 1, page_size: 100 })
    stats.total = data.total
    stats.risks = data.items.reduce((sum, c) => sum + c.risk_count, 0)
    stats.high = data.items.reduce((sum, c) => sum + c.high_count, 0)
    stats.scanned = data.items.length
  } catch {
    // 统计失败不影响首页展示，保持默认值
  }
})
</script>

<style scoped>
/* 欢迎横幅（浅色科技渐变 + 网格纹理） */
.welcome-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-radius: var(--card-radius);
  padding: 30px 34px;
  color: #0f172a;
  background:
    radial-gradient(460px 240px at 88% -20%, rgba(124, 58, 237, 0.16), transparent 62%),
    radial-gradient(420px 240px at 8% 130%, rgba(6, 182, 212, 0.14), transparent 62%),
    linear-gradient(120deg, #eef4ff 0%, #f5f8ff 55%, #faf7ff 100%);
  border: 1px solid rgba(37, 99, 235, 0.14);
  box-shadow: var(--card-shadow);
  margin-bottom: 20px;
  position: relative;
  overflow: hidden;
}
.welcome-banner::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(37, 99, 235, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(37, 99, 235, 0.05) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: radial-gradient(600px 260px at 50% 0%, #000, transparent 75%);
  pointer-events: none;
}
.welcome-banner::after {
  content: '';
  position: absolute;
  width: 280px;
  height: 280px;
  border-radius: 50%;
  right: -70px;
  top: -130px;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.12), transparent 65%);
  pointer-events: none;
}
.welcome-title {
  font-size: 23px;
  font-weight: 800;
  letter-spacing: 0.5px;
  background: linear-gradient(90deg, #1d4ed8, #7c3aed);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.welcome-sub {
  margin-top: 8px;
  font-size: 13px;
  color: #64748b;
}
/* 角色徽章 */
.welcome-badge {
  position: relative;
  z-index: 1;
}
.role-pill {
  display: inline-flex;
  align-items: center;
  padding: 7px 18px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 1px;
  backdrop-filter: blur(6px);
}
.role-super {
  color: #fff;
  background: linear-gradient(120deg, #2563eb, #7c3aed);
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35);
}
.role-admin {
  color: #0e7490;
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.3);
}
.role-user {
  color: #475569;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.35);
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
  flex-shrink: 0;
}
.stat-card { position: relative; overflow: hidden; }
.stat-spark {
  position: absolute;
  right: -26px;
  bottom: -34px;
  width: 104px;
  height: 104px;
  border-radius: 50%;
  opacity: 0.16;
  pointer-events: none;
}
.spark-blue { background: radial-gradient(circle, #2563eb, transparent 70%); }
.spark-orange { background: radial-gradient(circle, #f59e0b, transparent 70%); }
.spark-red { background: radial-gradient(circle, #ef4444, transparent 70%); }
.spark-green { background: radial-gradient(circle, #10b981, transparent 70%); }
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