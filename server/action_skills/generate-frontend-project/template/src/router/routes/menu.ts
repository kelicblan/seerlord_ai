import type { Component } from 'vue'
import {
  HomeFilled,
  List,
  User,
  Setting,
  Key,
  OfficeBuilding,
  Bell,
  Document,
  Clock,
  Warning,
  FolderOpened,
  Connection,
  Refresh,
  Odometer,
  Tools,
  DocumentDelete,
} from '@element-plus/icons-vue'

export interface MenuItem {
  icon: Component
  label: string
  path: string
  permission?: string
}

export interface MenuGroup {
  title: string
  items: MenuItem[]
}

export const menuConfig: MenuGroup[] = [
  {
    title: '总览',
    items: [
      {
        icon: HomeFilled,
        label: '首页',
        path: '/',
      },
    ],
  },
  {
    title: '基础模板',
    items: [
      {
        icon: List,
        label: '列表模板',
        path: '/examples/list',
      },
    ],
  },
  {
    title: '系统管理',
    items: [
      {
        icon: User,
        label: '用户管理',
        path: '/system/user',
        permission: 'system:user:view',
      },
      {
        icon: Tools,
        label: '角色管理',
        path: '/system/role',
        permission: 'system:role:view',
      },
      {
        icon: Key,
        label: '权限控制',
        path: '/security/permission',
        permission: 'security:permission:view',
      },
      {
        icon: OfficeBuilding,
        label: '部门管理',
        path: '/system/dept',
        permission: 'system:dept:view',
      },
      {
        icon: Setting,
        label: '系统配置',
        path: '/system/config',
        permission: 'system:config:view',
      },
      {
        icon: Bell,
        label: '系统通知',
        path: '/system/notice',
        permission: 'system:notice:view',
      },
      {
        icon: Document,
        label: '操作日志',
        path: '/system/log/operate',
        permission: 'system:log:operate',
      },
      {
        icon: Clock,
        label: '登录日志',
        path: '/system/log/login',
        permission: 'system:log:login',
      },
    ],
  },
  {
    title: '系统工具',
    items: [
      {
        icon: DocumentDelete,
        label: '系统备份',
        path: '/system/backup',
        permission: 'system:backup:view',
      },
      {
        icon: Warning,
        label: '异常检测',
        path: '/security/anomaly',
        permission: 'security:anomaly:view',
      },
      {
        icon: Connection,
        label: '加密配置',
        path: '/security/encryption',
        permission: 'security:encryption:view',
      },
      {
        icon: Odometer,
        label: '限流配置',
        path: '/security/rate-limit',
        permission: 'security:rate-limit:view',
      },
      {
        icon: FolderOpened,
        label: '系统帮助',
        path: '/system/help',
      },
    ],
  },
]
