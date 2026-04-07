import type { RouteRecordRaw } from 'vue-router';

export interface RouteMeta {
  title?: string;
  icon?: string;
  requiresAuth?: boolean;
  guestOnly?: boolean;
  permissions?: string[];
  hidden?: boolean;
  keepAlive?: boolean;
  activeMenu?: string;
  noCache?: boolean;
  affix?: boolean;
  breadcrumb?: boolean;
  description?: string;
  errorCode?: number;
}

export type CustomRouteRecordRaw = RouteRecordRaw & {
  meta?: RouteMeta;
  children?: CustomRouteRecordRaw[];
};

export interface RoutePermission {
  path: string;
  name: string;
  meta: RouteMeta;
}
