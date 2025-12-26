import path from "path"
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      dts: "src/auto-imports.d.ts",
      vueTemplate: true,
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: "src/components.d.ts",
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    chunkSizeWarningLimit: 2000,
    rollupOptions: {
      // 处理第三方依赖的打包告警：仅过滤已知且无实际影响的告警，避免淹没真正问题
      onwarn(warning, warn) {
        if (
          warning.code === 'IMPORT_IS_UNDEFINED'
          && typeof warning.id === 'string'
          && warning.id.includes('node_modules/vue-i18n/')
        ) {
          return
        }
        warn(warning)
      },
      output: {
        // 简单稳定的分包策略：按 node_modules 顶层包名拆分，降低单个 chunk 体积
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          const parts = id.split('node_modules/')[1]?.split('/')
          if (!parts || parts.length === 0) return
          const pkgName = parts[0] === '@' ? `${parts[0]}/${parts[1]}` : parts[0]
          return `vendor-${pkgName.replace('@', '').replace('/', '-')}`
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
