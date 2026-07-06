<template>
  <el-tabs v-model="activeTab" class="admin-tabs" @tab-change="changeTab">
    <el-tab-pane label="账号设置" name="account">
      <section class="account-page">
        <div class="account-hero">
          <div class="account-avatar">
            <el-icon><UserFilled /></el-icon>
          </div>
          <div class="account-identity">
            <h2>{{ accountInfo?.full_name || accountInfo?.username || '当前用户' }}</h2>
            <p>{{ accountInfo?.username || '-' }}</p>
            <div class="account-roles">
              <el-tag v-for="role in accountInfo?.roles || []" :key="role.id" effect="plain">{{ role.name }}</el-tag>
              <span v-if="!accountInfo?.roles?.length">暂无角色</span>
            </div>
          </div>
          <dl class="account-facts">
            <div>
              <dt>部门</dt>
              <dd>{{ accountInfo?.department || '-' }}</dd>
            </div>
            <div>
              <dt>账号状态</dt>
              <dd>正常</dd>
            </div>
          </dl>
        </div>

        <div class="account-settings">
          <div class="account-setting-row">
            <div class="setting-icon">
              <el-icon><Lock /></el-icon>
            </div>
            <div class="setting-copy">
              <h3>修改密码</h3>
              <p>定期更新密码可以提升账号安全性，修改成功后需要重新登录。</p>
            </div>
            <el-button type="primary" plain @click="passwordVisible = true">修改密码</el-button>
          </div>

          <div class="account-setting-row danger-row">
            <div class="setting-icon">
              <el-icon><Warning /></el-icon>
            </div>
            <div class="setting-copy">
              <h3>注销账号</h3>
              <p>注销后账号将从系统中删除，当前会话立即退出。</p>
            </div>
            <el-button type="danger" plain @click="cancelVisible = true">注销账号</el-button>
          </div>
        </div>
      </section>
    </el-tab-pane>

    <el-tab-pane label="用户管理" name="users">
      <section class="table-panel">
        <div class="panel-head">
          <div>
            <h2>用户与角色</h2>
            <p>创建账号、启停用户并分配角色。</p>
          </div>
          <el-button type="primary" :icon="Plus" @click="userVisible = true">新增用户</el-button>
        </div>
        <el-table v-loading="loading" :data="users" row-key="id">
          <el-table-column prop="username" label="账号" width="130" />
          <el-table-column prop="full_name" label="姓名" width="130" />
          <el-table-column prop="department" label="部门" min-width="140" />
          <el-table-column label="角色" min-width="220">
            <template #default="{ row }">
              <el-tag v-for="roleId in row.role_ids" :key="roleId" class="tag-gap">{{ roleName(roleId) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-switch :model-value="row.is_active" @change="(value: string | number | boolean) => changeUserActive(row.id, Boolean(value))" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="170">
            <template #default="{ row }">
              <div class="table-actions">
                <el-button text type="primary" @click="openRoleAssign(row)">分配角色</el-button>
                <el-button text type="danger" :disabled="isDeleteDisabled(row)" @click="deleteUserRow(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </el-tab-pane>

    <el-tab-pane label="角色管理" name="roles">
      <section class="table-panel">
        <div class="panel-head">
          <div>
            <h2>角色管理</h2>
            <p>维护角色信息，并查看菜单与权限绑定数量。</p>
          </div>
        </div>
        <el-table v-loading="loading" :data="roles" row-key="id">
          <el-table-column prop="name" label="角色" width="160" />
          <el-table-column prop="code" label="编码" width="180" />
          <el-table-column prop="description" label="说明" min-width="220" />
          <el-table-column label="菜单数量" width="100">
            <template #default="{ row }">{{ row.menu_ids.length }}</template>
          </el-table-column>
          <el-table-column label="权限数量" width="100">
            <template #default="{ row }">{{ row.permission_ids.length }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <div class="table-actions">
                <el-button text type="primary" @click="openPermissionAssign(row)">绑定权限</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </el-tab-pane>

    <el-tab-pane label="菜单管理" name="menus">
      <section class="table-panel">
        <div class="panel-head">
          <div>
            <h2>菜单管理</h2>
            <p>查看系统菜单、路由地址和启用状态。</p>
          </div>
        </div>
        <el-table v-loading="loading" :data="menus" row-key="id" default-expand-all>
          <el-table-column prop="title" label="菜单名称" min-width="170" />
          <el-table-column prop="route_path" label="路由" min-width="220" show-overflow-tooltip />
          <el-table-column prop="route_name" label="编码" min-width="180" show-overflow-tooltip />
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column label="可见" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_visible ? 'success' : 'info'">{{ row.is_visible ? '可见' : '隐藏' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="启用" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </el-tab-pane>

    <el-tab-pane label="权限管理" name="permissions">
      <section class="table-panel">
        <div class="panel-head">
          <div>
            <h2>权限管理</h2>
            <p>查看接口权限点、请求方法和资源路径。</p>
          </div>
        </div>
        <el-table v-loading="loading" :data="permissions" row-key="id">
          <el-table-column prop="name" label="权限名称" min-width="180" />
          <el-table-column prop="code" label="权限编码" min-width="220" show-overflow-tooltip />
          <el-table-column prop="method" label="方法" width="90" />
          <el-table-column prop="path" label="接口路径" min-width="260" show-overflow-tooltip />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </el-tab-pane>

    <el-tab-pane label="数据字典" name="dictionaries">
      <DictionaryManageView />
    </el-tab-pane>

    <el-tab-pane label="操作日志" name="logs">
      <section class="table-panel">
        <div class="panel-head">
          <div>
            <h2>操作日志</h2>
            <p>查看最近接口访问记录和业务处理结果。</p>
          </div>
        </div>
        <div class="toolbar-row">
          <el-input v-model="logQuery.trace_id" clearable placeholder="Trace ID" style="width: 220px" />
          <el-input v-model="logQuery.path" clearable placeholder="接口路径" style="width: 220px" />
          <el-select v-model="logQuery.method" clearable placeholder="方法" style="width: 120px">
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="PATCH" value="PATCH" />
            <el-option label="DELETE" value="DELETE" />
          </el-select>
          <el-button type="primary" @click="searchLogs">查询</el-button>
        </div>
        <el-table v-loading="loading" :data="logs" row-key="id">
          <el-table-column prop="created_at" label="时间" min-width="180" show-overflow-tooltip />
          <el-table-column prop="trace_id" label="Trace ID" min-width="180" show-overflow-tooltip />
          <el-table-column prop="method" label="方法" width="90" />
          <el-table-column prop="path" label="路径" min-width="240" show-overflow-tooltip />
          <el-table-column prop="operation" label="权限点" min-width="180" />
          <el-table-column prop="status_code" label="业务码" width="100" />
          <el-table-column prop="response_message" label="结果" min-width="180" />
        </el-table>
        <el-pagination
          v-model:current-page="logQuery.page"
          v-model:page-size="logQuery.page_size"
          class="pager"
          layout="total, sizes, prev, pager, next"
          :total="logTotal"
          @change="loadLogs"
        />
      </section>
    </el-tab-pane>
  </el-tabs>

  <el-dialog v-model="userVisible" title="新增用户" width="620px" @closed="resetUserForm">
    <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="92px">
      <el-form-item label="账号" prop="username"><el-input v-model="userForm.username" /></el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="userForm.password" type="password" show-password />
        <p class="form-tip">密码需 8-128 位，且包含大写字母、小写字母、数字和特殊字符。</p>
      </el-form-item>
      <el-form-item label="姓名" prop="full_name"><el-input v-model="userForm.full_name" /></el-form-item>
      <el-form-item label="部门"><el-input v-model="userForm.department" /></el-form-item>
      <el-form-item label="角色" prop="role_id">
        <el-select v-model="userForm.role_id" clearable placeholder="请选择一个角色" style="width: 100%">
          <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="userVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveUser">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="roleAssignVisible" title="分配用户角色" width="540px">
    <el-select v-model="selectedRoleId" clearable placeholder="请选择一个角色" style="width: 100%">
      <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
    </el-select>
    <template #footer>
      <el-button @click="roleAssignVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveRoleAssign">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="permissionAssignVisible" title="绑定角色权限" width="760px">
    <el-select v-model="selectedPermissionIds" multiple filterable style="width: 100%">
      <el-option
        v-for="permission in permissions"
        :key="permission.id"
        :label="`${permission.name} (${permission.code})`"
        :value="permission.id"
      />
    </el-select>
    <template #footer>
      <el-button @click="permissionAssignVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="savePermissionAssign">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="passwordVisible" title="修改密码" width="520px" @closed="resetPasswordForm">
    <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="104px" class="dialog-form">
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="passwordForm.old_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="passwordForm.new_password" type="password" show-password />
        <p class="form-tip">密码需 8-128 位，且包含大写字母、小写字母、数字和特殊字符。</p>
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirm_password">
        <el-input v-model="passwordForm.confirm_password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="passwordVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="savePassword">保存密码</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="cancelVisible" title="注销账号" width="520px" @closed="resetCancelForm">
    <el-alert type="warning" :closable="false" show-icon title="注销后账号将从系统中删除，无法继续登录。" />
    <el-form ref="cancelFormRef" :model="cancelForm" :rules="cancelRules" label-width="92px" class="dialog-form">
      <el-form-item label="当前密码" prop="password">
        <el-input v-model="cancelForm.password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="cancelVisible = false">取消</el-button>
      <el-button type="danger" :loading="saving" @click="confirmCancelAccount">确认注销</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Lock, Plus, UserFilled, Warning } from '@element-plus/icons-vue'
import { cancelCurrentAccount, changeCurrentPassword, getCurrentUser, type CurrentUser } from '../api/auth'
import { clearSessionMenus } from '../utils/menuCache'
import DictionaryManageView from './DictionaryManageView.vue'
import {
  assignRolePermissions,
  assignUserRoles,
  createUser,
  deleteUser,
  listMenus,
  listOperationLogs,
  listPermissions,
  listRoles,
  listUsers,
  type MenuItem,
  setUserActive,
  type OperationLogItem,
  type PermissionItem,
  type RoleItem,
  type UserItem
} from '../api/rbac'

const route = useRoute()
const router = useRouter()
const routeToTab: Record<string, string> = {
  '/system/account': 'account',
  '/system/users': 'users',
  '/system/roles': 'roles',
  '/system/menus': 'menus',
  '/system/permissions': 'permissions',
  '/system/operation-logs': 'logs',
  '/system/dictionaries': 'dictionaries'
}
const tabToRoute = computed<Record<string, string>>(() => Object.fromEntries(
  Object.entries(routeToTab).map(([path, tab]) => [tab, path])
))
const activeTab = ref(routeToTab[route.path] || 'account')
const loading = ref(false)
const saving = ref(false)
const accountInfo = ref<CurrentUser | null>(null)
const users = ref<UserItem[]>([])
const roles = ref<RoleItem[]>([])
const menus = ref<MenuItem[]>([])
const permissions = ref<PermissionItem[]>([])
const logs = ref<OperationLogItem[]>([])
const logTotal = ref(0)
const userVisible = ref(false)
const roleAssignVisible = ref(false)
const permissionAssignVisible = ref(false)
const passwordVisible = ref(false)
const cancelVisible = ref(false)
const editingUser = ref<UserItem | null>(null)
const editingRole = ref<RoleItem | null>(null)
const selectedRoleId = ref<number>()
const selectedPermissionIds = ref<number[]>([])
const passwordFormRef = ref<FormInstance>()
const cancelFormRef = ref<FormInstance>()
const userFormRef = ref<FormInstance>()
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})
const cancelForm = reactive({
  password: ''
})
const userForm = reactive({
  username: '',
  password: '',
  full_name: '',
  department: '',
  is_active: true,
  role_id: undefined as number | undefined
})
const logQuery = reactive({
  page: 1,
  page_size: 20,
  trace_id: '',
  path: '',
  method: ''
})

