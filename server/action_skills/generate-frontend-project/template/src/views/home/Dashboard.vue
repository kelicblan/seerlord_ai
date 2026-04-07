<script setup lang="ts">
import {
  ArrowRight,
  Connection,
  DataAnalysis,
  Key,
  Lock,
  Memo,
  Setting,
  TrendCharts,
  User,
} from '@element-plus/icons-vue'
import { ref, onMounted } from 'vue'

interface FeatureCard {
  title: string
  description: string
  icon: typeof User
  color: string
  gradient: string
  path: string
}

interface Activity {
  id: number
  user: string
  avatar: string
  action: string
  target: string
  time: string
  type: 'success' | 'warning' | 'info'
}

interface MetricData {
  label: string
  value: number
  suffix: string
  change: number
}

const loading = ref(false)
const currentTime = ref(new Date())
const animatedMetrics = ref<MetricData[]>([])

const features: FeatureCard[] = [
  {
    title: '智能数据分析',
    description: '实时监控业务指标，AI 驱动的趋势预测与异常检测',
    icon: TrendCharts,
    color: '#6366f1',
    gradient: 'from-indigo-500/20 to-indigo-500/5',
    path: '/analytics',
  },
  {
    title: '权限管理',
    description: '细粒度的 RBAC 权限控制，保障系统安全',
    icon: Key,
    color: '#10b981',
    gradient: 'from-emerald-500/20 to-emerald-500/5',
    path: '/permission',
  },
  {
    title: '数据加密',
    description: '端到端加密传输，敏感数据自动脱敏处理',
    icon: Lock,
    color: '#f59e0b',
    gradient: 'from-amber-500/20 to-amber-500/5',
    path: '/encryption',
  },
  {
    title: '流量防护',
    description: '智能限流熔断，防止恶意请求与流量攻击',
    icon: Connection,
    color: '#ef4444',
    gradient: 'from-red-500/20 to-red-500/5',
    path: '/rate-limit',
  },
  {
    title: '日志审计',
    description: '完整的操作记录，追踪每一步操作痕迹',
    icon: Memo,
    color: '#8b5cf6',
    gradient: 'from-violet-500/20 to-violet-500/5',
    path: '/logs',
  },
  {
    title: '系统配置',
    description: '灵活的配置中心，动态调整系统参数',
    icon: Setting,
    color: '#06b6d4',
    gradient: 'from-cyan-500/20 to-cyan-500/5',
    path: '/config',
  },
]

const activities: Activity[] = [
  {
    id: 1,
    user: '张明',
    avatar: 'Z',
    action: '完成了数据分析报告',
    target: 'Q1 季度总结',
    time: '3 分钟前',
    type: 'success',
  },
  {
    id: 2,
    user: '李华',
    avatar: 'L',
    action: '更新了权限配置',
    target: '财务部门角色',
    time: '15 分钟前',
    type: 'info',
  },
  {
    id: 3,
    user: '王芳',
    avatar: 'W',
    action: '提交了系统配置变更',
    target: '数据库连接池',
    time: '32 分钟前',
    type: 'warning',
  },
  {
    id: 4,
    user: '赵强',
    avatar: 'Z',
    action: '导出了用户数据',
    target: '会员列表.csv',
    time: '1 小时前',
    type: 'info',
  },
]

const metrics: MetricData[] = [
  { label: '活跃会话', value: 1247, suffix: '', change: 12.5 },
  { label: 'API 调用', value: 89342, suffix: 'K', change: 8.3 },
  { label: '响应时间', value: 42, suffix: 'ms', change: -15.2 },
  { label: '系统可用性', value: 99.97, suffix: '%', change: 0.02 },
]

const getActivityColor = (type: Activity['type']) => {
  switch (type) {
    case 'success':
      return { bg: 'bg-emerald-500/10', text: 'text-emerald-500' }
    case 'warning':
      return { bg: 'bg-amber-500/10', text: 'text-amber-500' }
    case 'info':
      return { bg: 'bg-blue-500/10', text: 'text-blue-500' }
    default:
      return { bg: 'bg-gray-500/10', text: 'text-gray-500' }
  }
}

