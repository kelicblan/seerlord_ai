import type { UserState, UserActions } from '@/types/store/user';
import type { AppState, AppActions } from '@/types/store/app';

export type { UserState, UserActions };
export type { AppState, AppActions };
export type { AppState as AuthState, AppActions as AuthActions };
export type { AppState as OfflineState, AppActions as OfflineActions };
export type AppStoreActions = AppState & AppActions;

export type ThemeMode = 'light' | 'dark' | 'system';

export interface LoginPayload {
  account: string;
  password: string;
  remember?: boolean;
}

export interface AuthSession {
  token: string;
  userName: string;
  userId?: string | number;
  roles?: string[];
  permissions?: string[];
  refreshToken?: string;
  expireTime?: number;
}

export interface UserInfo {
  id: string | number;
  account: string;
  userName: string;
  avatar?: string;
  email?: string;
  phone?: string;
  roles: string[];
  permissions: string[];
  department?: string;
  position?: string;
  lastLoginTime?: string;
}

export interface OfflineDataItem {
  id: string;
  type: string;
  data: unknown;
  timestamp: number;
  retryCount: number;
  metadata?: Record<string, unknown>;
}
