<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import {
  LayoutDashboard,
  Users,
  Bot,
  Server,
  MessageSquare,
  Zap,
  Library,
  Share2,
  FileText,
  Code
} from 'lucide-vue-next'

const { t } = useI18n()

const helpItems = [
  { 
    icon: LayoutDashboard, 
    titleKey: 'help.nav_agent', 
    descKey: 'help.nav_agent_desc',
    color: 'text-blue-500',
    bg: 'bg-blue-50'
  },
  { 
    icon: Users, 
    titleKey: 'help.nav_user_mgmt', 
    descKey: 'help.nav_user_mgmt_desc',
    color: 'text-green-500',
    bg: 'bg-green-50'
  },
  { 
    icon: Bot, 
    titleKey: 'help.nav_agent_mgmt', 
    descKey: 'help.nav_agent_mgmt_desc',
    color: 'text-purple-500',
    bg: 'bg-purple-50'
  },
  { 
    icon: Server, 
    titleKey: 'help.nav_mcp_mgmt', 
    descKey: 'help.nav_mcp_mgmt_desc',
    color: 'text-orange-500',
    bg: 'bg-orange-50'
  },
  { 
    icon: MessageSquare, 
    titleKey: 'help.nav_history', 
    descKey: 'help.nav_history_desc',
    color: 'text-cyan-500',
    bg: 'bg-cyan-50'
  },
  { 
    icon: Zap, 
    titleKey: 'help.nav_skills', 
    descKey: 'help.nav_skills_desc',
    color: 'text-yellow-500',
    bg: 'bg-yellow-50'
  },
  { 
    icon: Library, 
    titleKey: 'help.nav_knowledge', 
    descKey: 'help.nav_knowledge_desc',
    color: 'text-red-500',
    bg: 'bg-red-50'
  },
  { 
    icon: Share2, 
    titleKey: 'help.nav_knowledge_graph', 
    descKey: 'help.nav_knowledge_graph_desc',
    color: 'text-pink-500',
    bg: 'bg-pink-50'
  },
  { 
    icon: FileText, 
    titleKey: 'help.nav_content_plaza', 
    descKey: 'help.nav_content_plaza_desc',
    color: 'text-indigo-500',
    bg: 'bg-indigo-50'
  },
  { 
    icon: Code, 
    titleKey: 'help.nav_api_platform', 
    descKey: 'help.nav_api_platform_desc',
    color: 'text-gray-500',
    bg: 'bg-gray-50'
  }
]
</script>

<template>
  <div class="container mx-auto max-w-5xl py-8 px-4">
    <div class="text-center mb-10">
      <h1 class="text-3xl font-bold text-gray-900 mb-2">{{ t('help.title') }}</h1>
      <p class="text-gray-500 text-lg">{{ t('help.subtitle') }}</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div 
        v-for="(item, index) in helpItems" 
        :key="index"
        class="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow p-6 flex items-start gap-4"
      >
        <div 
          class="shrink-0 w-12 h-12 rounded-lg flex items-center justify-center"
          :class="item.bg"
        >
          <component :is="item.icon" class="w-6 h-6" :class="item.color" />
        </div>
        
        <div>
          <h3 class="text-lg font-semibold text-gray-900 mb-2">
            {{ t(item.titleKey) }}
          </h3>
          <p class="text-gray-600 leading-relaxed text-sm">
            {{ t(item.descKey) }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
