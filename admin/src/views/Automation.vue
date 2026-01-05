<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-2xl font-bold text-gray-800">自动化智能体</h2>
        <p class="text-gray-500 mt-1">管理和调度您的自动化任务</p>
      </div>
      <el-button type="primary" @click="handleCreate">
        <el-icon class="mr-1"><Plus /></el-icon>新建任务
      </el-button>
    </div>

    <el-card shadow="never" class="border-0">
      <el-table :data="tasks" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="任务名称" min-width="150" />
        <el-table-column prop="agent_id" label="应用Agent" min-width="150">
           <template #default="{ row }">
             {{ getAgentName(row.agent_id) }}
           </template>
        </el-table-column>
        <el-table-column label="执行策略" min-width="150">
          <template #default="{ row }">
            <el-tag v-if="row.is_one_time" type="info" effect="plain">一次性</el-tag>
            <el-tag v-else-if="row.cron_expression" type="warning" effect="plain">Cron: {{ row.cron_expression }}</el-tag>
            <el-tag v-else-if="row.interval_seconds" type="success" effect="plain">间隔: {{ row.interval_seconds }}s</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="(val: any) => handleStatusChange(row, val)"
              :loading="row.statusLoading"
            />
          </template>
        </el-table-column>
        <el-table-column prop="last_run_time" label="上次运行" width="180">
           <template #default="{ row }">
             {{ formatDate(row.last_run_time) }}
           </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" @click="handleRun(row)">
              <el-icon class="mr-1"><Play class="w-3 h-3" /></el-icon>测试运行
            </el-button>
            <el-button link type="primary" @click="handleLogs(row)">日志</el-button>
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑任务' : '新建任务'"
      width="600px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" label-position="left">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="给任务起个名字" />
        </el-form-item>
        <el-form-item label="选择Agent" prop="agent_id">
          <el-select v-model="form.agent_id" placeholder="选择要执行的Agent" class="w-full">
            <el-option
              v-for="agent in agentList"
              :key="agent.id"
              :label="agent.name_zh || agent.name"
              :value="agent.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="输入问题" prop="input_prompt">
          <el-input
            v-model="form.input_prompt"
            type="textarea"
            :rows="4"
            placeholder="输入您想问Agent的问题或指令"
          />
        </el-form-item>
        <el-form-item label="执行方式" required>
          <el-radio-group v-model="taskType" @change="handleTypeChange">
            <el-radio label="cron">Cron 表达式</el-radio>
            <el-radio label="interval">间隔时间</el-radio>
            <el-radio label="one_time">一次性</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item
          v-if="taskType === 'cron'"
          label="Cron表达式"
          prop="cron_expression"
          :rules="[{ required: true, message: '请输入Cron表达式', trigger: 'blur' }]"
        >
          <div class="flex gap-2">
            <el-input v-model="form.cron_expression" placeholder="e.g. 0 12 * * *" />
            <el-button type="primary" plain @click="handleOpenCronDialog">
              <el-icon class="mr-1"><Wand class="w-4 h-4" /></el-icon> AI 生成
            </el-button>
          </div>
          <div class="text-xs text-gray-400 mt-1">分 时 日 月 周 (例如: 0 12 * * * 表示每天12点)</div>
        </el-form-item>
        
        <el-form-item
          v-if="taskType === 'interval'"
          label="间隔(秒)"
          prop="interval_seconds"
          :rules="[{ required: true, message: '请输入间隔秒数', trigger: 'blur' }]"
        >
          <el-input-number v-model="form.interval_seconds" :min="10" :step="10" />
        </el-form-item>

        <el-form-item label="是否启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- AI Cron Generation Dialog -->
    <el-dialog
      v-model="cronDialogVisible"
      title="AI 生成 Cron 表达式"
      width="400px"
    >
      <p class="text-gray-500 mb-3 text-sm">请输入自然语言描述，例如："每天早上8点" 或 "每隔2小时"</p>
      <el-input
        v-model="cronPrompt"
        type="textarea"
        :rows="3"
        placeholder="请描述您的定时需求..."
        @keyup.enter.ctrl="handleGenerateCron"
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="cronDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleGenerateCron" :loading="generatingCron">
            生成
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Logs Drawer -->
    <el-drawer v-model="logsVisible" title="执行日志" size="50%">
      <div v-loading="logsLoading">
        <el-empty v-if="logs.length === 0" description="暂无日志" />
        <el-timeline v-else>
          <el-timeline-item
            v-for="log in logs"
            :key="log.id"
            :timestamp="formatDate(log.start_time)"
            :type="getLogType(log.status)"
            :color="getLogColor(log.status)"
          >
            <div class="font-bold text-sm mb-1">{{ log.status }}</div>
            <div v-if="log.output" class="bg-gray-50 p-2 rounded text-xs whitespace-pre-wrap font-mono">{{ log.output }}</div>
            <div v-if="log.error_message" class="text-red-500 text-xs mt-1">{{ log.error_message }}</div>
            <div class="text-gray-400 text-xs mt-1" v-if="log.end_time">耗时: {{ calculateDuration(log.start_time, log.end_time) }}</div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { Wand, Play } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { getTasks, createTask, updateTask, deleteTask, runTask, getTaskLogs, generateCronExpression } from '@/api/automation'
import { getPlugins, type AgentPlugin } from '@/api/agent'
import type { AutomationTask, AutomationLog } from '@/api/automation'

