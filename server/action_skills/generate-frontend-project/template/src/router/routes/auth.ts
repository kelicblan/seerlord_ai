import type { CustomRouteRecordRaw } from '@/types/router';
import { LOGIN_ROUTE } from '@/constants/app';

export const authRoutes: CustomRouteRecordRaw[] = [
  {
    path: LOGIN_ROUTE,
    name: 'login',
    component: () => import('@/views/login/Login.vue'),
    meta: {
      title: '登录',
      description: '用户登录页面',
      guestOnly: true,
    },
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: () => import('@/views/login/ResetPassword.vue'),
    meta: {
      title: '重置密码',
      description: '密码重置页面',
      guestOnly: true,
    },
  },
];
