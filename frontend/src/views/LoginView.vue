<template>
  <main class="login-shell">
    <section class="login-panel">
      <div>
        <p class="eyebrow">Factory Operations</p>
        <h1>Workover Management System</h1>
        <p class="login-copy">Sign in with your assigned account to manage approvals and project pool data.</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="Username" prop="username">
          <el-input v-model="form.username" size="large" autocomplete="username" />
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input v-model="form.password" size="large" type="password" autocomplete="current-password" show-password />
        </el-form-item>
        <el-button class="full-button" size="large" type="primary" :loading="loading" @click="handleLogin">Sign in</el-button>
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
  username: [{ required: true, message: 'Please enter your username', trigger: 'blur' }],
  password: [{ required: true, message: 'Please enter your password', trigger: 'blur' }]
}

async function handleLogin() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const result = await login(form)
    localStorage.setItem('access_token', result.token.access_token)
    localStorage.setItem('refresh_token', result.token.refresh_token)
    localStorage.setItem('current_user', JSON.stringify(result.user))
    ElMessage.success('Signed in')
    router.push(typeof route.query.redirect === 'string' ? route.query.redirect : '/approval')
  } catch {
    ElMessage.error('Sign-in failed. Check your credentials or backend service.')
  } finally {
    loading.value = false
  }
}
</script>
