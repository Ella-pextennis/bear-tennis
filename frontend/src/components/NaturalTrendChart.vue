<template>
  <el-card class="trend-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="title">自然流线上订单 · 每日波动</span>
        <span class="subtitle">自然流 = 美团 + 饿了么 - 小蚕（按日）</span>
      </div>
    </template>

    <div v-loading="loading" class="chart-wrap">
      <el-empty v-if="!items.length && !loading" description="暂无趋势数据" :image-size="80" />
      <v-chart
        v-else
        class="chart"
        :option="chartOption"
        :autoresize="true"
        :loading="loading"
        :loading-options="loadingOptions"
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkPointComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { fetchNaturalTrend, type NaturalTrendItem } from '../api'

use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkPointComponent,
])

const items = ref<NaturalTrendItem[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await fetchNaturalTrend()
    items.value = res.items ?? []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

function updateData(data: { items: NaturalTrendItem[] }) {
  items.value = data.items ?? []
}

const loadingOptions = {
  text: '加载中...',
  color: '#5b6cb8',
  textColor: '#3a4a8a',
  maskColor: 'rgba(255, 255, 255, 0.6)',
}

const chartOption = computed(() => {
  const dates = items.value.map((i) => i.date)
  const natural = items.value.map((i) => i.natural)

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(40, 28, 60, 0.92)',
      borderWidth: 0,
      textStyle: { color: '#fff', fontSize: 12 },
      extraCssText: 'border-radius:8px;box-shadow:0 4px 14px rgba(0,0,0,0.2);',
      formatter: (params: any[]) => {
        const date = params[0]?.axisValue ?? ''
        const idx = params[0]?.dataIndex ?? 0
        const item = items.value[idx]
        if (!item) return date
        const d = new Date(date)
        const weekdays = ['日', '一', '二', '三', '四', '五', '六']
        const weekday = weekdays[d.getDay()]
        return `<div style="font-weight:600;margin-bottom:4px;">${date} (周${weekday})</div>
          <div style="margin:3px 0;">自然流线上: <b style="color:#5b8def;">${item.natural}</b> 单</div>`
      },
    },
    legend: {
      data: ['自然流线上'],
      top: 6,
      right: 12,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: '#5a4a3a', fontSize: 12 },
    },
    grid: {
      left: 48,
      right: 24,
      top: 48,
      bottom: 64,
      containLabel: false,
    },
    xAxis: {
      type: 'category',
      boundaryGap: true,
      data: dates,
      axisLine: { lineStyle: { color: '#d8c9b8' } },
      axisLabel: {
        color: '#8a6f55',
        fontSize: 11,
        formatter: (val: string) => {
          const d = new Date(val)
          const weekdays = ['日', '一', '二', '三', '四', '五', '六']
          return `${val.slice(5)} (周${weekdays[d.getDay()]})`
        },
      },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '订单数',
      nameTextStyle: { color: '#8a6f55', fontSize: 11, padding: [0, 0, 4, -18] },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#8a6f55', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f0e7dc', type: 'dashed' } },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 18,
        bottom: 12,
        borderColor: 'transparent',
        backgroundColor: '#f7efe5',
        fillerColor: 'rgba(91, 108, 184, 0.18)',
        handleStyle: { color: '#5b6cb8', borderColor: '#5b6cb8' },
        textStyle: { color: '#8a6f55', fontSize: 10 },
      },
    ],
    series: [
      {
        name: '自然流线上',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: natural,
        itemStyle: { color: '#5b6cb8' },
        lineStyle: { width: 3, color: '#5b6cb8' },
        label: {
          show: true,
          position: 'top',
          fontSize: 11,
          fontWeight: 600,
          color: '#3a4a8a',
          formatter: '{c}',
        },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(91, 108, 184, 0.35)' },
              { offset: 1, color: 'rgba(91, 108, 184, 0.02)' },
            ],
          },
        },
        markPoint: {
          symbol: 'pin',
          symbolSize: 44,
          label: { fontSize: 11, color: '#fff' },
          itemStyle: { color: '#5b6cb8' },
          data: [
            { type: 'max', name: '峰值' },
            { type: 'min', name: '低谷' },
          ],
        },
      },
    ],
  }
})

defineExpose({ refresh: load, updateData })

onMounted(load)
</script>

<style scoped>
.trend-card {
  margin-bottom: 18px;
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 12px rgba(107, 66, 38, 0.06);
}
.trend-card :deep(.el-card__header) {
  padding: 14px 18px 8px;
  border-bottom: 1px dashed #f0e0cf;
}
.card-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.title {
  font-size: 15px;
  font-weight: 600;
  color: #3a2a1f;
}
.subtitle {
  font-size: 12px;
  color: #a08770;
}
.chart-wrap {
  min-height: 320px;
  padding: 8px 8px 0;
}
.chart {
  width: 100%;
  height: 320px;
}
.el-empty {
  padding: 60px 0;
}
</style>
