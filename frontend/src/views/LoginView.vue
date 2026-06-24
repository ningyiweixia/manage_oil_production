<template>
  <main class="login-shell">
    <section class="login-panel">
      <div>
        <p class="eyebrow">采油二厂</p>
        <h1>井下作业管理系统</h1>
        <p class="login-copy">使用分配账号登录，进入项目池提报、审批流转和统计分析工作台。</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" size="large" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" size="large" type="password" autocomplete="current-password" show-password />
        </el-form-item>
        <el-button class="full-button" size="large" type="primary" :loading="loading" @click="handleLogin">登录</el-button>
      </el-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { login } from '../api/auth'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const result = await login(form)
    localStorage.setItem('access_token', result.token.access_token)
    localStorage.setItem('refresh_token', result.token.refresh_token)
    localStorage.setItem('current_user', JSON.stringify(result.user))
    localStorage.setItem('permissions', JSON.stringify(result.permissions || []))
    localStorage.setItem('menus', JSON.stringify(result.menus || []))
    ElMessage.success('登录成功')
    router.push(typeof route.query.redirect === 'string' ? route.query.redirect : '/approval')
  } catch {
    ElMessage.error('登录失败，请检查账号密码或后端服务')
  } finally {
    loading.value = false
  }
}
</script>
