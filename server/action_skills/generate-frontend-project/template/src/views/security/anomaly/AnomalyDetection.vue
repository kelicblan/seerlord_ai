<script setup lang="ts">
import { ref, reactive } from 'vue'
import {
  ElCard,
  ElTable,
  ElTableColumn,
  ElButton,
  ElTag,
  ElSwitch,
  ElMessage,
  ElMessageBox,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElSelect,
  ElOption,
  ElInputNumber,
  ElAlert,
} from 'element-plus'
import {
  Plus,
  Edit,
  Delete,
  Refresh,
} from '@element-plus/icons-vue'
import {
  Odometer,
  CircleCheck,
  CircleClose,
  Warning,
} from '@element-plus/icons-vue'

interface AnomalyEvent {
  id: string
  type: string
  level: string
  ip: string
  user: string
  description: string
  status: string
  createdAt: string
  handledBy?: string
  handledAt?: string
}

interface DetectionRule {
  id: string
  name: string
  type: string
  threshold: number
  timeWindow: number
  enabled: boolean
  severity: string
  description: string
  lastTriggered?: string
  triggerCount: number
}

const activeTab = ref('events')

const anomalyEvents = ref<AnomalyEvent[]>([
  {
    id: '1',
    type: '暴力破解',
    level: 'high',
    ip: '192.168.1.105',
    user: 'admin',
    description: '连续 10 次登录失败，疑似暴力破解攻击',
    status: 'pending',
    createdAt: '2024-01-20 14:32:15',
  },
  {
    id: '2',
    type: '异常访问',
    level: 'medium',
    ip: '10.0.0.58',
    user: 'user001',
    description: '短时间内访问大量接口，行为异常',
    status: 'handled',
    createdAt: '2024-01-20 13:25:42',
    handledBy: 'admin',
    handledAt: '2024-01-20 14:00:00',
  },
  {
    id: '3',
    type: '权限绕过',
    level: 'critical',
    ip: '172.16.0.23',
    user: 'guest',
    description: '尝试访问管理员接口，权限验证绕过',
    status: 'pending',
    createdAt: '2024-01-20 12:18:33',
  },
  {
    id: '4',
    type: '数据泄露',
    level: 'critical',
    ip: '192.168.1.200',
    user: 'test',
    description: '大量导出用户数据，疑似数据泄露',
    status: 'pending',
    createdAt: '2024-01-20 11:45:20',
  },
  {
    id: '5',
    type: '异常登录',
    level: 'high',
    ip: '203.0.113.42',
    user: 'manager',
    description: '异地登录检测到新设备登录',
    status: 'handled',
    createdAt: '2024-01-20 10:30:15',
    handledBy: 'security',
    handledAt: '2024-01-20 11:00:00',
  },
])

const detectionRules = ref<DetectionRule[]>([
  {
    id: '1',
    name: '暴力破解检测',
    type: 'login_fail',
    threshold: 10,
    timeWindow: 5,
    enabled: true,
    severity: 'high',
    description: '检测连续登录失败次数',
    lastTriggered: '2024-01-20 14:32:15',
    triggerCount: 156,
  },
  {
    id: '2',
    name: '异常访问频率',
    type: 'access_frequency',
    threshold: 100,
    timeWindow: 1,
    enabled: true,
    severity: 'medium',
    description: '检测短时间内接口访问频率',
    lastTriggered: '2024-01-20 13:25:42',
    triggerCount: 89,
  },
  {
    id: '3',
    name: '权限绕过检测',
    type: 'privilege_bypass',
    threshold: 3,
    timeWindow: 10,
    enabled: true,
    severity: 'critical',
    description: '检测权限验证绕过行为',
    lastTriggered: '2024-01-20 12:18:33',
    triggerCount: 23,
  },
  {
    id: '4',
    name: '数据导出限制',
    type: 'data_export',
    threshold: 50,
    timeWindow: 60,
    enabled: true,
    severity: 'high',
    description: '限制单次数据导出数量',
    lastTriggered: '2024-01-20 11:45:20',
    triggerCount: 12,
  },
])

const statistics = reactive({
  total: 156,
  pending: 12,
  critical: 5,
  handled: 139,
})

const ruleForm = reactive({
  name: '',
  type: '',
  threshold: 10,
  timeWindow: 5,
  severity: 'medium',
  description: '',
})

const ruleDialogVisible = ref(false)

const getLevelType = (level: string) => {
  const map: Record<string, 'danger' | 'warning' | 'info'> = {
    critical: 'danger',
    high: 'warning',
    medium: 'warning',
    low: 'info',
  }
  return map[level] || 'info'
}

const getStatusType = (status: string) => {
  return status === 'pending' ? 'warning' : 'success'
}

const getSeverityType = (severity: string) => {
  return severity === 'critical' ? 'danger' : severity === 'high' ? 'warning' : 'info'
}

