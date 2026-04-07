import type { Directive, DirectiveBinding } from 'vue';
import { ElMessage } from 'element-plus';

type CopyValue = string | (() => string);

async function copyToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return fallbackCopy(text);
    }
  } else {
    return fallbackCopy(text);
  }
}

function fallbackCopy(text: string): boolean {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  textarea.style.top = '-9999px';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();

  try {
    document.execCommand('copy');
    return true;
  } catch {
    return false;
  } finally {
    document.body.removeChild(textarea);
  }
}

function getCopyValue(value: CopyValue): string {
  if (typeof value === 'function') {
    return value();
  }
  return value;
}

async function handleCopy(_el: HTMLElement, value: CopyValue): Promise<void> {
  const text = getCopyValue(value);
  if (!text) {
    ElMessage.warning('复制内容为空');
    return;
  }

  const success = await copyToClipboard(text);
  if (success) {
    ElMessage.success('复制成功');
  } else {
    ElMessage.error('复制失败，请手动复制');
  }
}

export const vCopy: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding<CopyValue>) {
    el.style.cursor = 'pointer';

    const handleClick = () => {
      handleCopy(el, binding.value);
    };

    el.addEventListener('click', handleClick);
    (el as HTMLElement & { _copyHandler?: () => void })._copyHandler = handleClick;
  },
  updated(el: HTMLElement, binding: DirectiveBinding<CopyValue>) {
    const oldHandler = (el as HTMLElement & { _copyHandler?: () => void })._copyHandler;
    if (oldHandler) {
      el.removeEventListener('click', oldHandler);
    }

    const newHandler = () => {
      handleCopy(el, binding.value);
    };

    el.addEventListener('click', newHandler);
    (el as HTMLElement & { _copyHandler?: () => void })._copyHandler = newHandler;
  },
  unmounted(el: HTMLElement) {
    const handler = (el as HTMLElement & { _copyHandler?: () => void })._copyHandler;
    if (handler) {
      el.removeEventListener('click', handler);
      delete (el as HTMLElement & { _copyHandler?: () => void })._copyHandler;
    }
  },
};
