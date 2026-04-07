export interface User {
  id: number;
  username: string;
  email?: string;
  phone?: string;
  status: number;
  roles: string[];
  deptId?: number;
  createTime: string;
  updateTime?: string;
}

export interface Role {
  id: number;
  name: string;
  code: string;
  description?: string;
  status: number;
  permissions: string[];
  createTime: string;
}

export interface Dept {
  id: number;
  name: string;
  parentId?: number;
  orderNum?: number;
  leader?: string;
  phone?: string;
  email?: string;
}

export interface OperateLog {
  id: number;
  username: string;
  module: string;
  action: string;
  method: string;
  url: string;
  ip: string;
  location?: string;
  params?: string;
  result?: string;
  duration?: number;
  createTime: string;
}

export interface LoginLog {
  id: number;
  username: string;
  ip: string;
  location?: string;
  browser?: string;
  os?: string;
  status: number;
  msg?: string;
  createTime: string;
}

export interface SystemConfig {
  id: number;
  key: string;
  value: string;
  name: string;
  group?: string;
  type: string;
  description?: string;
  createTime: string;
  updateTime?: string;
}

export interface Backup {
  id: number;
  name: string;
  size: string;
  path: string;
  status: number;
  createTime: string;
}

export interface Notice {
  id: number;
  title: string;
  content: string;
  type: number;
  status: number;
  createTime: string;
}
