<template>
  <div class="system-config-container">
    <el-card shadow="never">
      <template #header>
        <span>系统配置</span>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="basic">
          <el-form :model="basicConfig" label-width="120px" class="config-form">
            <el-form-item label="系统名称">
              <el-input v-model="basicConfig.systemName" placeholder="请输入系统名称" />
            </el-form-item>
            <el-form-item label="系统Logo">
              <el-input v-model="basicConfig.logo" placeholder="请输入Logo URL">
                <template #append>
                  <el-button>上传</el-button>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="系统描述">
              <el-input v-model="basicConfig.description" type="textarea" :rows="3" placeholder="请输入系统描述" />
            </el-form-item>
            <el-form-item label="版权信息">
              <el-input v-model="basicConfig.copyright" placeholder="请输入版权信息" />
            </el-form-item>
            <el-form-item label="版本号">
              <el-input v-model="basicConfig.version" disabled />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="安全配置" name="security">
          <el-form :model="securityConfig" label-width="120px" class="config-form">
            <el-form-item label="会话超时">
              <el-input-number v-model="securityConfig.sessionTimeout" :min="5" :max="120" />
              <span class="config-tip">分钟</span>
            </el-form-item>
            <el-form-item label="密码最小长度">
              <el-input-number v-model="securityConfig.passwordMinLength" :min="6" :max="20" />
            </el-form-item>
            <el-form-item label="密码复杂度">
              <el-checkbox-group v-model="securityConfig.passwordPolicy">
                <el-checkbox label="upper">必须包含大写字母</el-checkbox>
                <el-checkbox label="lower">必须包含小写字母</el-checkbox>
                <el-checkbox label="number">必须包含数字</el-checkbox>
                <el-checkbox label="special">必须包含特殊字符</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="登录失败锁定">
              <el-input-number v-model="securityConfig.maxLoginAttempts" :min="3" :max="10" />
              <span class="config-tip">次后锁定账户</span>
            </el-form-item>
            <el-form-item label="锁定时间">
              <el-input-number v-model="securityConfig.lockTime" :min="5" :max="1440" />
              <span class="config-tip">分钟</span>
            </el-form-item>
            <el-form-item label="双因素认证">
              <el-switch v-model="securityConfig.twoFactorAuth" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="邮件配置" name="email">
          <el-form :model="emailConfig" label-width="120px" class="config-form">
            <el-form-item label="SMTP服务器">
              <el-input v-model="emailConfig.smtpHost" placeholder="请输入SMTP服务器地址" />
            </el-form-item>
            <el-form-item label="SMTP端口">
              <el-input-number v-model="emailConfig.smtpPort" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="emailConfig.username" placeholder="请输入用户名" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="emailConfig.password" type="password" show-password placeholder="请输入密码" />
            </el-form-item>
            <el-form-item label="发件人">
              <el-input v-model="emailConfig.from" placeholder="请输入发件人邮箱" />
            </el-form-item>
            <el-form-item label="使用SSL">
              <el-switch v-model="emailConfig.useSSL" />
            </el-form-item>
            <el-form-item label="测试连接">
              <el-button @click="handleTestEmail">发送测试邮件</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="上传配置" name="upload">
          <el-form :model="uploadConfig" label-width="120px" class="config-form">
            <el-form-item label="允许的文件类型">
              <el-checkbox-group v-model="uploadConfig.allowedTypes">
                <el-checkbox label="jpg">JPG</el-checkbox>
                <el-checkbox label="png">PNG</el-checkbox>
                <el-checkbox label="pdf">PDF</el-checkbox>
                <el-checkbox label="doc">DOC</el-checkbox>
                <el-checkbox label="xls">XLS</el-checkbox>
                <el-checkbox label="zip">ZIP</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="单个文件大小">
              <el-input-number v-model="uploadConfig.maxFileSize" :min="1" :max="100" />
              <span class="config-tip">MB</span>
            </el-form-item>
            <el-form-item label="总文件大小">
              <el-input-number v-model="uploadConfig.maxTotalSize" :min="10" :max="1000" />
              <span class="config-tip">MB</span>
            </el-form-item>
            <el-form-item label="存储方式">
              <el-radio-group v-model="uploadConfig.storage">
                <el-radio label="local">本地存储</el-radio>
                <el-radio label="oss">对象存储</el-radio>
                <el-radio label="cos">云存储</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div class="form-actions">
        <el-button type="primary" @click="handleSave">保存配置</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('basic')

const basicConfig = reactive({
  systemName: '后台管理系统',
  logo: '',
  description: '一套高效、稳定的企业级后台管理系统',
  copyright: '© 2024 Company Name. All rights reserved.',
  version: '1.0.0'
})

const securityConfig = reactive({
  sessionTimeout: 30,
  passwordMinLength: 8,
  passwordPolicy: ['upper', 'lower', 'number'],
  maxLoginAttempts: 5,
  lockTime: 30,
  twoFactorAuth: false
})

const emailConfig = reactive({
  smtpHost: 'smtp.example.com',
  smtpPort: 465,
  username: '',
  password: '',
  from: '',
  useSSL: true
})

const uploadConfig = reactive({
  allowedTypes: ['jpg', 'png', 'pdf', 'doc', 'xls'],
  maxFileSize: 10,
  maxTotalSize: 100,
  storage: 'local'
})

const handleSave = () => {
  ElMessage.success('配置保存成功')
}

const handleReset = () => {
  ElMessage.info('配置已重置')
}

const handleTestEmail = () => {
  ElMessage.success('测试邮件已发送')
}
</script>

<style scoped>
.system-config-container {
  padding: 0px;
}

.config-form {
  max-width: 600px;
  margin: 20px 0;
}

.config-tip {
  margin-left: 10px;
  color: var(--el-text-color-secondary);
}

.form-actions {
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color);
  margin-top: 20px;
}
</style>