const fetchDashboardData = async () => {
  loading.value = true

  try {
    await new Promise((resolve) => setTimeout(resolve, 300))

    animatedMetrics.value = metrics.map((m) => ({
      ...m,
      value: 0,
    }))

    metrics.forEach((metric, index) => {
      setTimeout(() => {
        const target = metric.value
        const startTime = performance.now()
        const duration = 1200

        const updateValue = (currentTime: number) => {
          const elapsed = currentTime - startTime
          const progress = Math.min(elapsed / duration, 1)
          const easeOut = 1 - Math.pow(1 - progress, 4)
          const current = target * easeOut

          animatedMetrics.value[index] = {
            ...metric,
            value: metric.label.includes('%') ? parseFloat(current.toFixed(2)) : Math.floor(current),
          }

          if (progress < 1) {
            requestAnimationFrame(updateValue)
          }
        }

        requestAnimationFrame(updateValue)
      }, index * 100)
    })
  } catch (error) {
    console.error('获取仪表盘数据失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboardData()

  const timer = setInterval(() => {
    currentTime.value = new Date()
  }, 1000)

  return () => clearInterval(timer)
})
</script>

<template>
  <div class="relative min-h-[calc(100vh-120px)] overflow-hidden">
    <div class="absolute inset-0 overflow-hidden">
      <div class="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-[var(--app-primary)]/5 blur-3xl" />
      <div class="absolute -right-32 top-1/3 h-80 w-80 rounded-full bg-indigo-500/5 blur-3xl" />
      <div class="absolute bottom-0 left-1/3 h-64 w-64 rounded-full bg-emerald-500/5 blur-3xl" />
    </div>

    <div class="relative">
      <div class="mb-2 grid grid-cols-2 gap-2 lg:grid-cols-4">
        <div
          v-for="metric in animatedMetrics"
          :key="metric.label"
          class="group relative overflow-hidden rounded-[5px] border border-gray-200 bg-[var(--app-surface)] p-6 backdrop-blur-sm transition-all hover:-translate-y-1 hover:shadow-xl"
        >
          <div class="absolute inset-0 bg-gradient-to-br from-[var(--app-primary)]/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />

          <div class="relative">
            <p class="text-sm font-medium text-[var(--app-text-secondary)]">{{ metric.label }}</p>

            <div class="mt-2 flex items-baseline gap-1">
              <span class="text-3xl font-bold tracking-tight text-[var(--app-text)]">
                {{ metric.value.toLocaleString() }}
              </span>
              <span v-if="metric.suffix" class="text-lg font-medium text-[var(--app-text-secondary)]">
                {{ metric.suffix }}
              </span>
            </div>

            <div class="mt-3 flex items-center gap-1.5">
              <span
                class="inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium"
                :class="metric.change >= 0 ? 'bg-emerald-500/10 text-emerald-600' : 'bg-red-500/10 text-red-600'"
              >
                <svg
                  class="h-3 w-3"
                  :class="metric.change < 0 ? 'rotate-180' : ''"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
                </svg>
                {{ Math.abs(metric.change) }}%
              </span>
              <span class="text-xs text-[var(--app-text-tertiary)]">较昨日</span>
            </div>
          </div>

          <div class="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-[var(--app-primary)]/5 transition-transform group-hover:scale-150" />
        </div>
      </div>

      <div class="mb-2 grid grid-cols-1 gap-2 lg:grid-cols-3">
        <div class="lg:col-span-2">
          <div class="rounded-[5px] border border-gray-200 bg-[var(--app-surface)] p-8 backdrop-blur-sm">
            <div class="mb-6 flex items-center justify-between">
              <div>
                <h2 class="text-xl font-semibold">核心功能</h2>
                <p class="mt-1 text-sm text-[var(--app-text-secondary)]">探索平台提供的强大能力</p>
              </div>
              <button
                type="button"
                class="inline-flex cursor-pointer items-center gap-1 text-sm font-medium text-[var(--app-primary)] transition-colors hover:text-[var(--app-primary-hover)]"
              >
                全部功能
                <ArrowRight class="h-4 w-4" />
              </button>
            </div>

            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <router-link
                v-for="feature in features"
                :key="feature.title"
                :to="feature.path"
                class="group relative overflow-hidden rounded-[5px] border border-gray-200 bg-gradient-to-br p-5 transition-all hover:-translate-y-0.5 hover:shadow-lg"
                :class="feature.gradient"
              >
                <div class="flex items-start gap-4">
                  <div
                    class="flex h-12 w-12 items-center justify-center rounded-[5px] transition-transform group-hover:scale-110"
                    :style="{ backgroundColor: feature.color + '15', color: feature.color }"
                  >
                    <el-icon :size="24">
                      <component :is="feature.icon" />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <h3 class="font-semibold transition-colors group-hover:text-[var(--app-primary)]">
                      {{ feature.title }}
                    </h3>
                    <p class="mt-1 text-sm text-[var(--app-text-secondary)]">
                      {{ feature.description }}
                    </p>
                  </div>
                </div>
                <div
                  class="absolute right-0 top-0 h-24 w-24 rounded-full opacity-20 blur-2xl transition-transform group-hover:scale-150"
                  :style="{ backgroundColor: feature.color }"
                />
              </router-link>
            </div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="rounded-[5px] border border-gray-200 bg-[var(--app-surface)] p-6 backdrop-blur-sm">
            <div class="mb-5 flex items-center justify-between">
              <h2 class="text-lg font-semibold">实时动态</h2>
              <span class="relative flex h-2 w-2">
                <span class="absolute inline-flex h-full w-full animate-pulse rounded-full bg-emerald-500 opacity-75" />
                <span class="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
            </div>

            <div class="space-y-4">
              <div
                v-for="activity in activities"
                :key="activity.id"
                class="group flex items-start gap-3 rounded-[5px] p-3 transition-colors hover:bg-[var(--app-muted-surface)]"
              >
                <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br" :class="getActivityColor(activity.type).bg">
                  <span class="text-sm font-semibold" :class="getActivityColor(activity.type).text">
                    {{ activity.avatar }}
                  </span>
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-sm leading-snug">
                    <span class="font-medium">{{ activity.user }}</span>
                    <span class="text-[var(--app-text-secondary)]"> {{ activity.action }}</span>
                  </p>
                  <p class="mt-0.5 truncate text-xs text-[var(--app-primary)]">{{ activity.target }}</p>
                  <p class="mt-1 text-xs text-[var(--app-text-tertiary)]">{{ activity.time }}</p>
                </div>
              </div>
            </div>

            <button
              type="button"
              class="mt-4 w-full cursor-pointer rounded-[5px] border border-dashed border-gray-200 py-2.5 text-sm text-[var(--app-text-secondary)] transition-colors hover:border-[var(--app-primary)] hover:text-[var(--app-primary)]"
            >
              查看全部动态
            </button>
          </div>

          <div class="rounded-[5px] border border-gray-200 bg-gradient-to-br from-[var(--app-primary)] to-indigo-600 p-6 text-white">
            <div class="mb-4 flex items-center gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-[5px] bg-white/20">
                <el-icon :size="20">
                  <DataAnalysis />
                </el-icon>
              </div>
              <div>
                <h3 class="font-semibold">数据洞察</h3>
                <p class="text-sm text-white/70">AI 智能分析助手</p>
              </div>
            </div>
            <p class="mb-4 text-sm leading-relaxed text-white/90">
              本周业务数据呈现稳健增长趋势，用户活跃度提升 12.5%，建议关注转化率优化。
            </p>
            <button
              type="button"
              class="w-full cursor-pointer rounded-[5px] bg-white/20 px-4 py-2.5 text-sm font-medium backdrop-blur-sm transition-colors hover:bg-white/30"
            >
              查看详细报告
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
