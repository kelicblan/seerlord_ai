"""脚手架模板数据：包含所有脚手架文件的模板字符串。按 checklist 规范，数据文件不计入生成器行数限制。"""
from typing import Dict

PACKAGE_JSON = '''{
  "name": "generated-project",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint ."
  },
  "dependencies": {
    "vue": "^3.5.13",
    "vue-router": "^4.5.0",
    "pinia": "^3.0.4",
    "pinia-plugin-persistedstate": "^4.7.1",
    "element-plus": "^2.9.7",
    "@element-plus/icons-vue": "^2.3.1",
    "@vueuse/core": "^13.0.0",
    "axios": "^1.8.4"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.1",
    "@tailwindcss/vite": "^4.0.15",
    "typescript": "~5.6.2",
    "vite": "^6.0.0",
    "vue-tsc": "^2.1.10",
    "eslint": "^9.24.0",
    "eslint-plugin-vue": "^10.0.0",
    "tailwindcss": "^4.0.15"
  }
}
'''

VITE_CONFIG = '''import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
    },
  },
})
'''

TSCONFIG_JSON = '''{
  "compilerOptions": {
    "target": "ESNext",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ESNext", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue"]
}
'''

TSCONFIG_APP = '''{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "composite": true,
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "types": ["vite/client"]
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue"]
}
'''

TSCONFIG_NODE = '''{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "composite": true,
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "types": ["node"]
  },
  "include": ["vite.config.ts"]
}
'''

INDEX_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Generated Project</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
'''

MAIN_TS = '''import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus)

app.mount('#app')
'''

APP_VUE = '''<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <el-config-provider>
    <RouterView />
  </el-config-provider>
</template>

<style>
#app {
  width: 100%;
  height: 100%;
}
</style>
'''

ROUTER_TS = '''import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
  {
    path: '/home',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '首页', requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const title = to.meta?.title as string
  if (title) {
    document.title = `${title} - Generated Project`
  }
  next()
})

export default router
'''

HTTP_TS = '''import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

const http: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

http.interceptors.response.use(
  (response: AxiosResponse) => {
    const { data } = response
    if (data.code !== 0 && data.code !== 200) {
      ElMessage.error(data.message || 'Request failed')
      return Promise.reject(new Error(data.message || 'Request failed'))
    }
    return response
  },
  (error: AxiosError) => {
    if (error.response) {
      const { status } = error.response
      switch (status) {
        case 401:
          ElMessage.error('Unauthorized, please login again')
          localStorage.removeItem('token')
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error('Access denied')
          break
        case 404:
          ElMessage.error('Resource not found')
          break
        case 500:
          ElMessage.error('Server error')
          break
        default:
          ElMessage.error('Request failed')
      }
    } else if (error.request) {
      ElMessage.error('Network error, please check your connection')
    } else {
      ElMessage.error('Request error')
    }
    return Promise.reject(error)
  }
)

export default http

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export function request<T = any>(config: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return http(config) as any
}
'''

APP_STORE_TS = '''import { defineStore } from 'pinia'
import { ref } from 'vue'

interface UserInfo {
  id: string
  username: string
  nickname?: string
  avatar?: string
  roles: string[]
  permissions: string[]
}

export const useAppStore = defineStore('app', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<UserInfo | null>(null)
  const collapsed = ref(false)
  const theme = ref<'light' | 'dark'>('light')

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function setUserInfo(info: UserInfo) {
    userInfo.value = info
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  function toggleCollapsed() {
    collapsed.value = !collapsed.value
  }

  function setTheme(newTheme: 'light' | 'dark') {
    theme.value = newTheme
  }

  return {
    token,
    userInfo,
    collapsed,
    theme,
    setToken,
    setUserInfo,
    logout,
    toggleCollapsed,
    setTheme,
  }
}, {
  persist: {
    key: 'app-store',
    pick: ['token', 'userInfo', 'collapsed', 'theme'],
  },
})
'''

STYLE_CSS = '''@import "tailwindcss";

:root {
  --color-primary: #409eff;
  --color-success: #67c23a;
  --color-warning: #e6a23c;
  --color-danger: #f56c6c;
  --color-info: #909399;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body,
#app {
  width: 100%;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

a {
  text-decoration: none;
  color: inherit;
}
'''

VITE_ENV_DTS = '''/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
'''

SCAFFOLD_FILES: Dict[str, str] = {
    "package.json": PACKAGE_JSON,
    "vite.config.ts": VITE_CONFIG,
    "tsconfig.json": TSCONFIG_JSON,
    "tsconfig.app.json": TSCONFIG_APP,
    "tsconfig.node.json": TSCONFIG_NODE,
    "index.html": INDEX_HTML,
    "src/main.ts": MAIN_TS,
    "src/App.vue": APP_VUE,
    "src/router/index.ts": ROUTER_TS,
    "src/api/http.ts": HTTP_TS,
    "src/stores/app.ts": APP_STORE_TS,
    "src/style.css": STYLE_CSS,
    "src/vite-env.d.ts": VITE_ENV_DTS,
}
