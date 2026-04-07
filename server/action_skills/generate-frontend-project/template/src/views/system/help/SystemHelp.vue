<template>
  <div class="system-help-container">
    <el-card shadow="never">
      <template #header>
        <span>帮助中心</span>
      </template>

      <el-row :gutter="20">
        <el-col :span="6">
          <el-menu :default-active="activeMenu" @select="handleMenuSelect">
            <el-menu-item index="quickstart">
              <el-icon><House /></el-icon>
              <span>快速入门</span>
            </el-menu-item>
            <el-menu-item index="user">
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
            <el-menu-item index="role">
              <el-icon><Key /></el-icon>
              <span>角色权限</span>
            </el-menu-item>
            <el-menu-item index="dept">
              <el-icon><OfficeBuilding /></el-icon>
              <span>部门管理</span>
            </el-menu-item>
            <el-menu-item index="system">
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </el-menu-item>
            <el-menu-item index="faq">
              <el-icon><Question /></el-icon>
              <span>常见问题</span>
            </el-menu-item>
          </el-menu>
        </el-col>

        <el-col :span="18">
          <div class="help-content">
            <div v-show="activeMenu === 'quickstart'" class="help-panel">
              <h2>快速入门</h2>
              <el-divider />
              <h3>系统概述</h3>
              <p>本系统是一套功能完善的企业级后台管理系统，提供了用户管理、角色权限、部门管理、系统配置等核心功能。</p>
              
              <h3>快速开始</h3>
              <el-steps direction="vertical" :space="80" :active="0">
                <el-step title="登录系统" description="使用管理员账号密码登录系统" />
                <el-step title="基础配置" description="在系统设置中配置基本信息" />
                <el-step title="创建角色" description="根据业务需求创建相应的角色" />
                <el-step title="分配权限" description="为角色分配适当的权限" />
                <el-step title="添加用户" description="创建用户并分配角色" />
              </el-steps>
            </div>

            <div v-show="activeMenu === 'user'" class="help-panel">
              <h2>用户管理</h2>
              <el-divider />
              <h3>功能说明</h3>
              <p>用户管理模块用于管理系统用户，包括用户的增删改查、状态管理、角色分配等功能。</p>
              
              <h3>操作指南</h3>
              <ul class="help-list">
                <li><strong>新增用户</strong>：点击"新增用户"按钮，填写用户信息后保存</li>
                <li><strong>编辑用户</strong>：点击用户操作栏的"编辑"按钮，修改用户信息</li>
                <li><strong>删除用户</strong>：点击用户操作栏的"删除"按钮，确认后删除用户</li>
                <li><strong>分配角色</strong>：在编辑用户时，可以通过角色选择器分配用户的角色</li>
              </ul>
            </div>

            <div v-show="activeMenu === 'role'" class="help-panel">
              <h2>角色权限</h2>
              <el-divider />
              <h3>功能说明</h3>
              <p>角色权限模块用于管理系统角色和权限，支持树形权限配置。</p>
              
              <h3>权限配置</h3>
              <p>权限采用树形结构组织，包含三种类型：</p>
              <ul class="help-list">
                <li><strong>目录</strong>：用于分组，无实际权限</li>
                <li><strong>菜单</strong>：对应具体的功能页面</li>
                <li><strong>按钮</strong>：页面的具体操作权限</li>
              </ul>
            </div>

            <div v-show="activeMenu === 'dept'" class="help-panel">
              <h2>部门管理</h2>
              <el-divider />
              <h3>功能说明</h3>
              <p>部门管理模块采用树形结构展示，支持多级部门配置。</p>
              
              <h3>操作说明</h3>
              <ul class="help-list">
                <li>点击部门名称前的展开按钮可查看子部门</li>
                <li>支持新增同级部门或子部门</li>
                <li>删除部门时，如果有子部门会一并删除</li>
              </ul>
            </div>

            <div v-show="activeMenu === 'system'" class="help-panel">
              <h2>系统设置</h2>
              <el-divider />
              <h3>配置项说明</h3>
              <ul class="help-list">
                <li><strong>基本信息</strong>：系统名称、Logo、版权等基础信息</li>
                <li><strong>安全配置</strong>：密码策略、会话超时等安全相关配置</li>
                <li><strong>邮件配置</strong>：系统邮件发送相关配置</li>
                <li><strong>上传配置</strong>：文件上传的类型和大小限制</li>
              </ul>
            </div>

            <div v-show="activeMenu === 'faq'" class="help-panel">
              <h2>常见问题</h2>
              <el-divider />
              
              <el-collapse>
                <el-collapse-item title="忘记密码怎么办？" name="1">
                  <p>请联系系统管理员，在数据库中重置密码。</p>
                </el-collapse-item>
                <el-collapse-item title="如何创建新角色？" name="2">
                  <p>在角色管理页面点击"新增角色"，填写角色信息后保存即可。</p>
                </el-collapse-item>
                <el-collapse-item title="权限不生效怎么办？" name="3">
                  <p>请检查：1. 用户是否分配了正确的角色；2. 角色是否配置了相应的权限；3. 清除浏览器缓存后重新登录。</p>
                </el-collapse-item>
                <el-collapse-item title="如何导出数据？" name="4">
                  <p>在相应的列表页面，点击"导出"按钮即可导出数据为Excel格式。</p>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>

          <div class="help-footer">
            <el-divider />
            <div class="contact-info">
              <p>如需更多帮助，请联系技术支持</p>
              <p>邮箱：support@example.com | 电话：400-xxx-xxxx</p>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { House, User, Key, OfficeBuilding, Setting } from '@element-plus/icons-vue'

const activeMenu = ref('quickstart')

const handleMenuSelect = (index: string) => {
  activeMenu.value = index
}
</script>

<style scoped>
.system-help-container {
  padding: 0px;
}

.help-content {
  min-height: 500px;
}

.help-panel h2 {
  margin-bottom: 10px;
}

.help-panel h3 {
  margin: 20px 0 10px;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.help-panel p {
  line-height: 1.8;
  color: var(--el-text-color-regular);
  margin: 10px 0;
}

.help-list {
  padding-left: 20px;
  color: var(--el-text-color-regular);
}

.help-list li {
  line-height: 2;
}

.help-footer {
  margin-top: 40px;
}

.contact-info {
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
</style>
