import type { UserInfo } from '@/stores/types';

export interface UserState {
  userInfo: UserInfo | null;
  permissions: string[];
  roles: string[];
}

export interface UserActions {
  setUser(info: UserInfo): void;
  clearUser(): void;
  updateUserInfo(updates: Partial<UserInfo>): void;
  setPermissions(perms: string[]): void;
  setRoles(userRoles: string[]): void;
  hasPermission(permission: string): boolean;
  hasRole(role: string): boolean;
  hasAnyPermission(permList: string[]): boolean;
  hasAllPermissions(permList: string[]): boolean;
}

export type UserStore = UserState & UserActions;
