<template>
  <el-tabs v-model="activeTab" class="admin-tabs" @tab-change="changeTab">
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
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button text type="primary" @click="openRoleAssign(row)">分配角色</el-button>
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
              <el-button text type="primary" @click="openPermissionAssign(row)">绑定权限</el-button>
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

    <el-tab-pane label="操作日志" name="logs">
      <section class="table-panel">
        <div class="panel-head">
          <div>
            <h2>操作日志</h2>
            <p>查看最近接口访问记录和业务处理结果。</p>
          </div>
        </div>
        <el-table v-loading="loading" :data="logs" row-key="id">
          <el-table-column prop="created_at" label="时间" min-width="180" show-overflow-tooltip />
          <el-table-column prop="method" label="方法" width="90" />
          <el-table-column prop="path" label="路径" min-width="240" show-overflow-tooltip />
          <el-table-column prop="operation" label="权限点" min-width="180" />
          <el-table-column prop="status_code" label="业务码" width="100" />
          <el-table-column prop="response_message" label="结果" min-width="180" />
        </el-table>
      </section>
    </el-tab-pane>
  </el-tabs>

  <el-dialog v-model="userVisible" title="新增用户" width="620px">
    <el-form :model="userForm" label-width="92px">
      <el-form-item label="账号"><el-input v-model="userForm.username" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="userForm.password" type="password" show-password /></el-form-item>
      <el-form-item label="姓名"><el-input v-model="userForm.full_name" /></el-form-item>
      <el-form-item label="部门"><el-input v-model="userForm.department" /></el-form-item>
      <el-form-item label="角色">
        <el-select v-model="userForm.role_ids" multiple style="width: 100%">
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
    <el-select v-model="selectedRoleIds" multiple style="width: 100%">
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
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  assignRolePermissions,
  assignUserRoles,
  createUser,
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
  '/system/users': 'users',
  '/system/roles': 'roles',
  '/system/menus': 'menus',
  '/system/permissions': 'permissions',
  '/system/operation-logs': 'logs'
}
const tabToRoute = computed<Record<string, string>>(() => Object.fromEntries(
  Object.entries(routeToTab).map(([path, tab]) => [tab, path])
))
const activeTab = ref(routeToTab[route.path] || 'users')
const loading = ref(false)
const saving = ref(false)
const users = ref<UserItem[]>([])
const roles = ref<RoleItem[]>([])
const menus = ref<MenuItem[]>([])
const permissions = ref<PermissionItem[]>([])
const logs = ref<OperationLogItem[]>([])
const userVisible = ref(false)
const roleAssignVisible = ref(false)
const permissionAssignVisible = ref(false)
const editingUser = ref<UserItem | null>(null)
const editingRole = ref<RoleItem | null>(null)
const selectedRoleIds = ref<number[]>([])
const selectedPermissionIds = ref<number[]>([])
const userForm = reactive({
  username: '',
  password: '',
  full_name: '',
  department: '',
  is_active: true,
  role_ids: [] as number[]
})

function roleName(id: number) {
  return roles.value.find((role) => role.id === id)?.name || `角色${id}`
}

async function loadAll() {
  loading.value = true
  try {
    const [userRows, roleRows, menuRows, permissionRows, logRows] = await Promise.all([
      listUsers(),
      listRoles(),
      listMenus(),
      listPermissions(),
      listOperationLogs()
    ])
    users.value = userRows
    roles.value = roleRows
    menus.value = menuRows
    permissions.value = permissionRows
    logs.value = logRows
  } finally {
    loading.value = false
  }
}

async function saveUser() {
  saving.value = true
  try {
    await createUser(userForm)
    ElMessage.success('用户已创建')
    userVisible.value = false
    await loadAll()
  } finally {
    saving.value = false
  }
}

async function changeUserActive(id: number, isActive: boolean) {
  await setUserActive(id, isActive)
  await loadAll()
}

function openRoleAssign(row: UserItem) {
  editingUser.value = row
  selectedRoleIds.value = [...row.role_ids]
  roleAssignVisible.value = true
}

async function saveRoleAssign() {
  if (!editingUser.value) return
  saving.value = true
  try {
    await assignUserRoles(editingUser.value.id, selectedRoleIds.value)
    ElMessage.success('角色已更新')
    roleAssignVisible.value = false
    await loadAll()
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

function changeTab(tabName: string | number) {
  const nextPath = tabToRoute.value[String(tabName)]
  if (nextPath && nextPath !== route.path) {
    router.replace(nextPath)
  }
}

watch(
  () => route.path,
  (path) => {
    activeTab.value = routeToTab[path] || 'users'
  }
)

onMounted(loadAll)
</script>
