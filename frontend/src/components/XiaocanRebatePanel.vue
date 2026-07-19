<template>
  <el-card class="rebate-panel xiaocan-card" shadow="never">
    <template #header>
      <div class="table-header">
        <span class="title">小蚕订单返现结算录入</span>
        <span class="total-text">
          已录入 {{ items.length }} 条 · 返现总额
          <b class="rebate-total">¥{{ formatAmount(totalAmount) }}</b>
        </span>
        <div class="filter-bar">
          <el-button type="danger" plain :disabled="!items.length" @click="handleDeleteAll">
            清空所有
          </el-button>
        </div>
      </div>
    </template>

    <el-form :model="form" inline class="rebate-form" @submit.prevent="handleSubmit">
      <el-form-item label="日期">
        <el-date-picker
          v-model="form.settle_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择日期"
          style="width: 160px"
        />
      </el-form-item>
      <el-form-item label="结算金额">
        <el-input-number
          v-model="form.amount"
          :min="0"
          :precision="2"
          :step="10"
          controls-position="right"
          style="width: 160px"
        />
      </el-form-item>
      <el-form-item label="备注">
        <el-input
          v-model="form.remark"
          placeholder="可选备注"
          clearable
          style="width: 280px"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">录入</el-button>
      </el-form-item>
    </el-form>

    <el-table
      v-loading="loading"
      :data="items"
      border
      stripe
      size="small"
      height="360"
      style="width: 100%"
      empty-text="暂无返现记录，请录入第一条"
    >
      <el-table-column prop="settle_date" label="日期" width="140" sortable />
      <el-table-column prop="amount" label="结算金额" width="140" align="right" sortable>
        <template #default="{ row }">
          <span class="amt">¥{{ formatAmount(row.amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.remark || '-' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="录入时间" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="handleEdit(row)">修改</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="修改返现记录" width="520px" :close-on-click-modal="false">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="日期" required>
          <el-date-picker
            v-model="editForm.settle_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结算金额" required>
          <el-input-number
            v-model="editForm.amount"
            :min="0"
            :precision="2"
            :step="10"
            controls-position="right"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="editForm.remark"
            placeholder="可选备注"
            clearable
            style="width: 100%"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleUpdate">确认修改</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchXiaocanRebates,
  addXiaocanRebate,
  updateXiaocanRebate,
  deleteXiaocanRebate,
  deleteAllXiaocanRebates,
  type XiaocanRebateItem,
} from '../api'

const emit = defineEmits<{ (e: 'data-changed'): void }>()

const items = ref<XiaocanRebateItem[]>([])
const totalAmount = ref(0)
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)

const form = reactive({
  settle_date: '',
  amount: 0,
  remark: '',
})

const editForm = reactive({
  settle_date: '',
  amount: 0,
  remark: '',
})

async function load() {
  loading.value = true
  try {
    const res = await fetchXiaocanRebates()
    items.value = res.items
    totalAmount.value = res.total_amount ? Number(res.total_amount) : 0
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '查询失败'
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!form.settle_date) {
    ElMessage.warning('请选择日期')
    return
  }
  if (!form.amount || form.amount <= 0) {
    ElMessage.warning('结算金额必须大于 0')
    return
  }
  submitting.value = true
  try {
    await addXiaocanRebate({
      settle_date: form.settle_date,
      amount: form.amount,
      remark: form.remark || null,
    })
    ElMessage.success('录入成功')
    form.amount = 0
    form.remark = ''
    await load()
    emit('data-changed')
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '录入失败'
    ElMessage.error(detail)
  } finally {
    submitting.value = false
  }
}

function handleEdit(row: XiaocanRebateItem) {
  editingId.value = row.id
  editForm.settle_date = row.settle_date
  editForm.amount = Number(row.amount)
  editForm.remark = row.remark || ''
  dialogVisible.value = true
}

async function handleUpdate() {
  if (!editForm.settle_date) {
    ElMessage.warning('请选择日期')
    return
  }
  if (!editForm.amount || editForm.amount <= 0) {
    ElMessage.warning('结算金额必须大于 0')
    return
  }
  if (!editingId.value) return
  submitting.value = true
  try {
    await updateXiaocanRebate(editingId.value, {
      settle_date: editForm.settle_date,
      amount: editForm.amount,
      remark: editForm.remark || null,
    })
    ElMessage.success('修改成功')
    dialogVisible.value = false
    editingId.value = null
    await load()
    emit('data-changed')
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || '修改失败'
    ElMessage.error(detail)
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: XiaocanRebateItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${row.settle_date} 的返现记录 ¥${formatAmount(row.amount)}？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteXiaocanRebate(row.id)
    ElMessage.success('已删除')
    await load()
    emit('data-changed')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || err?.message || '删除失败')
  }
}

async function handleDeleteAll() {
  try {
    await ElMessageBox.confirm(
      '此操作将清空所有返现记录，且不可恢复，确认继续？',
      '清空全部数据',
      { type: 'error', confirmButtonText: '确认清空', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteAllXiaocanRebates()
    ElMessage.success('已清空所有返现记录')
    await load()
    emit('data-changed')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || err?.message || '删除失败')
  }
}

function formatDate(v: string | null): string {
  if (!v) return ''
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return v
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatAmount(v: number | null | undefined): string {
  if (v === null || v === undefined) return '0.00'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

defineExpose({ refresh: load })

onMounted(load)
</script>

<style scoped>
.rebate-panel {
  border-radius: 10px;
  margin-bottom: 18px;
}
.xiaocan-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #6a3aa0 0%, #4a2c70 100%);
  color: #fff;
}
.table-header {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.table-header .title {
  color: #fff;
  font-weight: 600;
  font-size: 15px;
}
.total-text {
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
}
.rebate-total {
  color: #ffd953;
  font-size: 16px;
  margin-left: 4px;
}
.filter-bar {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
.rebate-form {
  margin-bottom: 12px;
}
.amt {
  color: #b8860b;
  font-weight: 600;
}
</style>
