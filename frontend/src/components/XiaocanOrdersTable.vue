<template>
  <el-card class="orders-card xiaocan-card" shadow="never">
    <template #header>
      <div class="table-header">
        <span class="title">小蚕订单明细</span>
        <span class="total-text">共 {{ total }} 行</span>
        <div class="filter-bar">
          <el-input
            v-model="filters.order_no"
            placeholder="小蚕订单编号/平台单号"
            clearable
            style="width: 220px"
            @keyup.enter="applyFilters"
            @clear="applyFilters"
          />
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
            @change="applyFilters"
          />
          <el-select
            v-model="filters.platform"
            placeholder="下单平台"
            clearable
            filterable
            style="width: 150px"
            @change="applyFilters"
          >
            <el-option v-for="p in platformOptions" :key="p" :label="p" :value="p" />
          </el-select>
          <el-select
            v-model="filters.matched"
            placeholder="匹配状态"
            clearable
            style="width: 140px"
            @change="applyFilters"
          >
            <el-option label="已匹配原订单" :value="true" />
            <el-option label="未匹配" :value="false" />
          </el-select>
          <el-button type="primary" @click="applyFilters">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-divider direction="vertical" />
          <el-button
            type="danger"
            plain
            :disabled="!selectedRows.length"
            @click="handleDeleteSelected"
          >
            删除选中<template v-if="selectedRows.length"> ({{ selectedRows.length }})</template>
          </el-button>
          <el-button type="danger" @click="handleDeleteAll">清空所有</el-button>
        </div>
      </div>
    </template>

    <el-table
      v-loading="loading"
      :data="rows"
      border
      stripe
      size="small"
      height="500"
      style="width: 100%"
      @sort-change="onSortChange"
      @selection-change="onSelectionChange"
    >
      <el-table-column type="selection" width="45" fixed="left" />
      <el-table-column prop="xiaocan_order_no" label="小蚕订单编号" width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.xiaocan_order_no || '-' }}</template>
      </el-table-column>
      <el-table-column prop="platform" label="下单平台" width="110" sortable="custom">
        <template #default="{ row }">
          <el-tag v-if="row.platform" :type="platformTag(row.platform)" size="small">{{ row.platform }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="order_time" label="订单时间" width="160" sortable="custom">
        <template #default="{ row }">{{ formatDate(row.order_time) }}</template>
      </el-table-column>
      <el-table-column prop="platform_order_no" label="平台订单编号" width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <span :class="{ matched: isMatched(row) }">{{ row.platform_order_no || '-' }}</span>
          <el-tag v-if="isMatched(row)" type="success" size="small" style="margin-left: 8px">已匹配</el-tag>
          <el-tag v-else type="info" size="small" style="margin-left: 8px">未匹配</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="settlement_amount" label="结算金额" width="120" align="right" sortable="custom">
        <template #default="{ row }">{{ formatNum(row.settlement_amount) }}</template>
      </el-table-column>
      <el-table-column prop="imported_at" label="导入时间" width="160">
        <template #default="{ row }">{{ formatDate(row.imported_at) }}</template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @size-change="load"
        @current-change="load"
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchXiaocanOrders,
  deleteAllXiaocanOrders,
  deleteXiaocanOrdersBatch,
  type XiaocanOrderRow,
} from '../api'

const rows = ref<XiaocanOrderRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)

const filters = reactive({
  platform: '' as string,
  matched: null as boolean | null,
  order_no: '' as string,
  dateRange: null as [string, string] | null,
})
const platformOptions = ref<string[]>(['美团', '饿了么'])

const sort = ref('order_time')
const dir = ref<'asc' | 'desc'>('desc')
const selectedRows = ref<XiaocanOrderRow[]>([])

const emit = defineEmits<{ (e: 'data-changed'): void }>()

// Track which platform_order_no values match a coffee_order (computed by joining
// with the /orders endpoint lazily is too expensive; instead we rely on the
// "matched" filter param of the backend, which uses EXISTS subquery). For row-
// level display we maintain a set of matched ids fetched via filter=matched=true.
const matchedIds = ref<Set<number>>(new Set())

function onSelectionChange(r: XiaocanOrderRow[]) {
  selectedRows.value = r
}

async function load() {
  loading.value = true
  try {
    const res = await fetchXiaocanOrders({
      page: page.value,
      size: size.value,
      platform: filters.platform || undefined,
      matched: filters.matched === null ? undefined : filters.matched,
      order_no: filters.order_no || undefined,
      date_from: filters.dateRange?.[0] || undefined,
      date_to: filters.dateRange?.[1] || undefined,
      sort: sort.value,
      dir: dir.value,
    })
    rows.value = res.items
    total.value = res.total
    // Refresh matched-id set so the row badge stays correct across pagination
    await refreshMatchedIds()
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '查询失败'
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}

async function refreshMatchedIds() {
  try {
    const res = await fetchXiaocanOrders({ page: 1, size: 500, matched: true })
    matchedIds.value = new Set(res.items.map((r) => r.id))
  } catch {
    /* keep empty */
  }
}

function isMatched(row: XiaocanOrderRow): boolean {
  return matchedIds.value.has(row.id)
}

function applyFilters() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.platform = ''
  filters.matched = null
  filters.order_no = ''
  filters.dateRange = null
  page.value = 1
  load()
}

function onSortChange({ prop, order }: { prop: string; order: string | null }) {
  if (!prop || !order) {
    sort.value = 'order_time'
    dir.value = 'desc'
  } else {
    sort.value = prop
    dir.value = order === 'ascending' ? 'asc' : 'desc'
  }
  load()
}

function formatDate(v: string | null): string {
  if (!v) return ''
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatNum(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function platformTag(p: string): 'warning' | 'primary' | 'info' {
  if (p?.includes('美团')) return 'warning'
  if (p?.includes('饿了么') || p?.includes('饿百')) return 'primary'
  return 'info'
}

async function handleDeleteSelected() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedRows.value.length} 行小蚕订单？此操作不可恢复，且会刷新原订单的"是否小蚕订单"标记。`,
      '批量删除',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const ids = selectedRows.value.map((r) => r.id)
    const res = await deleteXiaocanOrdersBatch(ids)
    ElMessage.success(`已删除 ${res.deleted} 行`)
    selectedRows.value = []
    await load()
    emit('data-changed')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || err?.message || '删除失败')
  }
}

async function handleDeleteAll() {
  try {
    await ElMessageBox.confirm(
      '此操作将清空所有小蚕订单，并把原订单的"是否小蚕订单"标记全部重置为否，确认继续？',
      '清空全部数据',
      { type: 'error', confirmButtonText: '确认清空', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const res = await deleteAllXiaocanOrders()
    ElMessage.success(`已清空 ${res.deleted} 行小蚕订单`)
    selectedRows.value = []
    await load()
    emit('data-changed')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || err?.message || '删除失败')
  }
}

defineExpose({ refresh: load })

onMounted(load)
</script>

<style scoped>
.orders-card {
  border-radius: 10px;
  margin-bottom: 18px;
}
.xiaocan-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #6a3aa0 0%, #4a2c70 100%);
  color: #fff;
}
.table-header .title {
  color: #fff;
  font-weight: 600;
  font-size: 15px;
}
.total-text {
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
}
.table-header {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.filter-bar {
  margin-left: auto;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.matched {
  color: #67c23a;
  font-weight: 600;
}
</style>
