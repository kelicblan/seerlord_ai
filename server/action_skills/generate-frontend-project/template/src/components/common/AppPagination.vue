<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  total?: number
  page?: number
  pageSize?: number
  pageSizes?: number[]
}

const props = withDefaults(defineProps<Props>(), {
  total: 0,
  page: 1,
  pageSize: 10,
  pageSizes: () => [10, 20, 50, 100],
})

const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [pageSize: number]
  change: [payload: { page: number; pageSize: number }]
}>()

const currentPage = computed({
  get: () => props.page,
  set: (value: number) => {
    emit('update:page', value)
    emit('change', { page: value, pageSize: props.pageSize })
  },
})

const currentPageSize = computed({
  get: () => props.pageSize,
  set: (value: number) => {
    emit('update:pageSize', value)
    emit('change', { page: props.page, pageSize: value })
  },
})

const handleSizeChange = (size: number) => {
  currentPageSize.value = size
  if (props.page > Math.ceil(props.total / size)) {
    currentPage.value = 1
  }
}

const handleCurrentChange = (current: number) => {
  currentPage.value = current
}
</script>

<template>
  <div class="flex flex-col items-center gap-3 md:flex-row md:justify-between">
    <div class="text-sm text-[var(--app-text-secondary)]">
      共 <span class="font-medium text-[var(--app-text)]">{{ total }}</span> 条记录
    </div>

    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="currentPageSize"
      :page-sizes="pageSizes"
      :total="total"
      background
      layout="sizes, prev, pager, next, jumper"
      @size-change="handleSizeChange"
      @current-change="handleCurrentChange"
    />
  </div>
</template>
