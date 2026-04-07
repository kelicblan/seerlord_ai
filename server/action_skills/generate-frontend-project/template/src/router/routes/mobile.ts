import type { CustomRouteRecordRaw } from '@/types/router';

export const mobileRoutes: CustomRouteRecordRaw[] = [
  {
    path: '/mobile',
    name: 'mobile-home',
    component: () => import('@/layouts/MobileLayout.vue'),
    meta: {
      title: '移动端首页',
      description: '移动端主页面',
      requiresAuth: true,
    },
    children: [
      {
        path: '',
        name: 'mobile-dashboard',
        component: () => import('@/views/mobile/index/MobileHome.vue'),
        meta: {
          title: '移动端首页',
          description: '移动端数据概览',
          requiresAuth: true,
        },
      },
    ],
  },
];
