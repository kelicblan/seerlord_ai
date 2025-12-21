<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronRight, ChevronDown, Loader2, Brain, CheckCircle, XCircle, Terminal } from 'lucide-vue-next'
import type { ThoughtStep } from '@/composables/useAgent'

const { t } = useI18n()

const props = defineProps<{
  steps: ThoughtStep[]
  isFinished?: boolean
}>()

const isOpen = ref(true)

const formatDuration = (ms?: number) => {
  if (!ms) return ''
  return `${(ms / 1000).toFixed(2)}s`
}
</script>

<template>
  <div class="border rounded-md my-2 bg-muted/30" v-if="steps && steps.length > 0">
    <div 
      class="flex items-center gap-2 p-2 cursor-pointer hover:bg-muted/50 select-none text-sm text-muted-foreground"
      @click="isOpen = !isOpen"
    >
      <component :is="isOpen ? ChevronDown : ChevronRight" class="w-4 h-4" />
      <span class="font-medium">{{ t('common.thinking_process') }}</span>
      <Loader2 v-if="!isFinished" class="w-3 h-3 animate-spin ml-2" />
    </div>

    <div v-if="isOpen" class="p-2 pt-0 space-y-2">
      <div v-for="step in steps" :key="step.id" class="text-sm group">
        <div class="flex items-center gap-2 py-1">
          <!-- Icon based on type -->
          <div v-if="step.type === 'thought'" class="text-blue-500">
            <Brain class="w-4 h-4" />
          </div>
          <div v-else class="text-orange-500">
            <Terminal class="w-4 h-4" />
          </div>
          
          <span class="font-medium flex-1 truncate" :title="step.name">{{ step.name }}</span>
          
          <span v-if="step.duration" class="text-xs text-muted-foreground">{{ formatDuration(step.duration) }}</span>
          
          <!-- Status Icon -->
          <Loader2 v-if="step.status === 'pending'" class="w-3 h-3 animate-spin text-muted-foreground" />
          <CheckCircle v-else-if="step.status === 'success'" class="w-3 h-3 text-green-500" />
          <XCircle v-else class="w-3 h-3 text-red-500" />
        </div>
        
        <!-- Details for Tools (Input/Output) -->
        <div v-if="step.type === 'tool'" class="ml-6 pl-2 border-l-2 border-muted space-y-1 text-xs font-mono text-muted-foreground">
            <div v-if="step.input" class="bg-muted/30 p-1 rounded overflow-x-auto whitespace-pre-wrap break-all max-h-40 overflow-y-auto custom-scrollbar">
                <span class="font-bold select-none text-orange-600/70">Input: </span>{{ step.input }}
            </div>
            <div v-if="step.output" class="bg-muted/30 p-1 rounded overflow-x-auto whitespace-pre-wrap break-all max-h-40 overflow-y-auto custom-scrollbar">
                 <span class="font-bold select-none text-green-600/70">Output: </span>{{ step.output }}
            </div>
        </div>
      </div>
    </div>
  </div>
</template>
