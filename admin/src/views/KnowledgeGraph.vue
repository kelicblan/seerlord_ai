<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import axios from '@/api/axios'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()
const chartContainer = ref<HTMLElement | null>(null)
let myChart: echarts.ECharts | null = null
const loading = ref(false)

// Keep data in memory to re-render on locale change
let graphNodes: any[] = []
let graphLinks: any[] = []

const updateChartOptions = () => {
  if (!myChart) return

  const option = {
    title: {
      text: t('knowledge_graph.chart_title'),
      subtext: t('knowledge_graph.chart_subtext'),
      top: 'bottom',
      left: 'right'
    },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const props = params.data.properties
          let propStr = ''
          for (const key in props) {
            if (key !== 'embedding') // Hide embedding vector
              propStr += `<br/>${key}: ${props[key]}`
          }
          return `<strong>${params.name}</strong>${propStr}`
        } else {
          return `${params.data.source} -> ${params.data.target}<br/>Type: ${params.data.value}`
        }
      }
    },
    legend: [
      {
        data: [t('knowledge_graph.legend_entity'), t('knowledge_graph.legend_chunk')]
      }
    ],
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: graphNodes,
        links: graphLinks,
        categories: [
          { name: t('knowledge_graph.legend_entity') },
          { name: t('knowledge_graph.legend_chunk') }
        ],
        roam: true,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}'
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3
        },
        force: {
          repulsion: 300,
          edgeLength: 100
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 10
          }
        }
      }
    ]
  }

  myChart.setOption(option)
}

const initChart = async () => {
  if (!chartContainer.value) return

  // Dispose previous instance if exists to be safe, or just init if not
  if (!myChart) {
    myChart = echarts.init(chartContainer.value)
  }

  myChart.showLoading()
  loading.value = true

  try {
    const { data } = await axios.get('/api/v1/ske/graph?limit=300')

    graphNodes = data.nodes.map((node: any) => ({
      id: node.id,
      name: node.name,
      value: node.id,
      symbolSize: node.labels.includes('Entity') ? 30 : 15,
      category: node.labels.includes('Entity') ? 0 : 1,
      properties: node.properties
    }))

    graphLinks = data.links.map((link: any) => ({
      source: link.source,
      target: link.target,
      value: link.type
    }))

    updateChartOptions()
    myChart.hideLoading()

  } catch (error) {
    console.error('Failed to fetch graph data:', error)
    ElMessage.error(t('knowledge_graph.load_error'))
    myChart?.hideLoading()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  setTimeout(() => {
    initChart()
  }, 200)
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  myChart?.dispose()
})

const resizeChart = () => {
  myChart?.resize()
}

// Watch for locale changes to update chart text
watch(locale, () => {
  updateChartOptions()
})
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-bold">{{ t('knowledge_graph.title') }}</h2>
      <el-button type="primary" @click="initChart" :loading="loading">
        {{ t('knowledge_graph.refresh') }}
      </el-button>
    </div>
    <div ref="chartContainer" class="graph-container border border-gray-200 rounded bg-white"></div>
  </div>
</template>

<style scoped>
.graph-container{
  width: 100%;
  height: calc(100vh - 120px) !important;
}
</style>
