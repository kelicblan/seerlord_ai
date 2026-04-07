import type { CustomRouteRecordRaw } from '@/types/router';

export const examplesRoutes: CustomRouteRecordRaw[] = [
  {
    path: 'examples/list',
    name: 'examples-list',
    component: () => import('@/views/examples/ListTemplate.vue'),
    meta: {
      title: '列表模板',
      description: '列表页面模板示例',
      requiresAuth: true,
    },
  },
];
