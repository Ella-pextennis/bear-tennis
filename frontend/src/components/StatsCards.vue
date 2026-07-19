<template>
  <div class="stats-grid">
    <el-card class="stat-card orders" shadow="hover">
      <div class="stat-label">订单数</div>
      <div class="stat-value">{{ formatNum(stats.orders_count) }}</div>
      <div class="stat-sub">去重订单号</div>
    </el-card>
    <el-card class="stat-card accent" shadow="hover">
      <div class="stat-label">总金额</div>
      <div class="stat-value">¥{{ formatAmount(stats.total_amount) }}</div>
      <div class="stat-sub">订单头金额合计</div>
    </el-card>
    <el-card class="stat-card" shadow="hover">
      <div class="stat-label">门店数</div>
      <div class="stat-value">{{ formatNum(stats.stores_count) }}</div>
      <div class="stat-sub">{{ latestText }}</div>
    </el-card>
  </div>
  <div class="source-grid">
    <el-card class="stat-card source meituan" shadow="hover">
      <div class="stat-label">美团订单总量</div>
      <div class="stat-value">{{ sourceStats.meituan }}</div>
      <div class="stat-sub">美团外卖 · 美团到店 · 占比 {{ sourceStats.meituanRatio }}%</div>
    </el-card>
    <el-card class="stat-card source eleme" shadow="hover">
      <div class="stat-label">饿了么订单总量</div>
      <div class="stat-value">{{ sourceStats.eleme }}</div>
      <div class="stat-sub">饿了么 · 饿百 · 占比 {{ sourceStats.elemeRatio }}%</div>
    </el-card>
    <el-card class="stat-card source member" shadow="hover">
      <div class="stat-label">会员单汇总</div>
      <div class="stat-value">{{ memberStats.member }}</div>
      <div class="stat-sub">会员号非空 · 占比 {{ memberStats.ratio }}%</div>
    </el-card>
    <el-card class="stat-card source non-member" shadow="hover">
      <div class="stat-label">非会员单量</div>
      <div class="stat-value">{{ nonMemberStats.count }}</div>
      <div class="stat-sub">非会员 · 非美团 · 非饿了么 · 占比 {{ nonMemberStats.ratio }}%</div>
    </el-card>
    <el-card class="stat-card source xiaocan" shadow="hover">
      <div class="stat-label">小蚕订单总量</div>
      <div class="stat-value">{{ xiaocanStats.count }}</div>
      <div class="stat-sub">已匹配原订单 · 占比 {{ xiaocanStats.ratio }}%</div>
    </el-card>
    <el-card class="stat-card source natural" shadow="hover">
      <div class="stat-label">自然流线上订单</div>
      <div class="stat-value">{{ naturalOnlineStats.count }}</div>
      <div class="stat-sub">美团+饿了么-小蚕 · 自然流占比 {{ naturalOnlineStats.ratio }}%</div>
    </el-card>
    <el-card class="stat-card source core-ratio" shadow="hover">
      <div class="stat-label">核心渠道订单占比</div>
      <div class="stat-value">{{ coreChannelStats.ratio }}%</div>
      <div class="stat-sub">自然流线上 / 小蚕订单 · {{ coreChannelStats.detail }}</div>
    </el-card>
    <el-card class="stat-card source xiaocan-rebate" shadow="hover">
      <div class="stat-label">小蚕订单返现总额度</div>
      <div class="stat-value">¥{{ formatAmount(stats.xiaocan_rebate_total) }}</div>
      <div class="stat-sub">每日返现结算累计</div>
    </el-card>
    <el-card class="stat-card source actual-received" shadow="hover">
      <div class="stat-label">确收金额</div>
      <div class="stat-value">¥{{ formatAmount(stats.actual_received) }}</div>
      <div class="stat-sub">总金额 - 小蚕返现总额度</div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Stats } from '../api'

const props = defineProps<{ stats: Stats; loading?: boolean }>()

