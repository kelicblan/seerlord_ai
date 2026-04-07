import { createRouter, createWebHistory } from 'vue-router';
import type { CustomRouteRecordRaw } from '@/types/router';

import { authRoutes } from './routes/auth';
import { systemRoutes } from './routes/system';
import { securityRoutes } from './routes/security';
import { mobileRoutes } from './routes/mobile';
import { examplesRoutes } from './routes/examples';

import { authGuard } from './guards/authGuard';
import { permissionGuard } from './guards/permissionGuard';
import { errorGuard, notFoundGuard } from './guards/errorGuard';

const APP_TITLE = 'Vue Admin Starter';

const routes: CustomRouteRecordRaw[] = [
  ...authRoutes,
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: {
      requiresAuth: true,
    },
    children: [
      ...systemRoutes,
      ...securityRoutes,
      ...examplesRoutes,
    ],
  },
  ...mobileRoutes,
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('@/views/Error403View.vue'),
    meta: {
      title: '无权限访问',
      description: '您没有访问该页面的权限',
      errorCode: 403,
    },
  },
  {
    path: '/500',
    name: 'server-error',
    component: () => import('@/views/Error500View.vue'),
    meta: {
      title: '服务器错误',
      description: '服务器内部错误',
      errorCode: 500,
    },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: {
      title: '页面不存在',
      description: '访问的页面不存在或已迁移',
    },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({
    left: 0,
    top: 0,
  }),
});

router.beforeEach(async (to, from, next) => {
  await authGuard(to, from, next);
});

router.beforeEach(async (to, from, next) => {
  await permissionGuard(to, from, next);
});

router.beforeEach((to, from, next) => {
  errorGuard(to, from, next);
});

router.afterEach((to) => {
  notFoundGuard(to, {} as unknown as typeof to, () => {});

  const pageTitle = to.meta.title ? `${to.meta.title} · ${APP_TITLE}` : APP_TITLE;
  document.title = pageTitle;
});

export default router;
