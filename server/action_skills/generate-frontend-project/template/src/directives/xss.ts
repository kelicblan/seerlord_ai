import type { Directive, DirectiveBinding } from 'vue';
import { sanitizeHtml } from '@/utils/xss';

type XssValue = string | (() => string);

function getXssValue(value: XssValue): string {
  if (typeof value === 'function') {
    return value();
  }
  return value;
}

function sanitizeContent(content: string): string {
  if (!content) {
    return '';
  }
  return sanitizeHtml(content);
}

function updateContent(el: HTMLElement, value: XssValue): void {
  const originalContent = getXssValue(value);
  const sanitizedContent = sanitizeContent(originalContent);

  if (el.innerHTML !== sanitizedContent) {
    el.innerHTML = sanitizedContent;
  }
}

export const vXss: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding<XssValue>) {
    updateContent(el, binding.value);
  },
  updated(el: HTMLElement, binding: DirectiveBinding<XssValue>) {
    if (binding.value !== binding.oldValue) {
      updateContent(el, binding.value);
    }
  },
};
