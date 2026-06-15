<template>
  <main class="login-shell">
    <section class="login-panel">
      <div>
        <p class="eyebrow">Frontend & UI/UX</p>
        <h1>采油二厂井下作业管理系统</h1>
        <p class="login-copy">上修项目审批、实时待办提醒与统计分析看板。</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="账号" prop="username">
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
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { login } from '../api/auth'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'ChangeMe_123!' })

const rules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
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
    ElMessage.success('登录成功')
    router.push('/approval')
  } catch (error) {
    if (axios.isAxiosError(error) && !error.response) {
      localStorage.setItem('access_token', 'demo-token')
      localStorage.setItem('current_user', JSON.stringify({ full_name: '演示用户', department: '前端联调环境' }))
      ElMessage.warning('后端未连接，已进入演示模式')
      router.push('/approval')
      return
    }
    ElMessage.error('登录失败，请检查账号密码或后端接口返回')
  } finally {
    loading.value = false
  }
}
</script>
