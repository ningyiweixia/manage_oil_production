import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

const projectRoot = fileURLToPath(new URL('.', import.meta.url))
const frontendDist = fileURLToPath(new URL('../deploy/frontend-dist', import.meta.url))

export default defineConfig({
  root: projectRoot,
  plugins: [vue()],
  build: {
    outDir: frontendDist,
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replaceAll('\\', '/')
          if (!normalizedId.includes('node_modules')) return undefined
          if (normalizedId.includes('/vue/') || normalizedId.includes('/vue-router/')) return 'vue'
          if (normalizedId.includes('/element-plus/') || normalizedId.includes('/@element-plus/icons-vue/')) return 'element'
          if (normalizedId.includes('/echarts/')) return 'charts'
          return undefined
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true
      }
    }
  }
})
