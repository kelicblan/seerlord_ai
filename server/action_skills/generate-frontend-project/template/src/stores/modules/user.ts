import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import type { UserInfo } from '../types';

export const useUserStore = defineStore(
  'user',
  () => {
    const userInfo = ref<UserInfo | null>(null);
    const permissions = ref<string[]>([]);
    const roles = ref<string[]>([]);

    const isLoggedIn = computed(() => Boolean(userInfo.value));

    const setUser = (info: UserInfo) => {
      userInfo.value = info;
      permissions.value = info.permissions || [];
      roles.value = info.roles || [];
    };

    const clearUser = () => {
      userInfo.value = null;
      permissions.value = [];
      roles.value = [];
    };

    const updateUserInfo = (updates: Partial<UserInfo>) => {
      if (userInfo.value) {
        userInfo.value = {
          ...userInfo.value,
          ...updates,
        };
      }
    };

    const setPermissions = (perms: string[]) => {
      permissions.value = perms;
    };

    const setRoles = (userRoles: string[]) => {
      roles.value = userRoles;
    };

    const hasPermission = (permission: string): boolean => {
      return permissions.value.includes(permission);
    };

    const hasRole = (role: string): boolean => {
      return roles.value.includes(role);
    };

    const hasAnyPermission = (permList: string[]): boolean => {
      return permList.some(perm => permissions.value.includes(perm));
    };

    const hasAllPermissions = (permList: string[]): boolean => {
      return permList.every(perm => permissions.value.includes(perm));
    };

    return {
      userInfo,
      permissions,
      roles,
      isLoggedIn,
      setUser,
      clearUser,
      updateUserInfo,
      setPermissions,
      setRoles,
      hasPermission,
      hasRole,
      hasAnyPermission,
      hasAllPermissions,
    };
  },
  {
    persist: {
      key: 'user-info',
      pick: ['userInfo', 'permissions', 'roles'],
    },
  },
);
