import type { CustomRouteRecordRaw } from '@/types/router';

export const securityRoutes: CustomRouteRecordRaw[] = [
  {
    path: 'security/encryption',
    name: 'security-encryption',
    component: () => import('@/views/security/encryption/EncryptionConfig.vue'),
    meta: {
      title: '加密配置',
      description: '数据加密算法配置',
      requiresAuth: true,
      permissions: ['security:encryption:view'],
    },
  },
  {
    path: 'security/rate-limit',
    name: 'security-rate-limit',
    component: () => import('@/views/security/rate-limit/RateLimit.vue'),
    meta: {
      title: '限流配置',
      description: 'API请求限流配置',
      requiresAuth: true,
      permissions: ['security:rate-limit:view'],
    },
  },
  {
    path: 'security/permission',
    name: 'security-permission',
    component: () => import('@/views/security/permission/PermissionControl.vue'),
    meta: {
      title: '权限控制',
      description: '细粒度权限控制管理',
      requiresAuth: true,
      permissions: ['security:permission:view'],
    },
  },
  {
    path: 'security/anomaly',
    name: 'security-anomaly',
    component: () => import('@/views/security/anomaly/AnomalyDetection.vue'),
    meta: {
      title: '异常检测',
      description: '安全异常行为检测',
      requiresAuth: true,
      permissions: ['security:anomaly:view'],
    },
  },
];
