import { computed, ref } from 'vue';

export interface Role {
  id: string;
  name: string;
  code: string;
}

export interface Permission {
  id: string;
  name: string;
  code: string;
  action?: 'create' | 'read' | 'update' | 'delete';
  resource?: string;
}

export interface UsePermissionReturn {
  roles: ReturnType<typeof ref<Role[]>>;
  permissions: ReturnType<typeof ref<Permission[]>>;
  hasPermission: (code: string, action?: Permission['action']) => boolean;
  hasRole: (roleCode: string) => boolean;
  hasAnyPermission: (codes: string[]) => boolean;
  hasAllPermissions: (codes: string[]) => boolean;
  hasAnyRole: (roleCodes: string[]) => boolean;
  setRoles: (roles: Role[]) => void;
  setPermissions: (permissions: Permission[]) => void;
  clearPermissions: () => void;
}

const defaultRoles = ref<Role[]>([]);
const defaultPermissions = ref<Permission[]>([]);

export const usePermission = (
  initialRoles?: Role[],
  initialPermissions?: Permission[]
): UsePermissionReturn => {
  if (initialRoles) {
    defaultRoles.value = initialRoles;
  }

  if (initialPermissions) {
    defaultPermissions.value = initialPermissions;
  }

  const roles = computed(() => defaultRoles.value);
  const permissions = computed(() => defaultPermissions.value);

  const hasPermission = (
    code: string,
    action?: Permission['action']
  ): boolean => {
    if (defaultPermissions.value.length === 0) {
      return false;
    }

    if (action) {
      return defaultPermissions.value.some(
        (p) => p.code === code && p.action === action
      );
    }

    return defaultPermissions.value.some((p) => p.code === code);
  };

  const hasRole = (roleCode: string): boolean => {
    if (defaultRoles.value.length === 0) {
      return false;
    }

    return defaultRoles.value.some((r) => r.code === roleCode);
  };

  const hasAnyPermission = (codes: string[]): boolean => {
    if (codes.length === 0) {
      return true;
    }

    return codes.some((code) => hasPermission(code));
  };

  const hasAllPermissions = (codes: string[]): boolean => {
    if (codes.length === 0) {
      return true;
    }

    return codes.every((code) => hasPermission(code));
  };

  const hasAnyRole = (roleCodes: string[]): boolean => {
    if (roleCodes.length === 0) {
      return true;
    }

    return roleCodes.some((code) => hasRole(code));
  };

  const setRoles = (newRoles: Role[]): void => {
    defaultRoles.value = newRoles;
  };

  const setPermissions = (newPermissions: Permission[]): void => {
    defaultPermissions.value = newPermissions;
  };

  const clearPermissions = (): void => {
    defaultRoles.value = [];
    defaultPermissions.value = [];
  };

  return {
    roles,
    permissions,
    hasPermission,
    hasRole,
    hasAnyPermission,
    hasAllPermissions,
    hasAnyRole,
    setRoles,
    setPermissions,
    clearPermissions,
  };
};