const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,128}$/
const passwordMessage = '密码需 8-128 位，且包含大写字母、小写字母、数字和特殊字符'
const passwordRules: FormRules<typeof passwordForm> = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (!passwordPattern.test(value || '')) {
          callback(new Error(passwordMessage))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的新密码不一致'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}
const cancelRules: FormRules<typeof cancelForm> = {
  password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }]
}
const userRules: FormRules<typeof userForm> = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (!passwordPattern.test(value || '')) {
          callback(new Error(passwordMessage))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ],
  full_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role_id: [{ required: true, message: '请选择一个角色', trigger: 'change' }]
}

function clearAuthState() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('current_user')
  localStorage.removeItem('permissions')
  clearSessionMenus()
  router.push('/login')
}

async function loadAccount() {
  accountInfo.value = await getCurrentUser()
}

function roleName(id: number) {
  return roles.value.find((role) => role.id === id)?.name || `角色${id}`
}

function isCurrentOpsAdmin() {
  return Boolean(accountInfo.value?.roles?.some((role) => role.code === 'ops_admin'))
}

function isDeleteDisabled(row: UserItem) {
  return row.is_superuser || (isCurrentOpsAdmin() && accountInfo.value?.id === row.id)
}

async function savePassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await changeCurrentPassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    ElMessage.success('密码已修改，请重新登录')
    clearAuthState()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '密码修改失败'))
  } finally {
    saving.value = false
  }
}

