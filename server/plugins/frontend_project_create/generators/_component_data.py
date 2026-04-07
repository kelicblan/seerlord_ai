"""业务组件模板数据：包含 Table、FormModal、SearchBar、DeleteConfirm、表单组件的 Vue 模板字符串。"""

TABLE_VUE = """<script setup lang="ts">
import { use{module_title}Store } from '@/stores/{module}'
import { storeToRefs } from 'pinia'
import type {{module_title}Item} from '@/types/{module}'

const store = use{module_title}Store()
const { list, total, loading } = storeToRefs(store)

defineProps<{
  showPagination?: boolean
}>()

const emit = defineEmits<{
  (e: 'view', row: {module_title}Item): void
  (e: 'edit', row: {module_title}Item): void
  (e: 'delete', row: {module_title}Item): void
}>()

function onView(row: {module_title}Item) {
  emit('view', row)
}

function onEdit(row: {module_title}Item) {
  emit('edit', row)
}

function onDelete(row: {module_title}Item) {
  emit('delete', row)
}
</script>

<template>
  <el-table :data="list" v-loading="loading" stripe>
    <el-table-column type="index" label="序号" width="60" />
    <slot />
    <el-table-column label="操作" width="180" fixed="right">
      <template #default="{ row }">
        <el-button link type="primary" @click="onView(row)">查看</el-button>
        <el-button link type="primary" @click="onEdit(row)">编辑</el-button>
        <el-button link type="danger" @click="onDelete(row)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
"""

FORM_MODAL_VUE = """<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { use{module_title}Store } from '@/stores/{module}'
import type {{module_title}Item} from '@/types/{module}'

const props = defineProps<{
  visible: boolean
  initialData?: {module_title}Item | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'success'): void
}>()

const store = use{module_title}Store()

const formData = ref<Record<string, unknown>>({})
const loading = ref(false)

const isEdit = computed(() => !!props.initialData)
const title = computed(() => isEdit.value ? '编辑' : '新增')

watch(() => props.visible, (val) => {
  if (val) {
    formData.value = props.initialData ? { ...props.initialData } : {}
  }
})

function close() {
  emit('update:visible', false)
}

async function submit() {
  loading.value = true
  try {
    if (isEdit.value && props.initialData) {
      await store.update(props.initialData.id, formData.value)
    } else {
      await store.create(formData.value)
    }
    ElMessage.success('保存成功')
    close()
    emit('success')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="600px"
    @update:model-value="close"
  >
    <el-form :model="formData" label-width="100px">
      <slot :formData="formData" />
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>
"""

SEARCH_BAR_VUE = """<script setup lang="ts">
import { ref } from 'vue'
import { ElButton, ElInput } from 'element-plus'

defineProps<{
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'search', keyword: string): void
  (e: 'reset'): void
}>()

const keyword = ref('')

function onSearch() {
  emit('search', keyword.value)
}

function onReset() {
  keyword.value = ''
  emit('reset')
}
</script>

<template>
  <div class="search-bar flex gap-2 mb-4">
    <el-input
      v-model="keyword"
      :placeholder="placeholder || '请输入关键词'"
      clearable
      @keyup.enter="onSearch"
    />
    <el-button type="primary" @click="onSearch">搜索</el-button>
    <el-button @click="onReset">重置</el-button>
    <slot />
  </div>
</template>

<style scoped>
.search-bar {
  align-items: center;
}
</style>
"""

DELETE_CONFIRM_VUE = """<script setup lang="ts">
import { ElMessageBox } from 'element-plus'

defineProps<{
  title?: string
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
}>()

async function onDelete(row: Record<string, unknown>) {
  try {
    await ElMessageBox.confirm(
      '确定要删除该数据吗？此操作不可撤销。',
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    emit('confirm')
  } catch {
  }
}
</script>

<template>
  <slot :onDelete="onDelete" />
</template>
"""

PAGE_FORM_VUE = """<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  visible: boolean
  data?: Record<string, unknown> | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'submit', data: Record<string, unknown>): void
}>()

const formData = ref<Record<string, unknown>>({})

watch(() => props.visible, (val) => {
  if (val) {
    formData.value = props.data ? { ...props.data } : {}
  }
})

function close() {
  emit('update:visible', false)
}

function submit() {
  emit('submit', formData.value)
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    title="{page_name}表单"
    width="600px"
    @update:model-value="close"
  >
    <el-form :model="formData" label-width="100px">
      <el-form-item label="名称">
        <el-input v-model="formData.name" placeholder="请输入名称" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>
"""

COMPONENT_TEMPLATES: dict = {
    "table": TABLE_VUE,
    "form_modal": FORM_MODAL_VUE,
    "search_bar": SEARCH_BAR_VUE,
    "delete_confirm": DELETE_CONFIRM_VUE,
    "page_form": PAGE_FORM_VUE,
}
