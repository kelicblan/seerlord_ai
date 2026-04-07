import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

export const permissionGuard = async (
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext
): Promise<void | NavigationGuardNext> => {
  const { permissions } = to.meta
  const authStore = useAuthStore()

  if (authStore.isAdmin) {
    return next()
  }

  if (!permissions || permissions.length === 0) {
    return next()
  }

  const hasRequiredPermission = permissions.some(
    (permission: string) => authStore.permissions.includes(permission)
  )

  if (!hasRequiredPermission) {
    console.warn(`权限不足: 路由 ${to.path} 需要权限 [${(permissions as string[]).join(', ')}]`)

    return next({
      path: '/403',
      query: {
        message: '您没有访问该页面的权限',
        backUrl: to.fullPath,
      },
    })
  }

  return next()
}
