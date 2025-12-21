import { createRouter, createWebHistory } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import HomeView from '@/views/HomeView.vue'
import { useAuth } from '@/composables/useAuth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { title: '登录' }
    },
    {
      path: '/',
      component: DefaultLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'home',
          component: HomeView,
          meta: { title: 'common.nav_agent' }
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/UserManage.vue'),
          meta: { title: 'common.nav_user_mgmt' }
        },
        {
          path: 'agents',
          name: 'agents',
          component: () => import('@/views/AgentManage.vue'),
          meta: { title: 'common.nav_agent_mgmt' }
        },
        {
          path: 'mcp',
          name: 'mcp',
          component: () => import('@/views/MCPManage.vue'),
          meta: { title: 'common.nav_mcp_mgmt' }
        },
        {
          path: 'history',
          name: 'history',
          component: () => import('@/views/ChatHistory.vue'),
          meta: { title: 'common.nav_history' }
        },
        {
          path: 'skills',
          name: 'skills',
          component: () => import('@/views/SkillManage.vue'),
          meta: { title: 'common.nav_skills' }
        }
      ]
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const { isAuthenticated } = useAuth()
  
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    next('/login')
  } else if (to.path === '/login' && isAuthenticated.value) {
    next('/')
  } else {
    next()
  }
})

export default router
