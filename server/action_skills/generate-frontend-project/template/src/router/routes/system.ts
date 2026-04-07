import type { CustomRouteRecordRaw } from '@/types/router';

export const systemRoutes: CustomRouteRecordRaw[] = [
  {
    path: '',
    name: 'home',
    component: () => import('@/views/home/Dashboard.vue'),
    meta: {
      title: '首页',
      description: '系统首页概览',
      requiresAuth: true,
    },
  },
  {
    path: 'system/user',
    name: 'system-user',
    component: () => import('@/views/system/user/UserList.vue'),
    meta: {
      title: '用户管理',
      description: '系统用户管理',
      requiresAuth: true,
      permissions: ['system:user:view'],
    },
  },
  {
    path: 'system/role',
    name: 'system-role',
    component: () => import('@/views/system/role/RoleList.vue'),
    meta: {
      title: '角色权限',
      description: '系统角色权限管理',
      requiresAuth: true,
      permissions: ['system:role:view'],
    },
  },
  {
    path: 'system/dept',
    name: 'system-dept',
    component: () => import('@/views/system/dept/DeptTree.vue'),
    meta: {
      title: '部门管理',
      description: '组织部门管理',
      requiresAuth: true,
      permissions: ['system:dept:view'],
    },
  },
  {
    path: 'system/log/operate',
    name: 'system-log-operate',
    component: () => import('@/views/system/log/OperateLog.vue'),
    meta: {
      title: '操作日志',
      description: '系统操作日志',
      requiresAuth: true,
      permissions: ['system:log:operate'],
    },
  },
  {
    path: 'system/log/login',
    name: 'system-log-login',
    component: () => import('@/views/system/log/LoginLog.vue'),
    meta: {
      title: '登录日志',
      description: '系统登录日志',
      requiresAuth: true,
      permissions: ['system:log:login'],
    },
  },
  {
    path: 'system/notice',
    name: 'system-notice',
    component: () => import('@/views/system/notice/SystemNotice.vue'),
    meta: {
      title: '消息通知',
      description: '系统消息通知',
      requiresAuth: true,
      permissions: ['system:notice:view'],
    },
  },
  {
    path: 'system/backup',
    name: 'system-backup',
    component: () => import('@/views/system/backup/SystemBackup.vue'),
    meta: {
      title: '数据备份',
      description: '系统数据备份',
      requiresAuth: true,
      permissions: ['system:backup:view'],
    },
  },
  {
    path: 'system/config',
    name: 'system-config',
    component: () => import('@/views/system/config/SystemConfig.vue'),
    meta: {
      title: '系统配置',
      description: '系统参数配置',
      requiresAuth: true,
      permissions: ['system:config:view'],
    },
  },
  {
    path: 'system/init',
    name: 'system-init',
    component: () => import('@/views/system/init/SystemInit.vue'),
    meta: {
      title: '系统初始化',
      description: '系统初始化向导',
      requiresAuth: true,
    },
  },
  {
    path: 'system/help',
    name: 'system-help',
    component: () => import('@/views/system/help/SystemHelp.vue'),
    meta: {
      title: '帮助文档',
      description: '系统使用帮助',
      requiresAuth: true,
    },
  },
];
