<script setup lang="ts">
import { ref, reactive } from 'vue'
import {
  ElCard,
  ElForm,
  ElFormItem,
  ElSelect,
  ElOption,
  ElSwitch,
  ElButton,
  ElMessage,
  ElAlert,
  ElDivider,
} from 'element-plus'
import {
  Key,
  Refresh,
} from '@element-plus/icons-vue'

interface EncryptionConfig {
  algorithm: string
  keyLength: number
  enableAes: boolean
  enableRsa: boolean
  enableSm2: boolean
  rsaKeySize: number
  sm2Curve: string
  rotationInterval: number
  enableKeyBackup: boolean
  enableKeyAudit: boolean
}

const configForm = reactive<EncryptionConfig>({
  algorithm: 'AES-256-GCM',
  keyLength: 256,
  enableAes: true,
  enableRsa: true,
  enableSm2: false,
  rsaKeySize: 2048,
  sm2Curve: 'sm2p256v1',
  rotationInterval: 90,
  enableKeyBackup: true,
  enableKeyAudit: true,
})

const isLoading = ref(false)
const hasUnsavedChanges = ref(false)

const algorithmOptions = [
  { value: 'AES-128-CBC', label: 'AES-128-CBC', keyLength: 128 },
  { value: 'AES-128-GCM', label: 'AES-128-GCM', keyLength: 128 },
  { value: 'AES-256-CBC', label: 'AES-256-CBC', keyLength: 256 },
  { value: 'AES-256-GCM', label: 'AES-256-GCM', keyLength: 256 },
]

const rsaKeySizeOptions = [
  { value: 1024, label: '1024 位' },
  { value: 2048, label: '2048 位' },
  { value: 4096, label: '4096 位' },
]

const sm2CurveOptions = [
  { value: 'sm2p256v1', label: 'SM2 P-256v1' },
  { value: 'sm2p256r1', label: 'SM2 P-256r1' },
]

const rotationIntervalOptions = [
  { value: 30, label: '30 天' },
  { value: 60, label: '60 天' },
  { value: 90, label: '90 天' },
  { value: 180, label: '180 天' },
  { value: 365, label: '1 年' },
]

const handleConfigChange = () => {
  hasUnsavedChanges.value = true
}

const handleSaveConfig = async () => {
  isLoading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('加密配置保存成功')
    hasUnsavedChanges.value = false
  } catch {
    ElMessage.error('保存失败，请重试')
  } finally {
    isLoading.value = false
  }
}

const handleResetConfig = () => {
  configForm.algorithm = 'AES-256-GCM'
  configForm.keyLength = 256
  configForm.enableAes = true
  configForm.enableRsa = true
  configForm.enableSm2 = false
  configForm.rsaKeySize = 2048
  configForm.sm2Curve = 'sm2p256v1'
  configForm.rotationInterval = 90
  configForm.enableKeyBackup = true
  configForm.enableKeyAudit = true
  hasUnsavedChanges.value = false
  ElMessage.success('配置已重置')
}

const handleBackupKey = () => {
  ElMessage.info('正在备份密钥...')
}

const handleRotateKey = () => {
  ElMessage.info('正在轮换密钥...')
}
</script>

<template>
  <div class="encryption-config">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>敏感数据加密配置</span>
        </div>
      </template>

      <el-alert
        title="加密配置说明"
        type="info"
        description="配置系统的数据加密策略，确保敏感信息的安全"
        :closable="false"
        show-icon
        class="mb-4"
      />

      <el-form :model="configForm" label-width="140px">
        <el-divider content-position="left">AES 配置</el-divider>

        <el-form-item label="加密算法">
          <el-select v-model="configForm.algorithm" @change="handleConfigChange">
            <el-option
              v-for="item in algorithmOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="密钥长度">
          <el-select v-model="configForm.keyLength" @change="handleConfigChange">
            <el-option label="128 位" :value="128" />
            <el-option label="256 位" :value="256" />
          </el-select>
        </el-form-item>

        <el-form-item label="启用 AES 加密">
          <el-switch v-model="configForm.enableAes" @change="handleConfigChange" />
        </el-form-item>

        <el-divider content-position="left">RSA 配置</el-divider>

        <el-form-item label="启用 RSA 加密">
          <el-switch v-model="configForm.enableRsa" @change="handleConfigChange" />
        </el-form-item>

        <el-form-item label="RSA 密钥大小">
          <el-select v-model="configForm.rsaKeySize" @change="handleConfigChange">
            <el-option
              v-for="item in rsaKeySizeOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">SM2 配置</el-divider>

        <el-form-item label="启用 SM2 加密">
          <el-switch v-model="configForm.enableSm2" @change="handleConfigChange" />
        </el-form-item>

        <el-form-item label="SM2 曲线">
          <el-select v-model="configForm.sm2Curve" @change="handleConfigChange">
            <el-option
              v-for="item in sm2CurveOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">密钥管理</el-divider>

        <el-form-item label="密钥轮换周期">
          <el-select v-model="configForm.rotationInterval" @change="handleConfigChange">
            <el-option
              v-for="item in rotationIntervalOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="启用密钥备份">
          <el-switch v-model="configForm.enableKeyBackup" @change="handleConfigChange" />
        </el-form-item>

        <el-form-item label="启用密钥审计">
          <el-switch v-model="configForm.enableKeyAudit" @change="handleConfigChange" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="isLoading" @click="handleSaveConfig">
            保存配置
          </el-button>
          <el-button @click="handleResetConfig">重置</el-button>
          <el-button @click="handleBackupKey">
            <el-icon class="el-icon--left"><Refresh /></el-icon>
            备份密钥
          </el-button>
          <el-button @click="handleRotateKey">
            <el-icon class="el-icon--left"><Key /></el-icon>
            轮换密钥
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.encryption-config {
  padding: 0px;
}

.card-header {
  font-weight: 600;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>
