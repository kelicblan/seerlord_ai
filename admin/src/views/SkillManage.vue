<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Plus, Connection, Timer } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAgent } from '@/composables/useAgent'
import { useI18n } from 'vue-i18n'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import * as SkillApi from '@/api/skills'
import type { Skill, SkillLevel } from '@/api/skills'

const { t } = useI18n()

const { plugins, fetchPlugins } = useAgent()

// State
const activeCategory = ref<string>('all')
const searchQuery = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const historyDialogVisible = ref(false)
const currentSkillHistory = ref<any[]>([])
const currentSkillName = ref('')
const loading = ref(false)

const formData = ref<Omit<Skill, 'id' | 'version'>>({
  name: '',
  description: '',
  category: 'fta_analyst',
  level: 1,
  parentId: undefined,
  content: '',
  tags: []
})

// Real Data from Backend
const skills = ref<Skill[]>([])

const fetchSkills = async () => {
  loading.value = true
  try {
    const res = await SkillApi.getSkills(activeCategory.value === 'all' ? undefined : activeCategory.value)
    skills.value = res.data
  } catch (e) {
    console.error(e)
    ElMessage.error(t('skill_mgmt.toast_fetch_failed'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchPlugins()
  fetchSkills()
})

watch(activeCategory, () => {
  fetchSkills()
})

// Monaco Editor 配置项
const MONACO_OPTIONS = {
  minimap: { enabled: false },
  automaticLayout: true,
  formatOnType: true,
  formatOnPaste: true,
  scrollBeyondLastLine: false,
  fontSize: 14,
  tabSize: 2,
  wordWrap: 'on' as const
}

// Dynamic Categories from Application Agents
const categories = computed(() => {
  return plugins.value
    .filter(p => !p.type || p.type === 'application')
    .map(p => ({
      label: p.name_zh || p.name,
      value: p.id
    }))
})

// 技能等级定义
const levelOptions = computed(() => [
  { label: 'L1 (具体)', value: 1 as SkillLevel, type: 'info' as const, desc: '具体的执行技能' },
  { label: 'L2 (领域)', value: 2 as SkillLevel, type: 'success' as const, desc: '领域通用的模式' },
  { label: 'L3 (元)', value: 3 as SkillLevel, type: 'warning' as const, desc: '底层的元认知/方法论' },
])

// Computed


// Computed

/**
 * 获取可用的父级技能选项
 * 规则:
 * - L1 的父级必须是 L2
 * - L2 的父级必须是 L3
 * - L3 没有父级
 */
const parentCandidates = computed(() => {
  const currentLevel = formData.value.level
  if (currentLevel === 3) return []
  
  const targetParentLevel = (currentLevel + 1) as SkillLevel
  return skills.value.filter(s => s.level === targetParentLevel)
})

const filteredSkills = computed(() => {
  let result = skills.value || [] // 确保不为 undefined

  // We rely on backend filtering for category, but search is local for now
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(s =>
      s.name.toLowerCase().includes(query) ||
      s.description.toLowerCase().includes(query)
    )
  }

  return result
})

// Methods
const getLevelLabel = (level: SkillLevel) => levelOptions.value.find(l => l.value === level)?.label || level
const getLevelType = (level: SkillLevel) => levelOptions.value.find(l => l.value === level)?.type || 'info'
const getCategoryLabel = (value: string) => {
  const cat = categories.value.find(c => c.value === value)
  return cat ? cat.label : value
}

/**
 * 获取技能名称
 * @param id 技能ID
 */
const getSkillName = (id?: string) => {
  if (!id) return ''
  return skills.value.find(s => s.id === id)?.name || id
}

const handleAdd = () => {
  isEdit.value = false
  formData.value = {
    name: '',
    description: '',
    category: 'fta_analyst',
    level: 1,
    parentId: undefined,
    content: '',
    tags: []
  }
  dialogVisible.value = true
}

const handleEdit = (row: Skill) => {
  isEdit.value = true
  // 深拷贝以避免直接修改表格数据
  formData.value = JSON.parse(JSON.stringify(row))
  dialogVisible.value = true
}

const handleDelete = (row: Skill) => {
  ElMessageBox.confirm(
    t('skill_mgmt.confirm_delete_msg', { name: row.name }),
    t('skill_mgmt.confirm_delete_title'),
    {
      confirmButtonText: t('skill_mgmt.btn_delete'),
      cancelButtonText: t('skill_mgmt.btn_cancel'),
      type: 'warning',
    }
  ).then(async () => {
    try {
      await SkillApi.deleteSkill(row.id)
      ElMessage.success(t('skill_mgmt.toast_deleted'))
      fetchSkills()
    } catch (e) {
      console.error(e)
      ElMessage.error(t('skill_mgmt.toast_delete_failed'))
    }
  })
}

const handleSubmit = async () => {
  if (!formData.value.name) {
    ElMessage.warning(t('skill_mgmt.toast_name_required'))
    return
  }

  // 校验父级选择
  if (formData.value.level !== 3 && !formData.value.parentId) {
     // 只是警告，允许无父级的顶层孤儿节点
  }

  try {
    if (isEdit.value) {
      // @ts-ignore
      await SkillApi.updateSkill((formData.value).id, formData.value)
      ElMessage.success(t('skill_mgmt.toast_updated'))
    } else {
      await SkillApi.createSkill(formData.value)
      ElMessage.success(t('skill_mgmt.toast_created'))
    }
    dialogVisible.value = false
    fetchSkills()
  } catch (e) {
    console.error(e)
    ElMessage.error(isEdit.value ? t('skill_mgmt.toast_update_failed') : t('skill_mgmt.toast_create_failed'))
  }
}

const handleHistory = async (row: Skill) => {
  currentSkillName.value = row.name
  historyDialogVisible.value = true
  currentSkillHistory.value = [] // Reset
  try {
    const res = await SkillApi.getSkillHistory(row.id)
    currentSkillHistory.value = res.data.map(item => ({
      ...item,
      showContent: false,
      snapshot_content: item.snapshot_content || '暂无内容快照' // Ensure field exists
    }))
  } catch (e) {
    console.error('Failed to fetch history', e)
    ElMessage.error(t('skill_mgmt.toast_history_failed'))
  }
}

const toggleDiff = (activity: any) => {
  activity.showContent = !activity.showContent
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex justify-between items-center">
      <h2 class="text-2xl font-bold tracking-tight">{{ t('skill_mgmt.title') }}</h2>
      <ElButton type="primary" @click="handleAdd">
        <el-icon class="mr-2">
          <Plus />
        </el-icon>
        {{ t('skill_mgmt.add_skill') }}
      </ElButton>
    </div>

    <!-- 系统设计说明面板 -->
    <ElAlert :title="t('skill_mgmt.alert_core_design')" type="info" :closable="false" show-icon>
      <template #default>
        <div class="text-xs space-y-1 mt-1">
          <p><strong>{{ t('skill_mgmt.design_p1') }}</strong></p>
          <p><strong>{{ t('skill_mgmt.design_p2') }}</strong></p>
          <p><strong>{{ t('skill_mgmt.design_p3') }}</strong></p>
        </div>
      </template>
    </ElAlert>

    <ElCard shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <ElTabs v-model="activeCategory" class="w-full">
            <ElTabPane :label="t('skill_mgmt.tabs_all')" name="all" />
            <ElTabPane v-for="cat in categories" :key="cat.value" :label="cat.label" :name="cat.value" />
          </ElTabs>
          <div class="w-64 ml-4">
            <ElInput v-model="searchQuery" :placeholder="t('skill_mgmt.search_placeholder')" clearable />
          </div>
        </div>
      </template>

      <ElTable :data="filteredSkills" style="width: 100%" row-key="id" default-expand-all>
        <ElTableColumn prop="name" :label="t('skill_mgmt.header_name')" min-width="150">
          <template #default="{ row }">
            <div class="font-medium flex items-center">
              {{ row.name }}
              <el-tag v-if="row.parentId" size="small" type="info" class="ml-2" effect="plain">
                <el-icon><Connection /></el-icon>
              </el-tag>
            </div>
          </template>
        </ElTableColumn>

        <ElTableColumn prop="category" :label="t('skill_mgmt.header_category')" width="120">
          <template #default="{ row }">
            <ElTag size="small" effect="plain">{{ getCategoryLabel(row.category) }}</ElTag>
          </template>
        </ElTableColumn>

        <ElTableColumn prop="level" :label="t('skill_mgmt.header_level')" width="140">
          <template #default="{ row }">
            <ElTag :type="getLevelType(row.level)" effect="dark">
              {{ getLevelLabel(row.level) }}
            </ElTag>
          </template>
        </ElTableColumn>

        <ElTableColumn :label="t('skill_mgmt.col_parent')" min-width="120">
           <template #default="{ row }">
             <span v-if="row.parentId" class="text-gray-500 text-sm">
               {{ getSkillName(row.parentId) }}
             </span>
             <span v-else class="text-gray-300 text-xs">-</span>
           </template>
        </ElTableColumn>

        <ElTableColumn prop="description" :label="t('skill_mgmt.header_desc')" min-width="200" show-overflow-tooltip />

        <ElTableColumn :label="t('skill_mgmt.header_actions')" width="170" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" size="small" @click="handleEdit(row)">
              {{ t('skill_mgmt.btn_edit') }}
            </ElButton>
            <ElButton link type="danger" size="small" @click="handleDelete(row)">
              {{ t('skill_mgmt.btn_delete') }}
            </ElButton>
            <ElButton link type="warning" size="small" @click="handleHistory(row)">
              {{ t('skill_mgmt.btn_history') }}
            </ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>

    <!-- History Dialog -->
    <ElDialog v-model="historyDialogVisible" :title="`${t('skill_mgmt.dialog_history_title')} - ${currentSkillName}`" width="900px">
      <div v-if="currentSkillHistory.length === 0" class="text-center py-8 text-gray-400">
        {{ t('skill_mgmt.history_none') }}
      </div>
      <ElTimeline v-else>
        <ElTimelineItem
          v-for="(activity, index) in currentSkillHistory"
          :key="index"
          :timestamp="new Date(activity.timestamp).toLocaleString()"
          placement="top"
          :type="index === 0 ? 'primary' : undefined"
        >
          <ElCard class="mb-2" shadow="hover">
            <template #header>
               <div class="flex justify-between items-center">
                  <div class="flex items-center gap-2">
                     <span class="font-bold text-sm">{{ activity.agent_id }}</span>
                     <ElTag size="small">v{{ activity.version }}</ElTag>
                  </div>
                  <ElButton link type="primary" size="small" @click="toggleDiff(activity)">
                    {{ activity.showContent ? '收起内容' : '查看内容' }}
                  </ElButton>
               </div>
            </template>
            <div class="text-sm font-medium mb-2">{{ activity.change_description }}</div>
            
            <!-- Snapshot Content Display -->
            <div v-if="activity.showContent" class="mt-2 border-t pt-2">
                <div class="text-xs text-gray-500 mb-1">历史快照内容:</div>
                <div class="bg-gray-50 p-3 rounded text-xs font-mono whitespace-pre-wrap max-h-[300px] overflow-y-auto border">
                  {{ activity.snapshot_content }}
                </div>
            </div>
            
            <div v-if="activity.diff" class="mt-2 text-xs bg-gray-50 p-2 rounded text-gray-500 font-mono">
              {{ activity.diff }}
            </div>
          </ElCard>
        </ElTimelineItem>
      </ElTimeline>
    </ElDialog>

    <!-- Add/Edit Dialog -->
    <ElDialog v-model="dialogVisible" :title="isEdit ? t('skill_mgmt.dialog_edit_title') : t('skill_mgmt.dialog_add_title')" width="1100px" top="5vh">
      <ElForm :model="formData" label-position="top">
        <div class="flex flex-col lg:flex-row gap-6">
          <!-- 左侧：基础信息 -->
          <div class="flex-1 space-y-1">
            <ElFormItem :label="t('skill_mgmt.form_name')" required>
              <ElInput v-model="formData.name" :placeholder="t('skill_mgmt.form_name_placeholder')" />
            </ElFormItem>

            <ElFormItem :label="t('skill_mgmt.form_category')" required>
              <ElSelect v-model="formData.category" class="w-full">
                <ElOption
                  v-for="cat in categories"
                  :key="cat.value"
                  :label="cat.label"
                  :value="cat.value"
                />
              </ElSelect>
            </ElFormItem>

            <div class="grid grid-cols-2 gap-4">
              <ElFormItem :label="t('skill_mgmt.form_level')" required>
                    <ElSelect v-model="formData.level" class="w-full" @change="formData.parentId = undefined">
                      <ElOption v-for="lvl in levelOptions" :key="lvl.value" :label="lvl.label" :value="lvl.value">
                        <span class="float-left">{{ lvl.label }}</span>
                      </ElOption>
                    </ElSelect>
              </ElFormItem>

              <ElFormItem :label="t('skill_mgmt.form_parent')" v-if="formData.level !== 3">
                    <ElSelect v-model="formData.parentId" class="w-full" :placeholder="t('skill_mgmt.form_parent_placeholder')" clearable>
                      <ElOption v-for="p in parentCandidates" :key="p.id" :label="p.name" :value="p.id">
                        <span class="float-left">{{ p.name }}</span>
                        <span class="float-right text-gray-400 text-xs">L{{ p.level }}</span>
                      </ElOption>
                    </ElSelect>
              </ElFormItem>
            </div>

            <ElFormItem :label="t('skill_mgmt.form_desc')">
              <ElInput v-model="formData.description" type="textarea" :rows="8"
                :placeholder="t('skill_mgmt.form_desc_placeholder')" />
            </ElFormItem>
          </div>

          <!-- 右侧：技能内容编辑 (Monaco Editor) -->
          <div class="flex-1 flex flex-col">
            <ElFormItem :label="t('skill_mgmt.form_content')" required class="flex-1 flex flex-col h-full">
              <div class="w-full border rounded-md overflow-hidden border-gray-300 h-[500px]">
                <VueMonacoEditor
                  v-model:value="formData.content"
                  language="markdown"
                  theme="vs-dark"
                  :options="MONACO_OPTIONS"
                  height="100%"
                  class="w-full h-full"
                />
              </div>
            </ElFormItem>
          </div>
        </div>
      </ElForm>

      <template #footer>
        <span class="dialog-footer">
          <ElButton @click="dialogVisible = false">{{ t('skill_mgmt.btn_cancel') }}</ElButton>
          <ElButton type="primary" @click="handleSubmit">
            {{ isEdit ? t('skill_mgmt.btn_update') : t('skill_mgmt.btn_create') }}
          </ElButton>
        </span>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
:deep(.el-tabs__header) {
  margin-bottom: 0;
}

:deep(.el-card__header) {
  padding-bottom: 0;
}
</style>