function formatNum(v: number | null | undefined): string {
  if (v === null || v === undefined) return '0'
  return Number(v).toLocaleString('zh-CN')
}
function formatAmount(v: number | null | undefined): string {
  if (v === null || v === undefined) return '0.00'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const latestText = computed(() => {
  const s = props.stats.latest_import_at
  if (!s) return '尚未导入'
  const d = new Date(s)
  return `最近导入 ${d.toLocaleString('zh-CN')}`
})

const sourceStats = computed(() => {
  const breakdown = props.stats.source_breakdown || {}
  const total = props.stats.orders_count || 0
  let meituan = 0
  let eleme = 0
  for (const [source, count] of Object.entries(breakdown)) {
    if (source.includes('美团')) {
      meituan += count
    } else if (source.includes('饿了么') || source.includes('饿百')) {
      eleme += count
    }
  }
  const meituanRatio = total > 0 ? ((meituan / total) * 100).toFixed(1) : '0.0'
  const elemeRatio = total > 0 ? ((eleme / total) * 100).toFixed(1) : '0.0'
  return { meituan, eleme, meituanRatio, elemeRatio }
})

const memberStats = computed(() => {
  const total = props.stats.orders_count || 0
  const member = props.stats.member_orders_count || 0
  const ratio = total > 0 ? ((member / total) * 100).toFixed(1) : '0.0'
  return { member, ratio }
})

const nonMemberStats = computed(() => {
  const total = props.stats.orders_count || 0
  const count = props.stats.non_member_orders_count || 0
  const ratio = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0'
  return { count, ratio }
})

const xiaocanStats = computed(() => {
  const total = props.stats.orders_count || 0
  const count = props.stats.xiaocan_orders_count || 0
  const ratio = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0'
  return { count, ratio }
})

const naturalOnlineStats = computed(() => {
  const count = props.stats.natural_online_orders || 0
  const total = props.stats.orders_count || 0
  const ratio = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0'
  return { count, ratio }
})

const coreChannelStats = computed(() => {
  const natural = props.stats.natural_online_orders || 0
  const xiaocan = props.stats.xiaocan_orders_count || 0
  const ratio = xiaocan > 0 ? ((natural / xiaocan) * 100).toFixed(1) : '0.0'
  return { ratio, detail: `${natural}/${xiaocan}` }
})
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 18px;
}
.stat-card {
  border-radius: 10px;
  border: none;
}
.stat-card.orders {
  background: linear-gradient(135deg, #2c9e9e 0%, #1a6868 100%);
  color: #fff;
}
.stat-card.orders :deep(.el-card__body) {
  color: #fff;
}
.stat-card.accent {
  background: linear-gradient(135deg, #6b4226 0%, #a3683f 100%);
  color: #fff;
}
.stat-card.accent :deep(.el-card__body) {
  color: #fff;
}
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}
.stat-card.accent .stat-label {
  color: rgba(255, 255, 255, 0.85);
}
.stat-card.orders .stat-label {
  color: rgba(255, 255, 255, 0.85);
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}
.stat-sub {
  font-size: 12px;
  color: #b0b4bb;
  margin-top: 6px;
}
.stat-card.accent .stat-sub {
  color: rgba(255, 255, 255, 0.7);
}
.stat-card.orders .stat-sub {
  color: rgba(255, 255, 255, 0.7);
}
.source-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 18px;
}
.source.meituan {
  background: linear-gradient(135deg, #ffc300 0%, #ff8c00 100%);
  color: #fff;
}
.source.eleme {
  background: linear-gradient(135deg, #0097ff 0%, #0070e0 100%);
  color: #fff;
}
.source.member {
  background: linear-gradient(135deg, #c9a14a 0%, #8a6a1f 100%);
  color: #fff;
}
.source.non-member {
  background: linear-gradient(135deg, #8a7a6b 0%, #5d4f42 100%);
  color: #fff;
}
.source.xiaocan {
  background: linear-gradient(135deg, #5cb85c 0%, #3d8b3d 100%);
  color: #fff;
}
.source.natural {
  background: linear-gradient(135deg, #5b6cb8 0%, #3a4a8a 100%);
  color: #fff;
}
.source.core-ratio {
  background: linear-gradient(135deg, #c0392b 0%, #8e2420 100%);
  color: #fff;
}
.source.xiaocan-rebate {
  background: linear-gradient(135deg, #8e44ad 0%, #5e2b73 100%);
  color: #fff;
}
.source.actual-received {
  background: linear-gradient(135deg, #16a085 0%, #0e6e5c 100%);
  color: #fff;
}
.source .stat-label {
  color: rgba(255, 255, 255, 0.9);
}
.source .stat-sub {
  color: rgba(255, 255, 255, 0.75);
}
@media (max-width: 1100px) {
  .source-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .source-grid {
    grid-template-columns: 1fr;
  }
}
</style>
