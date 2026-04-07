import type { Directive, DirectiveBinding } from 'vue';
import { usePermission } from '@/composables/usePermission';

type PermissionValue = string | string[];

function hasPermissionValue(value: PermissionValue): boolean {
  const { hasPermission, hasAnyPermission } = usePermission();

  if (typeof value === 'string') {
    return hasPermission(value);
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return true;
    }
    return hasAnyPermission(value);
  }

  return false;
}

function hideElement(el: HTMLElement): void {
  if (el.style.display !== 'none') {
    el.dataset.originalDisplay = el.style.display || '';
    el.style.display = 'none';
  }
}

function showElement(el: HTMLElement): void {
  const originalDisplay = el.dataset.originalDisplay;
  if (originalDisplay !== undefined) {
    el.style.display = originalDisplay;
    delete el.dataset.originalDisplay;
  } else {
    el.style.display = '';
  }
}

function updateVisibility(el: HTMLElement, value: PermissionValue): void {
  if (hasPermissionValue(value)) {
    showElement(el);
  } else {
    hideElement(el);
  }
}

export const vPermission: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding<PermissionValue>) {
    updateVisibility(el, binding.value);
  },
  updated(el: HTMLElement, binding: DirectiveBinding<PermissionValue>) {
    if (binding.value !== binding.oldValue) {
      updateVisibility(el, binding.value);
    }
  },
};
