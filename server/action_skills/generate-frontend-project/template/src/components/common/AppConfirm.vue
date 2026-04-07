<script setup lang="ts">
import { ElMessageBox } from 'element-plus'

type ConfirmType = 'warning' | 'danger' | 'info'

interface ConfirmOptions {
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  type?: ConfirmType
  showClose?: boolean
  closeOnClickModal?: boolean
  closeOnPressEscape?: boolean
}

interface Props {
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  type?: ConfirmType
}

const props = withDefaults(defineProps<Props>(), {
  title: '提示',
  message: '确定要执行此操作吗？',
  confirmText: '确定',
  cancelText: '取消',
  type: 'warning',
})

const typeButtonMap: Record<ConfirmType, 'warning' | 'info'> = {
  warning: 'warning',
  danger: 'warning',
  info: 'info',
}

const show = async (options: ConfirmOptions = {}): Promise<string> => {
  const mergedOptions = { ...props, ...options }

  await ElMessageBox.confirm(mergedOptions.message || props.message, mergedOptions.title || props.title, {
    confirmButtonText: mergedOptions.confirmText || props.confirmText,
    cancelButtonText: mergedOptions.cancelText || props.cancelText,
    type: typeButtonMap[mergedOptions.type || props.type],
    showClose: options.showClose ?? false,
    closeOnClickModal: options.closeOnClickModal ?? false,
    closeOnPressEscape: options.closeOnPressEscape ?? false,
  })
  return 'confirm'
}

defineExpose({
  show,
})
</script>

<template>
  <slot />
</template>