const loading = ref(false)
const tasks = ref<any[]>([]) // Add statusLoading
const agentList = ref<AgentPlugin[]>([])

const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const taskType = ref('cron')

const form = reactive({
  id: 0,
  name: '',
  agent_id: '',
  input_prompt: '',
  cron_expression: '',
  interval_seconds: undefined as number | undefined,
  is_one_time: false,
  is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  agent_id: [{ required: true, message: '请选择Agent', trigger: 'change' }],
  input_prompt: [{ required: true, message: '请输入提示词', trigger: 'blur' }],
}

const logsVisible = ref(false)
const logsLoading = ref(false)
const logs = ref<AutomationLog[]>([])

// AI Cron Generation
const cronDialogVisible = ref(false)
const cronPrompt = ref('')
const generatingCron = ref(false)

const handleOpenCronDialog = () => {
  cronPrompt.value = ''
  cronDialogVisible.value = true
}

const handleGenerateCron = async () => {
  if (!cronPrompt.value) {
    ElMessage.warning('请输入时间描述')
    return
  }
  
  generatingCron.value = true
  try {
    const res = await generateCronExpression(cronPrompt.value)
    form.cron_expression = res.data.cron_expression
    ElMessage.success('Cron表达式生成成功')
    cronDialogVisible.value = false
  } catch (error) {
    console.error(error)
    ElMessage.error('生成失败，请重试')
  } finally {
    generatingCron.value = false
  }
}

onMounted(async () => {
  await fetchAgents()
  await fetchTasks()
})

const fetchAgents = async () => {
  try {
    const res = await getPlugins()
    agentList.value = res.data
  } catch (error) {
    console.error(error)
  }
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await getTasks()
    tasks.value = res.data.map(t => ({ ...t, statusLoading: false }))
  } catch (error) {
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

const getAgentName = (id: string) => {
  const agent = agentList.value.find(a => a.id === id)
  return agent ? (agent.name_zh || agent.name) : id
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

const handleCreate = () => {
  isEdit.value = false
  form.id = 0
  form.name = ''
  form.agent_id = ''
  form.input_prompt = ''
  form.cron_expression = ''
  form.interval_seconds = undefined
  form.is_one_time = false
  form.is_active = true
  taskType.value = 'cron'
  dialogVisible.value = true
}

const handleEdit = (row: AutomationTask) => {
  isEdit.value = true
  Object.assign(form, row)
  
  if (row.is_one_time) {
    taskType.value = 'one_time'
  } else if (row.cron_expression) {
    taskType.value = 'cron'
  } else if (row.interval_seconds) {
    taskType.value = 'interval'
  } else {
    taskType.value = 'cron'
  }
  
  dialogVisible.value = true
}

const handleTypeChange = (val: string | number | boolean | undefined) => {
  if (val === 'one_time') {
    form.is_one_time = true
    form.cron_expression = ''
    form.interval_seconds = undefined
  } else if (val === 'cron') {
    form.is_one_time = false
    form.interval_seconds = undefined
  } else {
    form.is_one_time = false
    form.cron_expression = ''
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        // Clean up data based on type
        if (taskType.value === 'cron') {
           form.interval_seconds = undefined
           form.is_one_time = false
        } else if (taskType.value === 'interval') {
           form.cron_expression = ''
           form.is_one_time = false
        } else {
           form.cron_expression = ''
           form.interval_seconds = undefined
           form.is_one_time = true
        }

        if (isEdit.value) {
          await updateTask(form.id, form)
          ElMessage.success('更新成功')
        } else {
          // Remove id for create
          const { id, ...data } = form
          await createTask(data)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchTasks()
      } catch (error) {
        ElMessage.error('操作失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

const handleDelete = async (row: AutomationTask) => {
  try {
    await ElMessageBox.confirm('确定要删除该任务吗？', '警告', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteTask(row.id)
    ElMessage.success('删除成功')
    fetchTasks()
  } catch (error) {
    // Cancelled
  }
}

const handleStatusChange = async (row: any, val: string | number | boolean): Promise<void> => {
  row.statusLoading = true
  try {
    await updateTask(row.id, { is_active: Boolean(val) })
    ElMessage.success(val ? '任务已启用' : '任务已停止')
  } catch (error) {
    row.is_active = !val // Revert
    ElMessage.error('状态更新失败')
  } finally {
    row.statusLoading = false
  }
}

const handleRun = async (row: AutomationTask) => {
  try {
    await runTask(row.id)
    ElMessage.success('已触发后台运行')
  } catch (error) {
    ElMessage.error('触发失败')
  }
}

const handleLogs = async (row: AutomationTask) => {
  logsVisible.value = true
  logsLoading.value = true
  logs.value = []
  try {
    const res = await getTaskLogs(row.id)
    logs.value = res.data
  } catch (error) {
    ElMessage.error('获取日志失败')
  } finally {
    logsLoading.value = false
  }
}

const getLogType = (status: string) => {
  if (status === 'SUCCESS') return 'success'
  if (status === 'FAILURE') return 'danger'
  return 'primary'
}

const getLogColor = (status: string) => {
  if (status === 'RUNNING') return '#409EFF'
  return ''
}

const calculateDuration = (start: string, end?: string) => {
  if (!end) return '进行中...'
  const diff = new Date(end).getTime() - new Date(start).getTime()
  return `${(diff / 1000).toFixed(2)}s`
}
</script>
