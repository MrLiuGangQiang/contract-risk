<template>
  <div class="user-manage">
    <el-card class="toolbar-card" shadow="never">
      <div class="toolbar">
        <div class="toolbar-left">
          <h3>用户与角色</h3>
          <span class="toolbar-desc">管理系统用户及角色分配，仅管理员及以上可访问</span>
        </div>
        <div class="toolbar-right">
          <el-input
            v-model="keyword"
            placeholder="搜索用户名 / 显示名"
            clearable
            style="width: 220px"
            @keyup.enter="onSearch"
            @clear="onSearch"
          >
            <template #prefix><el-icon><search /></el-icon></template>
          </el-input>
          <el-button type="primary" :icon="Plus" @click="openCreate">新建用户</el-button>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="users" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="140">
          <template #default="{ row }">
            <span class="username">{{ row.username }}</span>
            <el-tag v-if="row.is_super_admin" type="danger" size="small" class="super-tag">超管</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="display_name" label="显示名" min-width="120" />
        <el-table-column label="角色" min-width="160">
          <template #default="{ row }">
            <el-tag
              v-for="r in row.roles"
              :key="r.code"
              :type="r.code === 'super_admin' ? 'danger' : r.code === 'admin' ? 'warning' : 'primary'"
              size="small"
              class="role-tag"
            >
              {{ r.name }}
            </el-tag>
            <span v-if="row.roles.length === 0" class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="首次改密" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.must_change_password" type="warning" size="small">待改密</el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="最近登录" min-width="160">
          <template #default="{ row }">{{ formatTime(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="openReset(row)">重置密码</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadUsers"
          @size-change="loadUsers"
        />
      </div>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建用户' : '编辑用户'"
      width="480px"
      destroy-on-close
    >
      <el-form ref="dialogFormRef" :model="dialogForm" :rules="dialogRules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="dialogForm.username" :disabled="dialogMode === 'edit'" placeholder="字母/数字/_、-、." />
        </el-form-item>
        <el-form-item label="显示名" prop="display_name">
          <el-input v-model="dialogForm.display_name" placeholder="用户显示名称" />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'create'" label="初始密码" prop="password">
          <el-input v-model="dialogForm.password" type="password" show-password placeholder="至少 10 位，必含三类字符" />
          <div class="form-tip">创建后用户首次登录将强制改密</div>
        </el-form-item>
        <el-form-item v-if="dialogMode === 'edit'" label="状态" prop="status">
          <el-radio-group v-model="dialogForm.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="角色" prop="roles">
          <el-checkbox-group v-model="dialogForm.roles">
            <el-checkbox v-for="r in roles" :key="r.code" :value="r.code">{{ r.name }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="dialogSaving" @click="submitDialog">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetVisible" title="重置密码" width="440px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="用户">
          <span>{{ resetTarget?.username }}</span>
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="resetPassword" type="password" show-password placeholder="至少 10 位，必含三类字符" />
          <div class="form-tip">重置后该用户将被强制注销，下次登录需改密</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetSaving" @click="submitReset">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import {
  createUser,
  deleteUser,
  listRoles,
  listUsers,
  resetUserPassword,
  updateUser,
} from '@/api/admin'
import type { AdminUser, Role } from '@/api/types'

const loading = ref(false)
const users = ref<AdminUser[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const roles = ref<Role[]>([])

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogSaving = ref(false)
const dialogFormRef = ref<FormInstance>()
const dialogForm = reactive({
  id: 0,
  username: '',
  display_name: '',
  password: '',
  status: 1,
  roles: [] as string[],
})

const resetVisible = ref(false)
const resetSaving = ref(false)
const resetTarget = ref<AdminUser | null>(null)
const resetPassword = ref('')

const dialogRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 10, message: '密码至少 10 位', trigger: 'blur' },
  ],
  roles: [{ required: true, type: 'array', min: 1, message: '至少分配一个角色', trigger: 'change' }],
}

onMounted(async () => {
  await Promise.all([loadRoles(), loadUsers()])
})

async function loadRoles() {
  try {
    roles.value = await listRoles()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function loadUsers() {
  loading.value = true
  try {
    const data = await listUsers({ page: page.value, page_size: pageSize.value, keyword: keyword.value || undefined })
    users.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  loadUsers()
}

function openCreate() {
  dialogMode.value = 'create'
  dialogForm.id = 0
  dialogForm.username = ''
  dialogForm.display_name = ''
  dialogForm.password = ''
  dialogForm.status = 1
  dialogForm.roles = ['user']
  dialogVisible.value = true
}

function openEdit(user: AdminUser) {
  dialogMode.value = 'edit'
  dialogForm.id = user.id
  dialogForm.username = user.username
  dialogForm.display_name = user.display_name
  dialogForm.password = ''
  dialogForm.status = user.status
  dialogForm.roles = user.roles.map((r) => r.code)
  dialogVisible.value = true
}

async function submitDialog() {
  const valid = await dialogFormRef.value?.validate().catch(() => false)
  if (!valid) return
  dialogSaving.value = true
  try {
    if (dialogMode.value === 'create') {
      await createUser({
        username: dialogForm.username,
        display_name: dialogForm.display_name,
        password: dialogForm.password,
        roles: dialogForm.roles,
      })
      ElMessage.success('用户创建成功')
    } else {
      await updateUser(dialogForm.id, {
        display_name: dialogForm.display_name,
        status: dialogForm.status,
        roles: dialogForm.roles,
      })
      ElMessage.success('用户已更新')
    }
    dialogVisible.value = false
    await loadUsers()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    dialogSaving.value = false
  }
}

function openReset(user: AdminUser) {
  resetTarget.value = user
  resetPassword.value = ''
  resetVisible.value = true
}

async function submitReset() {
  if (!resetTarget.value) return
  if (resetPassword.value.length < 10) {
    ElMessage.warning('密码至少 10 位')
    return
  }
  resetSaving.value = true
  try {
    await resetUserPassword(resetTarget.value.id, resetPassword.value)
    ElMessage.success('密码已重置')
    resetVisible.value = false
    await loadUsers()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    resetSaving.value = false
  }
}

async function onDelete(user: AdminUser) {
  try {
    await ElMessageBox.confirm(
      `确定删除用户「${user.username}」？删除后该用户不可登录。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteUser(user.id)
    ElMessage.success('用户已删除')
    await loadUsers()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

function formatTime(value: string | null): string {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  return d.toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.user-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-left h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #111827;
}
.toolbar-desc {
  font-size: 12px;
  color: #6b7280;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.username {
  font-weight: 600;
  color: #111827;
}
.super-tag {
  margin-left: 6px;
}
.role-tag {
  margin-right: 6px;
}
.muted {
  color: #9ca3af;
}
.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.5;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
