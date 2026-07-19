<template>
  <el-card class="orders-card" shadow="never">
    <template #header>
      <div class="table-header">
        <span class="title">订单明细</span>
        <span class="total-text">共 {{ total }} 行</span>
        <div class="filter-bar">
          <el-input
            v-model="filters.order_no"
            placeholder="订单号"
            clearable
            style="width: 180px"
            @keyup.enter="applyFilters"
            @clear="applyFilters"
          />
          <el-input
            v-model="filters.platform_order_no"
            placeholder="平台单号"
            clearable
            style="width: 180px"
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
            v-model="filters.store"
            placeholder="门店"
            clearable
            filterable
            style="width: 200px"
            @change="applyFilters"
          >
            <el-option v-for="s in filterOptions.stores" :key="s" :label="s" :value="s" />
          </el-select>
          <el-select
            v-model="filters.source"
            placeholder="订单来源"
            clearable
            filterable
            style="width: 150px"
            @change="applyFilters"
          >
            <el-option v-for="s in filterOptions.sources" :key="s" :label="s" :value="s" />
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
      height="600"
      style="width: 100%"
      :row-class-name="rowClass"
      @sort-change="onSortChange"
      @selection-change="onSelectionChange"
    >
      <el-table-column type="selection" width="45" fixed="left" />
      <el-table-column prop="order_no" label="订单号" width="200" fixed="left" sortable="custom" />
      <el-table-column prop="order_date" label="日期" width="160" sortable="custom">
        <template #default="{ row }">{{ formatDate(row.order_date) }}</template>
      </el-table-column>
      <el-table-column prop="store_name" label="门店" width="180" />
      <el-table-column prop="order_source" label="订单来源" width="100" />
      <el-table-column prop="member_no" label="会员号" width="110" />
      <el-table-column prop="unit_price" label="单价" width="100" align="right" sortable="custom">
        <template #default="{ row }">{{ formatNum(row.unit_price) }}</template>
      </el-table-column>
      <el-table-column prop="quantity" label="数量" width="80" align="right" sortable="custom">
        <template #default="{ row }">{{ formatNum(row.quantity) }}</template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="110" align="right" sortable="custom">
        <template #default="{ row }">
          <span :class="{ 'amt-negative': row.amount !== null && row.amount < 0 }">
            {{ formatNum(row.amount) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="platform_order_no" label="平台单号" width="220" show-overflow-tooltip sortable="custom">
        <template #default="{ row }">{{ row.platform_order_no || '-' }}</template>
      </el-table-column>
      <el-table-column prop="discount_amount" label="折让金额" width="110" align="right" sortable="custom">
        <template #default="{ row }">{{ formatNum(row.discount_amount) }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip />
      <el-table-column prop="imported_at" label="导入时间" width="160">
        <template #default="{ row }">{{ formatDate(row.imported_at) }}</template>
      </el-table-column>
      <el-table-column prop="is_xiaocan" label="是否小蚕订单" width="120" align="center" sortable="custom">
        <template #default="{ row }">
          <el-tag v-if="row.is_xiaocan === 1" type="success" size="small">是</el-tag>
          <el-tag v-else type="info" size="small">否</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="160" sortable="custom">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
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
  fetchOrders,
  fetchFilters,
  deleteAllOrders,
  deleteOrdersBatch,
  type OrderRow,
  type FilterOptions,
} from '../api'

const rows = ref<OrderRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)

const filters = reactive({
  order_no: '',
  platform_order_no: '',
  dateRange: null as [string, string] | null,
  store: '',
  source: '',
})
const filterOptions = reactive<FilterOptions>({ stores: [], sources: [], statuses: [] })

const sort = ref('order_date')
const dir = ref<'asc' | 'desc'>('desc')
const selectedRows = ref<OrderRow[]>([])

const emit = defineEmits<{ (e: 'data-changed'): void }>()

function onSelectionChange(rows: OrderRow[]) {
  selectedRows.value = rows
}

async function load() {
  loading.value = true
  try {
    const res = await fetchOrders({
      page: page.value,
      size: size.value,
      order_no: filters.order_no || undefined,
      platform_order_no: filters.platform_order_no || undefined,
      date_from: filters.dateRange?.[0] || undefined,
      date_to: filters.dateRange?.[1] || undefined,
      store: filters.store || undefined,
      source: filters.source || undefined,
      sort: sort.value,
      dir: dir.value,
    })
    rows.value = res.items
    total.value = res.total
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '查询失败'
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}

async function loadFilters() {
  try {
    const opts = await fetchFilters()
    filterOptions.stores = opts.stores
    filterOptions.sources = opts.sources
    filterOptions.statuses = opts.statuses
  } catch {
    /* dropdowns stay empty; user can still type-free filter via order_no/product */
  }
}

function applyFilters() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.order_no = ''
  filters.platform_order_no = ''
  filters.dateRange = null
  filters.store = ''
  filters.source = ''
  page.value = 1
  load()
}

function onSortChange({ prop, order }: { prop: string; order: string | null }) {
  if (!prop || !order) {
    sort.value = 'order_date'
    dir.value = 'desc'
  } else {
    sort.value = prop
    dir.value = order === 'ascending' ? 'asc' : 'desc'
  }
  load()
}

function rowClass({ row }: { row: OrderRow }): string {
  return row.is_order_header === 1 ? 'order-header-row' : ''
}

function formatDate(v: string | null): string {
  if (!v) return ''
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatNum(v: number | null | undefined): string {
  if (v === null || v === undefined) return ''
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function handleDeleteSelected() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedRows.value.length} 行数据？此操作不可恢复。`,
      '批量删除',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const ids = selectedRows.value.map((r) => r.id)
    const res = await deleteOrdersBatch(ids)
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
      '此操作将清空所有订单数据，且不可恢复，确认继续？',
      '清空全部数据',
      { type: 'error', confirmButtonText: '确认清空', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const res = await deleteAllOrders()
    ElMessage.success(`已清空 ${res.deleted} 行数据`)
    selectedRows.value = []
    await load()
    emit('data-changed')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || err?.message || '删除失败')
  }
}

defineExpose({ refresh: load })

onMounted(async () => {
  await Promise.all([load(), loadFilters()])
})
</script>

<style scoped>
.orders-card {
  border-radius: 10px;
}
.table-header {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.table-header .title {
  font-weight: 600;
  font-size: 15px;
}
.total-text {
  color: #909399;
  font-size: 13px;
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
:deep(.order-header-row) {
  background-color: #fdf6ec !important;
  font-weight: 600;
}
:deep(.order-header-row td .cell) {
  color: #8a5a3b;
}
.amt-negative {
  color: #f56c6c;
}
</style>
