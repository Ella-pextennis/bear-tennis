<template>
  <el-card class="trend-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="title">每日订单趋势 · 分渠道</span>
        <span class="subtitle">按订单来源汇总（美团 / 饿了么 / 其他）</span>
      </div>
    </template>

    <div v-loading="loading" class="chart-wrap">
      <el-empty v-if="!items.length && !loading" description="暂无趋势数据，请上传多日订单" :image-size="80" />
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
import { fetchDailyTrend, type DailyTrendItem } from '../api'

use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkPointComponent,
])

const items = ref<DailyTrendItem[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await fetchDailyTrend()
    items.value = res.items ?? []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

const loadingOptions = {
  text: '加载中...',
  color: '#a3683f',
  textColor: '#6b4226',
  maskColor: 'rgba(255, 255, 255, 0.6)',
}

const chartOption = computed(() => {
  const dates = items.value.map((i) => i.date)
  const meituan = items.value.map((i) => i.meituan)
  const eleme = items.value.map((i) => i.eleme)
  const other = items.value.map((i) => i.other)

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(40, 28, 20, 0.92)',
      borderWidth: 0,
      textStyle: { color: '#fff', fontSize: 12 },
      extraCssText: 'border-radius:8px;box-shadow:0 4px 14px rgba(0,0,0,0.2);',
      formatter: (params: any[]) => {
        const date = params[0]?.axisValue ?? ''
        const lines = params
          .map((p) => {
            const detail = items.value[p.dataIndex]?.detail || {}
            const detailStr = Object.entries(detail)
              .map(([src, cnt]) => `${src}: ${cnt}`)
              .join('　')
            return `<div style="margin:4px 0;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px;"></span>
              ${p.seriesName}: <b>${p.value}</b> 单
              ${detailStr ? `<span style="color:rgba(255,255,255,0.6);font-size:11px;margin-left:6px;">(${detailStr})</span>` : ''}
            </div>`
          })
          .join('')
        return `<div style="font-weight:600;margin-bottom:2px;">${date}</div>${lines}`
      },
    },
    legend: {
      data: ['美团', '饿了么', '其他渠道'],
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
      boundaryGap: false,
      data: dates,
      axisLine: { lineStyle: { color: '#d8c9b8' } },
      axisLabel: {
        color: '#8a6f55',
        fontSize: 11,
        formatter: (val: string) => val.slice(5),
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
        fillerColor: 'rgba(163, 104, 63, 0.18)',
        handleStyle: { color: '#a3683f', borderColor: '#a3683f' },
        textStyle: { color: '#8a6f55', fontSize: 10 },
      },
    ],
    series: [
      {
        name: '美团',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        data: meituan,
        itemStyle: { color: '#ff8c00' },
        lineStyle: { width: 3, color: '#ff8c00' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(255, 140, 0, 0.28)' },
              { offset: 1, color: 'rgba(255, 140, 0, 0.02)' },
            ],
          },
        },
        markPoint: {
          symbol: 'pin',
          symbolSize: 44,
          label: { fontSize: 11, color: '#fff' },
          itemStyle: { color: '#ff8c00' },
          data: [{ type: 'max', name: '峰值' }],
        },
      },
      {
        name: '饿了么',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        data: eleme,
        itemStyle: { color: '#0070e0' },
        lineStyle: { width: 3, color: '#0070e0' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 112, 224, 0.24)' },
              { offset: 1, color: 'rgba(0, 112, 224, 0.02)' },
            ],
          },
        },
        markPoint: {
          symbol: 'pin',
          symbolSize: 44,
          label: { fontSize: 11, color: '#fff' },
          itemStyle: { color: '#0070e0' },
          data: [{ type: 'max', name: '峰值' }],
        },
      },
      {
        name: '其他渠道',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        data: other,
        itemStyle: { color: '#8a5a3b' },
        lineStyle: { width: 3, color: '#8a5a3b' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(138, 90, 59, 0.22)' },
              { offset: 1, color: 'rgba(138, 90, 59, 0.02)' },
            ],
          },
        },
      },
    ],
  }
})

defineExpose({ refresh: load })

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
