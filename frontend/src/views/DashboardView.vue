<template>
  <div class="dashboard">
    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <UploadPanel @imported="onCoffeeImported" />
      </el-col>
      <el-col :xs="24" :md="12">
        <XiaocanUploadPanel @imported="onXiaocanImported" />
      </el-col>
    </el-row>

    <StatsCards :stats="stats" :loading="statsLoading" />

    <OrdersTable ref="tableRef" @data-changed="loadStats" />
    <XiaocanOrdersTable ref="xiaocanTableRef" @data-changed="onXiaocanDataChanged" />
    <XiaocanRebatePanel ref="rebateRef" @data-changed="loadStats" />
    <DailyTrendChart ref="trendRef" />
    <NaturalTrendChart ref="naturalTrendRef" />
    <ActualReceivedChart ref="actualReceivedRef" />

    <el-empty
      v-if="!statsLoading && stats.total_rows === 0"
      description="尚未导入数据，请上传 Excel 文件"
      :image-size="120"
      class="empty-state"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElRow, ElCol } from 'element-plus'
import UploadPanel from '../components/UploadPanel.vue'
import XiaocanUploadPanel from '../components/XiaocanUploadPanel.vue'
import StatsCards from '../components/StatsCards.vue'
import OrdersTable from '../components/OrdersTable.vue'
import XiaocanOrdersTable from '../components/XiaocanOrdersTable.vue'
import XiaocanRebatePanel from '../components/XiaocanRebatePanel.vue'
import DailyTrendChart from '../components/DailyTrendChart.vue'
import NaturalTrendChart from '../components/NaturalTrendChart.vue'
import ActualReceivedChart from '../components/ActualReceivedChart.vue'
import { fetchDashboard, type Stats, type TaskResult } from '../api'

const stats = ref<Stats>({
  total_rows: 0,
  orders_count: 0,
  total_amount: null,
  stores_count: 0,
  latest_import_at: null,
  source_breakdown: {},
  member_orders_count: 0,
  non_member_orders_count: 0,
  xiaocan_orders_count: 0,
  xiaocan_rebate_total: null,
  natural_online_orders: 0,
  actual_received: null,
})
const statsLoading = ref(false)
const tableRef = ref<InstanceType<typeof OrdersTable> | null>(null)
const xiaocanTableRef = ref<InstanceType<typeof XiaocanOrdersTable> | null>(null)
const rebateRef = ref<InstanceType<typeof XiaocanRebatePanel> | null>(null)
const trendRef = ref<InstanceType<typeof DailyTrendChart> | null>(null)
const naturalTrendRef = ref<InstanceType<typeof NaturalTrendChart> | null>(null)
const actualReceivedRef = ref<InstanceType<typeof ActualReceivedChart> | null>(null)

async function loadDashboard() {
  statsLoading.value = true
  try {
    const data = await fetchDashboard()
    stats.value = data.stats
    trendRef.value?.updateData(data.daily_trend)
    naturalTrendRef.value?.updateData(data.natural_trend)
    actualReceivedRef.value?.updateData(data.actual_received_trend)
  } catch {
    /* keep existing data */
  } finally {
    statsLoading.value = false
  }
}

function onCoffeeImported(_result: TaskResult) {
  loadDashboard()
  tableRef.value?.refresh()
}

function onXiaocanImported(_result: TaskResult) {
  loadDashboard()
  tableRef.value?.refresh()
  xiaocanTableRef.value?.refresh()
}

function onXiaocanDataChanged() {
  loadDashboard()
  tableRef.value?.refresh()
}

onMounted(() => {
  loadDashboard()
  rebateRef.value?.refresh()
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
}
.empty-state {
  margin-top: 24px;
}
</style>
