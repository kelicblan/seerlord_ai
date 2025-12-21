<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  MoreHorizontal,
} from 'lucide-vue-next'

export interface Column {
  key: string
  label: string
  slot?: string
  width?: string
}

const props = defineProps<{
  columns: Column[]
  data: any[]
  total: number
  page: number
  pageSize: number
  loading: boolean
  selectable?: boolean
  actions?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:page', page: number): void
  (e: 'update:pageSize', size: number): void
  (e: 'selection-change', selectedIds: number[]): void
  (e: 'edit', item: any): void
  (e: 'delete', item: any): void
}>()

const { t } = useI18n()
const selectedIds = ref<number[]>([])

watch(() => props.page, () => {
  selectedIds.value = []
  emit('selection-change', [])
})

const totalPages = computed(() => Math.ceil(props.total / props.pageSize))

const handleSelectionChange = (selection: any[]) => {
  selectedIds.value = (selection ?? []).map(item => item.id).filter((id: any) => typeof id === 'number')
  emit('selection-change', selectedIds.value)
}

const handleActionCommand = (command: string, row: any) => {
  if (command === 'edit') emit('edit', row)
  if (command === 'delete') emit('delete', row)
}

const handlePageChange = (newPage: number) => {
  if (newPage >= 1 && newPage <= totalPages.value) emit('update:page', newPage)
}

const handlePageSizeChange = (newSize: number) => {
  emit('update:pageSize', newSize)
  emit('update:page', 1)
}
</script>

<template>
  <div class="space-y-2">
    <div class="rounded-md border shadow-sm bg-card">
      <ElTable
        :data="data"
        :border="true"
        style="width: 100%"
        :empty-text="loading ? (t('common.loading') || 'Loading...') : (t('common.no_data') || 'No data')"
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <ElTableColumn v-if="selectable" type="selection" width="48" />

        <ElTableColumn
          v-for="col in columns"
          :key="col.key"
          :prop="col.key"
          :label="col.label"
        >
          <template #default="{ row }">
            <slot
              v-if="col.slot"
              :name="col.slot"
              :row="row"
              :value="row?.[col.key]"
            >
              {{ row?.[col.key] }}
            </slot>
            <template v-else>
              {{ row?.[col.key] }}
            </template>
          </template>
        </ElTableColumn>

        <ElTableColumn v-if="actions" width="60" align="right">
          <template #default="{ row }">
            <ElDropdown trigger="click" @command="(cmd: string) => handleActionCommand(cmd, row)">
              <ElButton text circle size="small">
                <MoreHorizontal class="h-4 w-4" />
                <span class="sr-only">Open menu</span>
              </ElButton>
              <template #dropdown>
                <ElDropdownMenu>
                  <ElDropdownItem command="edit">
                    {{ t('common.edit') || 'Edit' }}
                  </ElDropdownItem>
                  <ElDropdownItem command="delete" class="text-red-600">
                    {{ t('common.delete') || 'Delete' }}
                  </ElDropdownItem>
                </ElDropdownMenu>
              </template>
            </ElDropdown>
          </template>
        </ElTableColumn>
      </ElTable>
    </div>

    <!-- Pagination -->
    <div class="flex items-center justify-between px-2">
      <div class="text-sm text-muted-foreground">
        {{ t('common.selected_rows', { selected: selectedIds.length, total: total }) || `Selected ${selectedIds.length} / Total ${total}` }}
      </div>
      <ElPagination
        background
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </div>
  </div>
</template>
