<template>
  <AppLayout>
    <div class="change-password-page">
    <div class="auth-card">
      <div class="auth-head">
        <el-icon class="auth-logo" :size="34" color="#2563eb"><lock /></el-icon>
        <h2>修改密码</h2>
        <p v-if="force">首次登录必须修改初始密码后才能继续使用系统</p>
        <p v-else>定期更换密码，保护账号安全</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @keyup.enter="onSubmit"
      >
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="form.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="form.newPassword" type="password" show-password />
          <div class="form-tip">长度至少 10 位，需包含小写/大写/数字/特殊字符中的至少三类</div>
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" show-password />
        </el-form-item>
        <el-button
          type="primary"
          class="submit-btn"
          size="large"
          :loading="loading"
          @click="onSubmit"
        >
          确认修改
        </el-button>
      </el-form>
    </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { changePassword } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/AppLayout.vue'

const router = useRouter()
const auth = useAuthStore()
const force = computed(() => auth.mustChangePassword)

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const rules: FormRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 10, message: '密码长度至少 10 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== form.newPassword) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function onSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await changePassword(form.oldPassword, form.newPassword)
    ElMessage.success('密码修改成功，请重新登录')
    auth.clear()
    router.replace({ name: 'login' })
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  margin: -24px;
  background:
    radial-gradient(620px 420px at 15% 12%, rgba(59, 130, 246, 0.10), transparent 62%),
    radial-gradient(560px 420px at 88% 88%, rgba(124, 58, 237, 0.09), transparent 62%),
    linear-gradient(135deg, #f7faff 0%, #eef4ff 48%, #f8fafc 100%);
}
.auth-card {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border-radius: 16px;
  padding: 40px 36px;
  box-shadow: 0 20px 60px rgba(37, 99, 235, 0.12);
}
.auth-head {
  text-align: center;
  margin-bottom: 28px;
}
.auth-logo {
  display: block;
  margin: 0 auto 16px;
}
.auth-head h2 {
  margin: 0 0 8px;
  font-size: 22px;
  color: #111827;
}
.auth-head p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}
.submit-btn {
  width: 100%;
  margin-top: 8px;
  border-radius: 8px;
  letter-spacing: 2px;
}
</style>