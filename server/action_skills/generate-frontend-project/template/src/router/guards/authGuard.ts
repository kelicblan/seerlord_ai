import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { LOGIN_ROUTE, DEFAULT_ROUTE } from '@/constants/app';

export const authGuard = async (
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext
): Promise<void | NavigationGuardNext> => {
  const authStore = useAuthStore();

  authStore.ensureSession();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({
      path: LOGIN_ROUTE,
      query: {
        redirect: to.fullPath,
      },
    });
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return next({
      path: DEFAULT_ROUTE,
    });
  }

  return next();
};