function resetPasswordForm() {
  Object.assign(passwordForm, {
    old_password: '',
    new_password: '',
    confirm_password: ''
  })
  passwordFormRef.value?.clearValidate()
}

function resetCancelForm() {
  cancelForm.password = ''
  cancelFormRef.value?.clearValidate()
}

async function confirmCancelAccount() {
  const valid = await cancelFormRef.value?.validate().catch(() => false)
  if (!valid) return
  try {
    await ElMessageBox.confirm('确认注销当前账号吗？注销后账号将从系统中删除。', '确认注销', {
      confirmButtonText: '注销',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger'
    })
    saving.value = true
    await cancelCurrentAccount({ password: cancelForm.password })
    ElMessage.success('账号已注销')
    clearAuthState()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '账号注销失败'))
  } finally {
    saving.value = false
  }
}

async function loadAll() {
  loading.value = true
  try {
    const [userRows, roleRows, menuRows, permissionRows, logPage] = await Promise.all([
      listUsers(),
      listRoles(),
      listMenus(),
      listPermissions(),
      listOperationLogs(logQuery)
    ])
    users.value = userRows
    roles.value = roleRows
    menus.value = menuRows
    permissions.value = permissionRows
    logs.value = logPage.items
    logTotal.value = logPage.total
  } finally {
    loading.value = false
  }
}

