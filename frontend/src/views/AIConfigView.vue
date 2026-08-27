<template>
  <AppLayout>
    <div class="ai-config-page">
      <el-card shadow="never">
        <div class="page-head">
          <h3>AI 增强识别配置</h3>
          <span class="page-desc">配置 OpenAI 兼容模型；开启后合同扫描会叠加 AI 风险识别，未配置/失败自动降级为规则识别</span>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" label-width="150px" class="config-form">
          <el-form-item label="启用 AI 识别">
            <el-switch v-model="form.enabled" />
          </el-form-item>
          <el-form-item label="API 地址" prop="api_base">
            <el-input v-model="form.api_base" placeholder="https://api.openai.com/v1" />
          </el-form-item>
          <el-form-item label="API Key" prop="api_key">
            <el-input v-model="form.api_key" type="password" show-password :placeholder="apiKeyPlaceholder" />
            <div class="form-tip">留空表示不修改；已保存的密钥加密存储，读取时脱敏</div>
          </el-form-item>
          <el-form-item label="模型" prop="model">
            <el-input v-model="form.model" placeholder="gpt-4o-mini" />
          </el-form-item>
          <el-form-item label="超时（秒）" prop="timeout_seconds">
            <el-input-number v-model="form.timeout_seconds" :min="5" :max="300" />
          </el-form-item>
          <el-form-item label="上下文长度" prop="context_chars">
            <el-input-number v-model="form.context_chars" :min="1000" :max="200000" :step="1000" />
          </el-form-item>
          <el-form-item label="最大发现数" prop="max_findings">
            <el-input-number v-model="form.max_findings" :min="1" :max="100" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
            <el-button :loading="testing" @click="onTest">测试连通性</el-button>
          </el-form-item>
          <el-form-item v-if="testMessage">
            <el-alert :title="testMessage" :type="testOk ? 'success' : 'error'" :closable="false" show-icon />
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getAIConfig, testAIConfig, updateAIConfig } from '@/api/admin'
import AppLayout from '@/components/AppLayout.vue'

const formRef = ref<FormInstance>()
const saving = ref(false)
const testing = ref(false)
const testMessage = ref('')
const testOk = ref(false)
const apiKeyOldMasked = ref('')

const form = reactive({
  enabled: false,
  api_base: 'https://api.openai.com/v1',
  api_key: '',
  model: 'gpt-4o-mini',
  timeout_seconds: 30,
  context_chars: 30000,
  max_findings: 50,
})

const apiKeyPlaceholder = computed(() => apiKeyOldMasked.value || '请输入 API Key')

const rules: FormRules = {
  api_base: [{ required: true, message: '请输入 API 地址', trigger: 'blur' }],
  model: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
}

onMounted(loadConfig)

async function loadConfig() {
  try {
    const data = await getAIConfig()
    form.enabled = data.enabled
    form.api_base = data.api_base
    form.model = data.model
    form.timeout_seconds = data.timeout_seconds
    form.context_chars = data.context_chars
    form.max_findings = data.max_findings
    apiKeyOldMasked.value = data.api_key_masked
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const data = await updateAIConfig({
      enabled: form.enabled,
      api_base: form.api_base,
      api_key: form.api_key,
      model: form.model,
      timeout_seconds: form.timeout_seconds,
      context_chars: form.context_chars,
      max_findings: form.max_findings,
    })
    apiKeyOldMasked.value = data.api_key_masked
    form.api_key = ''
    testMessage.value = ''
    ElMessage.success('AI 配置已保存')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    saving.value = false
  }
}

async function onTest() {
  testing.value = true
  testMessage.value = ''
  try {
    const result = await testAIConfig()
    testOk.value = result.ok
    testMessage.value = result.detail
  } catch (e) {
    testOk.value = false
    testMessage.value = (e as Error).message
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.ai-config-page {
  max-width: 760px;
}
.page-head {
  margin-bottom: 20px;
}
.page-head h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #111827;
}
.page-desc {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
}
.config-form {
  max-width: 640px;
}
.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.5;
}
</style>