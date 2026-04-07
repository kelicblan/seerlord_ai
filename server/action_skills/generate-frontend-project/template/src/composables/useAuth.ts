import { ref } from 'vue';
import { useAuthStore, type LoginPayload } from '@/stores/auth';
import router from '@/router';
import {
  ACCESS_TOKEN_KEY,
  DEFAULT_ROUTE,
} from '@/constants/app';

export interface UseAuthReturn {
  isAuthenticated: ReturnType<typeof useAuthStore>['isAuthenticated'];
  userName: ReturnType<typeof useAuthStore>['userName'];
  token: ReturnType<typeof useAuthStore>['token'];
  loading: ReturnType<typeof useAuthStore>['loading'];
  login: (payload: LoginPayload) => Promise<boolean>;
  logout: () => Promise<void>;
  ensureSession: () => void;
  redirectAfterLogin: (redirect?: string | null) => Promise<void>;
  checkAuth: () => boolean;
}

export const useAuth = (): UseAuthReturn => {
  const authStore = useAuthStore();

  const redirectUrl = ref<string | null>(null);

  const login = async (payload: LoginPayload): Promise<boolean> => {
    try {
      await authStore.login(payload);
      return true;
    } catch (error) {
      console.error('登录失败:', error);
      return false;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await authStore.logout();
      redirectUrl.value = null;
    } catch (error) {
      console.error('登出失败:', error);
      authStore.clearSession();
    }
  };

  const ensureSession = (): void => {
    authStore.ensureSession();
  };

  const redirectAfterLogin = async (redirect?: string | null): Promise<void> => {
    const targetUrl = redirect || redirectUrl.value || DEFAULT_ROUTE;
    await router.replace(targetUrl);
    redirectUrl.value = null;
  };

  const checkAuth = (): boolean => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    return Boolean(token);
  };

  return {
    isAuthenticated: authStore.isAuthenticated,
    userName: authStore.userName,
    token: authStore.token,
    loading: authStore.loading,
    login,
    logout,
    ensureSession,
    redirectAfterLogin,
    checkAuth,
  };
};
