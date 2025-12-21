<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api/axios'
import DataTable, { type Column } from '@/components/common/DataTable.vue'

interface User {
  id: number
  username: string
  is_active: boolean
  is_superuser: boolean
}

const users = ref<User[]>([])
const loading = ref(false)
const isDialogOpen = ref(false)
const isEditMode = ref(false)
const currentUserId = ref<number | null>(null)
const selectedUsers = ref<number[]>([])
const searchQuery = ref('')
const activeTab = ref<'all' | 'active' | 'inactive'>('all')

// Pagination state
const currentPage = ref(1)
const pageSize = ref(10)
const totalUsers = ref(0)

// Form state
const form = ref({
  username: '',
  password: '',
  is_active: true,
  is_superuser: false
})

const { t } = useI18n()

const columns = computed<Column[]>(() => [
  { key: 'username', label: t('user_mgmt.header_username') },
  { key: 'is_active', label: t('user_mgmt.header_status'), slot: 'status' },
  { key: 'is_superuser', label: t('user_mgmt.header_role'), slot: 'role' },
  { key: 'id', label: t('user_mgmt.header_id') }
])

// Fetch users
const fetchUsers = async () => {
  loading.value = true
  try {
    const params: any = { page: currentPage.value, size: pageSize.value }
    if (searchQuery.value) {
      params.search = searchQuery.value
    }
    if (activeTab.value === 'active') params.is_active = true
    if (activeTab.value === 'inactive') params.is_active = false
    const response = await api.get('/api/v1/users/', { params })
    // The backend now returns { items: [], total: number, page: number, size: number }
    users.value = response.data.items
    totalUsers.value = response.data.total
  } catch (error) {
    console.error('Failed to fetch users:', error)
    ElMessage.error(t('user_mgmt.toast_error_fetch'))
  } finally {
    loading.value = false
  }
}

watch([currentPage, pageSize], () => {
  fetchUsers()
})

watch(activeTab, () => {
  currentPage.value = 1
  fetchUsers()
})

const handleSearch = () => {
  currentPage.value = 1
  fetchUsers()
}

// Open dialog for create
const openCreateDialog = () => {
  isEditMode.value = false
  currentUserId.value = null
  form.value = {
    username: '',
    password: '',
    is_active: true,
    is_superuser: false
  }
  isDialogOpen.value = true
}

// Open dialog for edit
const openEditDialog = (user: User) => {
  isEditMode.value = true
  currentUserId.value = user.id
  form.value = {
    username: user.username,
    password: '', // Password is not populated for security
    is_active: user.is_active,
    is_superuser: user.is_superuser
  }
  isDialogOpen.value = true
}

// Submit form
const handleSubmit = async () => {
  try {
    if (isEditMode.value && currentUserId.value) {
      // Update
      const payload: any = { ...form.value }
      if (!payload.password) delete payload.password // Don't send empty password if not changed
      
      await api.put(`/api/v1/users/${currentUserId.value}`, payload)
      ElMessage.success(t('user_mgmt.toast_success_update'))
    } else {
      // Create
      if (!form.value.password) {
        ElMessage.error(t('user_mgmt.toast_error_password_required'))
        return
      }
      await api.post('/api/v1/users/', form.value)
      ElMessage.success(t('user_mgmt.toast_success_create'))
    }
    isDialogOpen.value = false
    fetchUsers()
  } catch (error: any) {
    console.error('Failed to save user:', error)
    ElMessage.error(error.response?.data?.detail || t('user_mgmt.toast_error_save'))
  }
}

// Delete user
const deleteUser = async (id: number) => {
  try {
    await ElMessageBox.confirm(
      t('user_mgmt.confirm_delete'),
      t('common.confirm') || 'Confirm',
      {
        confirmButtonText: t('common.delete') || 'Delete',
        cancelButtonText: t('common.cancel') || 'Cancel',
        type: 'warning',
      },
    )
    await api.delete(`/api/v1/users/${id}`)
    ElMessage.success(t('user_mgmt.toast_success_delete'))
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete user:', error)
      ElMessage.error(t('user_mgmt.toast_error_delete'))
    }
  }
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <div class=" h-full w-full">
    <!-- Top Bar -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <ElTabs v-model="activeTab" class="w-full sm:w-auto">
        <ElTabPane name="all" :label="t('user_mgmt.tabs_all')" />
        <ElTabPane name="active" :label="t('user_mgmt.tabs_active')" />
        <ElTabPane name="inactive" :label="t('user_mgmt.tabs_inactive')" />
      </ElTabs>
      
      <div class="flex items-center gap-2">
        <div class="relative w-[250px]">
          <ElInput
            v-model="searchQuery"
            :placeholder="t('user_mgmt.search_placeholder')"
            @keyup.enter="handleSearch"
            clearable
          >
            <template #prefix>
              <Search class="h-4 w-4 text-muted-foreground" />
            </template>
          </ElInput>
        </div>
        <ElButton type="primary" @click="openCreateDialog">
          {{ t('user_mgmt.add_user') }}
        </ElButton>
      </div>
    </div>
<DataTable
          :columns="columns"
          :data="users"
          :total="totalUsers"
          v-model:page="currentPage"
          v-model:pageSize="pageSize"
          :loading="loading"
          :selectable="true"
          :actions="true"
          @selection-change="selectedUsers = $event"
          @edit="openEditDialog"
          @delete="(item) => deleteUser(item.id)"
        >
          <template #status="{ value }">
            <ElTag v-if="value" type="success" effect="light">
              {{ t('user_mgmt.status_active') }}
            </ElTag>
            <ElTag v-else type="danger" effect="light">
              {{ t('user_mgmt.status_inactive') }}
            </ElTag>
          </template>
          <template #role="{ value }">
            <ElTag type="info" effect="plain">
              {{ value ? t('user_mgmt.role_admin') : t('user_mgmt.role_user') }}
            </ElTag>
          </template>
        </DataTable>

    <!-- Dialogs -->
    <ElDialog
      v-model="isDialogOpen"
      :title="isEditMode ? t('user_mgmt.dialog_edit_title') : t('user_mgmt.dialog_create_title')"
      width="520px"
    >
      <div class="text-sm text-muted-foreground mb-4">
        {{ t('user_mgmt.dialog_desc') }}
      </div>

      <ElForm label-width="110px">
        <ElFormItem :label="t('user_mgmt.label_username')">
          <ElInput v-model="form.username" />
        </ElFormItem>
        <ElFormItem :label="t('user_mgmt.label_password')">
          <ElInput
            v-model="form.password"
            type="password"
            show-password
            :placeholder="isEditMode ? t('user_mgmt.placeholder_password_edit') : ''"
          />
        </ElFormItem>
        <ElFormItem :label="t('user_mgmt.label_active')">
          <ElCheckbox v-model="form.is_active">
            {{ t('user_mgmt.label_user_is_active') }}
          </ElCheckbox>
        </ElFormItem>
        <ElFormItem :label="t('user_mgmt.label_superuser')">
          <ElCheckbox v-model="form.is_superuser">
            {{ t('user_mgmt.label_user_is_admin') }}
          </ElCheckbox>
        </ElFormItem>
      </ElForm>

      <template #footer>
        <ElButton @click="isDialogOpen = false">{{ t('common.cancel') || 'Cancel' }}</ElButton>
        <ElButton type="primary" @click="handleSubmit">{{ t('user_mgmt.btn_save') }}</ElButton>
      </template>
    </ElDialog>
  </div>
</template>
