import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router';
import type { RouteLocationRaw } from 'vue-router';

export const errorGuard = (
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext
): void => {
  const errorCodes = [500, 502, 503, 504];

  if (to.meta.errorCode && errorCodes.includes(to.meta.errorCode as number)) {
    const route: RouteLocationRaw = {
      path: '/500',
      query: {
        code: String(to.meta.errorCode),
        message: String(to.meta.errorMessage || '服务器错误'),
      },
    };
    next(route);
    return;
  }

  next();
};

export const notFoundGuard = (
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext
): void => {
  if (to.name === 'not-found' || to.path.match(/^\/[^/]+$/)) {
    const isApiRoute = to.path.startsWith('/api/');
    const isStaticRoute = ['/assets', '/public', '/static'].some(
      (prefix) => to.path.startsWith(prefix)
    );

    if (isApiRoute) {
      console.error(`API路由不存在: ${to.path}`);
      return next({
        path: '/api/404',
      });
    }

    if (!isStaticRoute) {
      return next({
        path: '/404',
        query: {
          path: to.path,
        },
      });
    }
  }

  next();
};