const handleEvent = async () => {
  try {
    await ElMessageBox.prompt('请输入处理结果', '处理异常事件', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputType: 'textarea',
    })
    ElMessage.success('处理成功')
  } catch {
    // User cancelled
  }
}

const handleIgnore = () => {
  ElMessage.info('已忽略该异常')
}

const toggleRule = async (row: DetectionRule) => {
  row.enabled = !row.enabled
  ElMessage.success(`${row.enabled ? '启用' : '禁用'}规则成功`)
}

const handleAddRule = () => {
  Object.assign(ruleForm, {
    name: '',
    type: '',
    threshold: 10,
    timeWindow: 5,
    severity: 'medium',
    description: '',
  })
  ruleDialogVisible.value = true
}

const handleEditRule = (row: DetectionRule) => {
  Object.assign(ruleForm, row)
  ruleDialogVisible.value = true
}

const handleDeleteRule = async () => {
  try {
    await ElMessageBox.confirm('确定要删除该规则吗？', '提示', {
      type: 'warning',
    })
    ElMessage.success('删除成功')
  } catch {
    // User cancelled
  }
}

const saveRule = () => {
  ElMessage.success('保存成功')
  ruleDialogVisible.value = false
}

const refreshData = () => {
  ElMessage.success('刷新成功')
}
</script>

<template>
  <div class="anomaly-detection">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>异常检测</span>
          <el-button type="primary" @click="refreshData">
            <el-icon class="el-icon--left"><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-row :gutter="20" class="statistics-row">
        <el-col :span="6">
          <el-statistic title="异常总数" :value="statistics.total">
            <template #prefix>
              <el-icon><Odometer /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="待处理" :value="statistics.pending">
            <template #prefix>
              <el-icon><Warning /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="严重" :value="statistics.critical">
            <template #prefix>
              <el-icon><CircleClose /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="已处理" :value="statistics.handled">
            <template #prefix>
              <el-icon><CircleCheck /></el-icon>
            </template>
          </el-statistic>
        </el-col>
      </el-row>

      <el-tabs v-model="activeTab" class="mt-4">
        <el-tab-pane label="异常事件" name="events">
          <el-table :data="anomalyEvents" stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column label="级别" width="100">
              <template #default="{ row }">
                <el-tag :type="getLevelType(row.level)" size="small">
                  {{ row.level }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="ip" label="IP地址" width="140" />
            <el-table-column prop="user" label="用户" width="100" />
            <el-table-column prop="description" label="描述" min-width="200" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="createdAt" label="创建时间" width="160" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'pending'"
                  type="primary"
                  size="small"
                  @click="handleEvent"
                >
                  处理
                </el-button>
                <el-button size="small" @click="handleIgnore">忽略</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="检测规则" name="rules">
          <div class="mb-4">
            <el-button type="primary" @click="handleAddRule">
              <el-icon class="el-icon--left"><Plus /></el-icon>
              添加规则
            </el-button>
          </div>

          <el-table :data="detectionRules" stripe>
            <el-table-column prop="name" label="规则名称" min-width="150" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="threshold" label="阈值" width="80" />
            <el-table-column prop="timeWindow" label="时间窗口(分钟)" width="140" />
            <el-table-column label="严重程度" width="100">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)" size="small">
                  {{ row.severity }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="triggerCount" label="触发次数" width="100" />
            <el-table-column prop="lastTriggered" label="最后触发" width="160" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" @change="toggleRule(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="handleEditRule(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button type="danger" size="small" @click="handleDeleteRule">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="统计概览" name="stats">
          <el-alert
            title="统计概览"
            type="info"
            description="异常检测统计数据将在这里展示"
            :closable="false"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="ruleDialogVisible" title="编辑规则" width="600px">
      <el-form :model="ruleForm" label-width="120px">
        <el-form-item label="规则名称">
          <el-input v-model="ruleForm.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="规则类型">
          <el-select v-model="ruleForm.type" placeholder="请选择规则类型">
            <el-option label="登录失败" value="login_fail" />
            <el-option label="访问频率" value="access_frequency" />
            <el-option label="权限绕过" value="privilege_bypass" />
            <el-option label="数据导出" value="data_export" />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值">
          <el-input-number v-model="ruleForm.threshold" :min="1" />
        </el-form-item>
        <el-form-item label="时间窗口(分钟)">
          <el-input-number v-model="ruleForm.timeWindow" :min="1" />
        </el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="ruleForm.severity" placeholder="请选择严重程度">
            <el-option label="严重" value="critical" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="规则描述">
          <el-input v-model="ruleForm.description" type="textarea" :rows="3" placeholder="请输入规则描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.anomaly-detection {
  padding: 0px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.statistics-row {
  margin-bottom: 20px;
}

.mt-4 {
  margin-top: 20px;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>
