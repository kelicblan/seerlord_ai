<template>
  <div class="system-init-container">
    <el-card shadow="never">
      <template #header>
        <span>系统初始化</span>
      </template>

      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="环境检测" />
        <el-step title="基础配置" />
        <el-step title="数据库配置" />
        <el-step title="管理员设置" />
        <el-step title="完成安装" />
      </el-steps>

      <div class="step-content">
        <div v-show="currentStep === 0" class="step-panel">
          <el-alert
            title="环境检测"
            type="info"
            description="请确保服务器环境满足以下要求"
            :closable="false"
            show-icon
          />

          <el-table :data="envCheckItems" class="check-table" size="small">
            <el-table-column prop="name" label="检测项" min-width="200" />
            <el-table-column prop="required" label="要求" width="150" />
            <el-table-column prop="current" label="当前" width="150" />
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
                  {{ row.passed ? '通过' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-show="currentStep === 1" class="step-panel">
          <el-form :model="basicConfig" label-width="120px" class="init-form">
            <el-form-item label="系统名称">
              <el-input v-model="basicConfig.systemName" placeholder="请输入系统名称" />
            </el-form-item>
            <el-form-item label="系统描述">
              <el-input v-model="basicConfig.description" type="textarea" :rows="3" placeholder="请输入系统描述" />
            </el-form-item>
            <el-form-item label="系统URL">
              <el-input v-model="basicConfig.baseUrl" placeholder="请输入系统访问URL" />
            </el-form-item>
            <el-form-item label="系统时区">
              <el-select v-model="basicConfig.timezone" placeholder="请选择时区">
                <el-option label="Asia/Shanghai (UTC+8)" value="Asia/Shanghai" />
                <el-option label="America/New_York (UTC-5)" value="America/New_York" />
                <el-option label="Europe/London (UTC+0)" value="Europe/London" />
              </el-select>
            </el-form-item>
            <el-form-item label="系统语言">
              <el-select v-model="basicConfig.language" placeholder="请选择语言">
                <el-option label="简体中文" value="zh-CN" />
                <el-option label="English" value="en-US" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>

        <div v-show="currentStep === 2" class="step-panel">
          <el-form :model="dbConfig" label-width="120px" class="init-form">
            <el-form-item label="数据库类型">
              <el-select v-model="dbConfig.type" placeholder="请选择数据库类型">
                <el-option label="MySQL" value="mysql" />
                <el-option label="PostgreSQL" value="postgresql" />
                <el-option label="SQL Server" value="sqlserver" />
              </el-select>
            </el-form-item>
            <el-form-item label="主机地址">
              <el-input v-model="dbConfig.host" placeholder="请输入数据库主机地址" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input-number v-model="dbConfig.port" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="数据库名">
              <el-input v-model="dbConfig.database" placeholder="请输入数据库名称" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="dbConfig.username" placeholder="请输入数据库用户名" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="dbConfig.password" type="password" show-password placeholder="请输入数据库密码" />
            </el-form-item>
            <el-form-item label="测试连接">
              <el-button @click="handleTestDb">测试连接</el-button>
            </el-form-item>
          </el-form>
        </div>

        <div v-show="currentStep === 3" class="step-panel">
          <el-form ref="adminFormRef" :model="adminConfig" :rules="adminRules" label-width="120px" class="init-form">
            <el-form-item label="管理员账号">
              <el-input v-model="adminConfig.username" placeholder="请输入管理员账号" />
            </el-form-item>
            <el-form-item label="管理员密码" prop="password">
              <el-input v-model="adminConfig.password" type="password" show-password placeholder="请输入管理员密码" />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input v-model="adminConfig.confirmPassword" type="password" show-password placeholder="请确认密码" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="adminConfig.email" placeholder="请输入管理员邮箱" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="adminConfig.phone" placeholder="请输入管理员手机号" />
            </el-form-item>
          </el-form>
        </div>

        <div v-show="currentStep === 4" class="step-panel">
          <el-result
            icon="success"
            title="安装完成"
            sub-title="系统已成功初始化，现在可以开始使用了"
          >
            <template #extra>
              <el-button type="primary" @click="handleFinish">进入系统</el-button>
            </template>
          </el-result>
        </div>
      </div>

      <div class="step-actions">
        <el-button v-if="currentStep > 0 && currentStep < 4" @click="handlePrev">上一步</el-button>
        <el-button v-if="currentStep < 3" type="primary" @click="handleNext">下一步</el-button>
        <el-button v-if="currentStep === 3" type="primary" @click="handleInstall">开始安装</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const currentStep = ref(0)

const envCheckItems = ref([
  { name: 'PHP版本', required: '>= 7.4', current: '8.1.0', passed: true },
  { name: 'MySQL版本', required: '>= 5.7', current: '8.0.25', passed: true },
  { name: 'Redis扩展', required: '已安装', current: '已安装', passed: true },
  { name: '上传大小限制', required: '>= 2M', current: '10M', passed: true },
  { name: '磁盘空间', required: '>= 500M', current: '100G', passed: true }
])

const basicConfig = reactive({
  systemName: '',
  description: '',
  baseUrl: '',
  timezone: 'Asia/Shanghai',
  language: 'zh-CN'
})

const dbConfig = reactive({
  type: 'mysql',
  host: 'localhost',
  port: 3306,
  database: '',
  username: '',
  password: ''
})

const adminConfig = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
  phone: ''
})

const adminFormRef = ref<FormInstance>()

const validateConfirmPassword = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (value !== adminConfig.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const adminRules: FormRules = {
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleTestDb = () => {
  ElMessage.info('正在测试数据库连接...')
}

const handlePrev = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const handleNext = () => {
  if (currentStep.value < 4) {
    currentStep.value++
  }
}

const handleInstall = async () => {
  try {
    await adminFormRef.value?.validate()
    ElMessage.success('安装成功！')
    currentStep.value = 4
  } catch {
    ElMessage.error('请检查表单填写是否正确')
  }
}

const handleFinish = () => {
  ElMessage.success('即将进入系统...')
}
</script>

<style scoped>
.system-init-container {
  padding: 0px;
}

.step-content {
  margin-top: 30px;
  min-height: 400px;
}

.step-panel {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.init-form {
  max-width: 600px;
  margin: 0 auto;
}

.check-table {
  margin-top: 20px;
}

.step-actions {
  margin-top: 30px;
  text-align: center;
  display: flex;
  justify-content: center;
  gap: 10px;
}
</style>
