import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import { loginApi } from '@/api/modules/auth';
import type { LoginPayload, AuthSession } from '../types';
import { useUserStore } from './user';
import router from '@/router';
import {
  ACCESS_TOKEN_KEY,
  DEFAULT_ROUTE,
  LOGIN_ROUTE,
  USER_NAME_KEY,
} from '@/constants/app';

export const useAuthStore = defineStore(
  'auth',
  () => {
    const token = ref('');
    const userName = ref('');
    const loading = ref(false);
    const refreshToken = ref('');
    const tokenExpireTime = ref<number | null>(null);
    const lastActivityTime = ref<number | null>(null);

    const isAuthenticated = computed(() => Boolean(token.value));

    const setSession = (session: AuthSession) => {
      token.value = session.token;
      userName.value = session.userName;
      refreshToken.value = session.refreshToken || '';
      tokenExpireTime.value = session.expireTime || null;

      localStorage.setItem(ACCESS_TOKEN_KEY, session.token);
      localStorage.setItem(USER_NAME_KEY, session.userName);

      if (session.refreshToken) {
        localStorage.setItem('refresh-token', session.refreshToken);
      }

      lastActivityTime.value = Date.now();
    };

    const clearSession = () => {
      token.value = '';
      userName.value = '';
      refreshToken.value = '';
      tokenExpireTime.value = null;
      lastActivityTime.value = null;

      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(USER_NAME_KEY);
      localStorage.removeItem('refresh-token');

      const userStore = useUserStore();
      userStore.clearUser();
    };

    const setToken = (newToken: string) => {
      token.value = newToken;
      localStorage.setItem(ACCESS_TOKEN_KEY, newToken);
      lastActivityTime.value = Date.now();
    };

    const login = async (payload: LoginPayload) => {
      loading.value = true;

      try {
        const session = await loginApi(payload);
        setSession(session);

        const userStore = useUserStore();
        userStore.setUser({
          id: 1,
          account: payload.account,
          userName: session.userName,
          roles: [],
          permissions: [],
        });

        return session;
      } catch (error) {
        console.error('登录失败', error);
        throw error;
      } finally {
        loading.value = false;
      }
    };

    const logout = async () => {
      clearSession();

      if (router.currentRoute.value.path !== LOGIN_ROUTE) {
        await router.replace(LOGIN_ROUTE);
      }
    };

    const refreshTokenHandler = async () => {
      if (!refreshToken.value) {
        throw new Error('No refresh token available');
      }

      try {
        loading.value = true;
        const response = await fetch('/api/auth/refresh', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            refreshToken: refreshToken.value,
          }),
        });

        if (!response.ok) {
          throw new Error('Token refresh failed');
        }

        const data = await response.json();
        setToken(data.token);
        return data.token;
      } catch (error) {
        console.error('Token refresh failed', error);
        await logout();
        throw error;
      } finally {
        loading.value = false;
      }
    };

    const refreshTokenAction = async () => {
      try {
        await refreshTokenHandler();
      } catch (error) {
        console.error('Auto token refresh failed', error);
      }
    };

    const ensureSession = () => {
      if (token.value) {
        localStorage.setItem(ACCESS_TOKEN_KEY, token.value);
      }

      if (userName.value) {
        localStorage.setItem(USER_NAME_KEY, userName.value);
      }

      if (token.value && !userName.value) {
        userName.value = localStorage.getItem(USER_NAME_KEY) || '系统管理员';
      }

      if (token.value) {
        lastActivityTime.value = Date.now();
      }
    };

    const redirectAfterLogin = async (redirect?: string | null) => {
      await router.replace(redirect || DEFAULT_ROUTE);
    };

    const isTokenExpired = (): boolean => {
      if (!tokenExpireTime.value) return false;
      return Date.now() > tokenExpireTime.value;
    };

    const getTimeUntilExpiry = (): number | null => {
      if (!tokenExpireTime.value) return null;
      return tokenExpireTime.value - Date.now();
    };

    return {
      token,
      userName,
      loading,
      refreshToken,
      tokenExpireTime,
      lastActivityTime,
      isAuthenticated,
      login,
      logout,
      setToken,
      clearSession,
      ensureSession,
      redirectAfterLogin,
      refreshTokenAction,
      isTokenExpired,
      getTimeUntilExpiry,
    };
  },
  {
    persist: {
      key: 'auth-session',
      pick: ['token', 'userName', 'refreshToken', 'tokenExpireTime'],
    },
  },
);
