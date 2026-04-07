<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElButton,
  ElAvatar,
  ElIcon,
  ElBadge,
} from 'element-plus'
import {
  HomeFilled,
  Bell,
  ArrowRight,
  Star,
  Clock,
} from '@element-plus/icons-vue'

const router = useRouter()

interface QuickAction {
  id: string
  title: string
  icon: string
  color: string
  path: string
}

interface Activity {
  id: string
  title: string
  subtitle: string
  tag: string
  tagType: string
}

const userInfo = reactive({
  name: '张三',
  avatar: '',
  points: 2580,
  level: '黄金会员',
})

const quickActions = ref<QuickAction[]>([
  { id: '1', title: '订单', icon: 'ShoppingCart', color: 'bg-blue-500', path: '/mobile/orders' },
  { id: '2', title: '优惠券', icon: 'Ticket', color: 'bg-orange-500', path: '/mobile/coupons' },
  { id: '3', title: '地址', icon: 'Location', color: 'bg-green-500', path: '/mobile/address' },
  { id: '4', title: '设置', icon: 'Setting', color: 'bg-gray-500', path: '/mobile/settings' },
])

const activities = ref<Activity[]>([
  {
    id: '1',
    title: '新人专享',
    subtitle: '首单立减 50 元',
    tag: '限时',
    tagType: 'danger',
  },
  {
    id: '2',
    title: '积分翻倍',
    subtitle: '今日购物享双倍积分',
    tag: '今日',
    tagType: 'warning',
  },
  {
    id: '3',
    title: '会员专享',
    subtitle: '全场 8 折起',
    tag: '会员',
    tagType: 'success',
  },
])

const recommendedProducts = ref([
  {
    id: '1',
    name: '智能手环 Pro',
    price: 299,
    originalPrice: 399,
    sales: 12580,
    image: 'https://via.placeholder.com/150x150/6366F1/FFFFFF?text=Band',
  },
  {
    id: '2',
    name: '无线蓝牙耳机',
    price: 199,
    originalPrice: 299,
    sales: 8932,
    image: 'https://via.placeholder.com/150x150/EC4899/FFFFFF?text=耳机',
  },
  {
    id: '3',
    name: '便携充电宝',
    price: 99,
    originalPrice: 149,
    sales: 15632,
    image: 'https://via.placeholder.com/150x150/F59E0B/FFFFFF?text=充电宝',
  },
  {
    id: '4',
    name: '运动休闲鞋',
    price: 259,
    originalPrice: 359,
    sales: 4521,
    image: 'https://via.placeholder.com/150x150/8B5CF6/FFFFFF?text=运动鞋',
  },
])

const handleQuickAction = (action: QuickAction) => {
  router.push(action.path)
}

const handleProductClick = (product: typeof recommendedProducts.value[0]) => {
  router.push(`/product/${product.id}`)
}

const formatPrice = (price: number) => {
  return price.toFixed(2)
}

const formatSales = (sales: number) => {
  if (sales >= 10000) {
    return (sales / 10000).toFixed(1) + '万'
  }
  return sales.toString()
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <div class="bg-gradient-to-r from-blue-500 to-purple-600 px-4 pt-4 pb-8">
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
          <el-avatar :size="48" class="border-2 border-white">
            <el-icon size="24"><HomeFilled /></el-icon>
          </el-avatar>
          <div class="text-white">
            <div class="text-lg font-semibold">{{ userInfo.name }}</div>
            <div class="text-sm opacity-90">{{ userInfo.level }}</div>
          </div>
        </div>

        <el-badge :value="3" type="danger" class="relative">
          <el-button text circle class="text-white touch-manipulation">
            <el-icon size="24"><Bell /></el-icon>
          </el-button>
        </el-badge>
      </div>

      <div class="bg-white rounded-2xl p-4 shadow-lg">
        <div class="flex justify-around">
          <div class="text-center">
            <div class="text-2xl font-bold text-gray-900">{{ userInfo.points }}</div>
            <div class="text-xs text-gray-500 mt-1">积分</div>
          </div>
          <div class="w-px bg-gray-200" />
          <div class="text-center">
            <div class="text-2xl font-bold text-gray-900">12</div>
            <div class="text-xs text-gray-500 mt-1">优惠券</div>
          </div>
          <div class="w-px bg-gray-200" />
          <div class="text-center">
            <div class="text-2xl font-bold text-gray-900">5</div>
            <div class="text-xs text-gray-500 mt-1">待收货</div>
          </div>
        </div>
      </div>
    </div>

    <div class="px-4 -mt-4 relative z-10">
      <div class="bg-white rounded-2xl shadow-md p-4">
        <div class="grid grid-cols-4 gap-4">
          <button
            v-for="action in quickActions"
            :key="action.id"
            class="flex flex-col items-center touch-manipulation"
            @click="() => handleQuickAction(action)"
          >
            <div
              class="w-12 h-12 rounded-xl flex items-center justify-center mb-2"
              :class="action.color"
            >
              <el-icon size="24" class="text-white">
                <component :is="action.icon" />
              </el-icon>
            </div>
            <span class="text-xs text-gray-700">{{ action.title }}</span>
          </button>
        </div>
      </div>
    </div>

    <div class="px-4 mt-6">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-lg font-semibold text-gray-900">热门活动</h2>
        <button class="text-sm text-blue-500 touch-manipulation flex items-center">
          查看更多
          <el-icon size="16"><ArrowRight /></el-icon>
        </button>
      </div>

      <div class="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
        <div
          v-for="activity in activities"
          :key="activity.id"
          class="flex-shrink-0 bg-white rounded-xl p-4 shadow-sm border border-gray-100 min-w-[200px]"
        >
          <el-tag :type="activity.tagType" size="small" class="mb-2">
            {{ activity.tag }}
          </el-tag>
          <div class="text-base font-semibold text-gray-900">{{ activity.title }}</div>
          <div class="text-sm text-gray-500 mt-1">{{ activity.subtitle }}</div>
        </div>
      </div>
    </div>

    <div class="px-4 mt-6">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-lg font-semibold text-gray-900">为你推荐</h2>
        <button class="text-sm text-blue-500 touch-manipulation flex items-center">
          换一批
          <el-icon size="16"><Clock /></el-icon>
        </button>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div
          v-for="product in recommendedProducts"
          :key="product.id"
          class="bg-white rounded-xl overflow-hidden shadow-sm border border-gray-100 touch-manipulation transition-transform active:scale-95"
          @click="() => handleProductClick(product)"
        >
          <div class="relative">
            <img
              :src="product.image"
              :alt="product.name"
              class="w-full aspect-square object-cover"
            >
            <div class="absolute top-2 right-2 bg-red-500 text-white text-xs px-2 py-1 rounded-full">
              爆款
            </div>
          </div>

          <div class="p-3">
            <div class="text-sm font-medium text-gray-900 line-clamp-2 mb-2">
              {{ product.name }}
            </div>
            <div class="flex items-baseline gap-2">
              <span class="text-lg font-bold text-red-500">
                ¥{{ formatPrice(product.price) }}
              </span>
              <span class="text-xs text-gray-400 line-through">
                ¥{{ formatPrice(product.originalPrice) }}
              </span>
            </div>
            <div class="flex items-center justify-between mt-2">
              <span class="text-xs text-gray-500">
                已售 {{ formatSales(product.sales) }}
              </span>
              <el-icon size="14" class="text-gray-400"><Star /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="h-8" />
  </div>
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.touch-manipulation {
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
</style>