async function loadLogs() {
  const page = await listOperationLogs(logQuery)
  logs.value = page.items
  logTotal.value = page.total
}

async function searchLogs() {
  logQuery.page = 1
  await loadLogs()
}

async function saveUser() {
  const valid = await userFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await createUser({
      username: userForm.username,
      password: userForm.password,
      full_name: userForm.full_name,
      department: userForm.department,
      is_active: userForm.is_active,
      role_ids: userForm.role_id ? [userForm.role_id] : []
    })
    ElMessage.success('用户已创建')
    userVisible.value = false
    await loadAll()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '用户创建失败，请检查账号、密码和角色配置'))
  } finally {
    saving.value = false
  }
}

function resetUserForm() {
  Object.assign(userForm, {
    username: '',
    password: '',
    full_name: '',
    department: '',
    is_active: true,
    role_id: undefined
  })
  userFormRef.value?.clearValidate()
}

async function changeUserActive(id: number, isActive: boolean) {
  await setUserActive(id, isActive)
  await loadAll()
}

async function deleteUserRow(row: UserItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除用户「${row.full_name || row.username}」吗？删除后该账号将从系统中移除。`,
      '删除用户',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    await deleteUser(row.id)
    ElMessage.success('用户已删除')
    await loadAll()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '删除用户失败'))
  }
}

function openRoleAssign(row: UserItem) {
  editingUser.value = row
  selectedRoleId.value = row.role_ids[0]
  roleAssignVisible.value = true
}

async function saveRoleAssign() {
  if (!editingUser.value) return
  saving.value = true
  try {
    await assignUserRoles(editingUser.value.id, selectedRoleId.value ? [selectedRoleId.value] : [])
    ElMessage.success('角色已更新')
    roleAssignVisible.value = false
    await loadAll()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '角色更新失败'))
  } finally {
    saving.value = false
  }
}

function openPermissionAssign(row: RoleItem) {
  editingRole.value = row
  selectedPermissionIds.value = [...row.permission_ids]
  permissionAssignVisible.value = true
}

async function savePermissionAssign() {
  if (!editingRole.value) return
  saving.value = true
  try {
    await assignRolePermissions(editingRole.value.id, selectedPermissionIds.value)
    ElMessage.success('权限已更新')
    permissionAssignVisible.value = false
    await loadAll()
  } finally {
    saving.value = false
  }
}

function getErrorMessage(error: unknown, fallback: string) {
  const response = (error as { response?: { data?: { msg?: string; data?: unknown } } }).response
  const msg = response?.data?.msg
  if (msg && msg !== 'Invalid request parameters') return msg
  if (Array.isArray(response?.data?.data)) {
    const firstPasswordError = response.data.data.find((item: { loc?: string[] }) => item.loc?.includes('password'))
    if (firstPasswordError) return passwordMessage
  }
  return error instanceof Error && error.message ? error.message : fallback
}

function changeTab(tabName: string | number) {
  const nextPath = tabToRoute.value[String(tabName)]
  if (nextPath && nextPath !== route.path) {
    router.replace(nextPath)
  }
}

watch(
  () => route.path,
  (path) => {
    activeTab.value = routeToTab[path] || 'account'
  }
)

onMounted(() => {
  loadAccount()
  loadAll()
})
</script>

<style scoped>
.account-page {
  display: grid;
  gap: 16px;
}

.account-hero {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) minmax(220px, auto);
  align-items: center;
  gap: 18px;
  padding: 20px;
  background: linear-gradient(135deg, #f8fbff 0%, #eef6ff 100%);
  border: 1px solid #d8e0eb;
  border-radius: 8px;
}

.account-avatar {
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  color: #2f7de1;
  background: #ffffff;
  border: 1px solid #c8ddfb;
  border-radius: 50%;
  font-size: 30px;
}

.account-identity {
  min-width: 0;
}

.account-identity h2 {
  margin: 0;
  color: #172033;
  font-size: 22px;
}

.account-identity p {
  margin: 6px 0 10px;
  color: #667085;
}

.account-roles {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: #667085;
}

.account-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.account-facts div {
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid #d8e0eb;
  border-radius: 8px;
}

.account-facts dt {
  margin: 0 0 4px;
  color: #667085;
  font-size: 12px;
}

.account-facts dd {
  margin: 0;
  color: #172033;
  font-weight: 700;
}

.account-settings {
  display: grid;
  gap: 12px;
}

.account-setting-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #d8e0eb;
  border-radius: 8px;
}

.account-setting-row.danger-row {
  border-color: var(--el-color-danger-light-7);
}

.setting-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  color: #2f7de1;
  background: #eef6ff;
  border-radius: 8px;
  font-size: 20px;
}

.danger-row .setting-icon {
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.setting-copy h3 {
  margin: 0;
  color: #172033;
  font-size: 16px;
}

.setting-copy p {
  margin: 5px 0 0;
  color: #667085;
  line-height: 1.5;
}

.dialog-form {
  margin-top: 16px;
}

.form-tip {
  width: 100%;
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
}

@media (max-width: 900px) {
  .account-hero,
  .account-setting-row {
    grid-template-columns: 1fr;
  }

  .account-avatar {
    width: 56px;
    height: 56px;
  }

  .account-facts {
    grid-template-columns: 1fr;
  }
}
</style>
