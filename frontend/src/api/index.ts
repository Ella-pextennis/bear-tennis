import axios, { type AxiosInstance } from 'axios'

export interface OrderRow {
  id: number
  order_no: string | null
  order_date: string | null
  store_name: string | null
  queue_no: string | null
  order_source: string | null
  delivery_method: string | null
  status: string | null
  payment_method: string | null
  member_no: string | null
  customer_name: string | null
  phone: string | null
  address: string | null
  product_name: string | null
  flavor_group: string | null
  unit_price: number | null
  quantity: number | null
  amount: number | null
  remark: string | null
  logistics_no: string | null
  weight: string | null
  is_order_header: number
  imported_at: string | null
  platform_order_no: string | null
  discount_amount: number | null
  is_xiaocan: number
  updated_at: string | null
}

export interface OrdersPage {
  total: number
  page: number
  size: number
  items: OrderRow[]
}

export interface Stats {
  total_rows: number
  orders_count: number
  total_amount: number | null
  stores_count: number
  latest_import_at: string | null
  source_breakdown: Record<string, number>
  member_orders_count: number
  non_member_orders_count: number
  xiaocan_orders_count: number
  xiaocan_rebate_total: number | null
  natural_online_orders: number
  actual_received: number | null
}

export interface ImportResult {
  total_rows: number
  orders_count: number
  total_amount: number | null
  stores_count: number
  skipped_empty_rows: number
  truncated: boolean
  errors: string[]
}

export interface XiaocanOrderRow {
  id: number
  xiaocan_order_no: string | null
  platform: string | null
  order_time: string | null
  platform_order_no: string | null
  settlement_amount: number | null
  imported_at: string | null
}

export interface XiaocanOrdersPage {
  total: number
  page: number
  size: number
  items: XiaocanOrderRow[]
}

export interface XiaocanImportResult {
  total_rows: number
  matched_count: number
  unmatched_count: number
  truncated: boolean
}

export interface XiaocanRebateItem {
  id: number
  settle_date: string
  amount: number
  remark: string | null
  created_at: string | null
}

export interface XiaocanRebateCreateReq {
  settle_date: string
  amount: number
  remark?: string | null
}

export interface XiaocanRebateList {
  items: XiaocanRebateItem[]
  total: number
  total_amount: number | null
}

const client: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 120_000,
})

export async function uploadExcel(file: File, onProgress?: (pct: number) => void): Promise<TaskResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await client.post<TaskResult>('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return res.data
}

export async function fetchOrders(params: {
  page: number
  size: number
  order_no?: string
  platform_order_no?: string
  store?: string
  source?: string
  product?: string
  status?: string
  date_from?: string
  date_to?: string
  sort?: string
  dir?: 'asc' | 'desc'
}): Promise<OrdersPage> {
  const res = await client.get<OrdersPage>('/orders', { params })
  return res.data
}

export async function fetchStats(): Promise<Stats> {
  const res = await client.get<Stats>('/orders/stats')
  return res.data
}

export interface FilterOptions {
  stores: string[]
  sources: string[]
  statuses: string[]
}

export async function fetchFilters(): Promise<FilterOptions> {
  const res = await client.get<FilterOptions>('/orders/filters')
  return res.data
}

export async function fetchHealth(): Promise<{ status: string; db: string }> {
  const res = await client.get('/health')
  return res.data
}

export async function deleteAllOrders(): Promise<{ deleted: number }> {
  const res = await client.delete<{ deleted: number }>('/orders')
  return res.data
}

export async function deleteOrdersBatch(ids: number[]): Promise<{ deleted: number }> {
  const res = await client.post<{ deleted: number }>('/orders/delete-batch', { ids })
  return res.data
}

export interface DailyTrendItem {
  date: string
  meituan: number
  eleme: number
  other: number
  detail: Record<string, number>
}

export interface DailyTrend {
  items: DailyTrendItem[]
}

export async function fetchDailyTrend(): Promise<DailyTrend> {
  const res = await client.get<DailyTrend>('/orders/stats/daily-trend')
  return res.data
}

export interface NaturalTrendItem {
  date: string
  meituan: number
  eleme: number
  xiaocan: number
  natural: number
}

export interface NaturalTrend {
  items: NaturalTrendItem[]
}

export async function fetchNaturalTrend(): Promise<NaturalTrend> {
  const res = await client.get<NaturalTrend>('/orders/stats/natural-trend')
  return res.data
}

export interface ActualReceivedTrendItem {
  date: string
  total_amount: number
  rebate_amount: number
  actual_received: number
}

export interface ActualReceivedTrend {
  items: ActualReceivedTrendItem[]
}

export async function fetchActualReceivedTrend(): Promise<ActualReceivedTrend> {
  const res = await client.get<ActualReceivedTrend>('/orders/stats/actual-received-trend')
  return res.data
}

export async function uploadXiaocanExcel(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<TaskResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await client.post<TaskResult>('/xiaocan/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return res.data
}

export async function fetchXiaocanOrders(params: {
  page: number
  size: number
  platform?: string
  matched?: boolean
  order_no?: string
  date_from?: string
  date_to?: string
  sort?: string
  dir?: 'asc' | 'desc'
}): Promise<XiaocanOrdersPage> {
  const res = await client.get<XiaocanOrdersPage>('/xiaocan/orders', { params })
  return res.data
}

export async function deleteAllXiaocanOrders(): Promise<{ deleted: number }> {
  const res = await client.delete<{ deleted: number }>('/xiaocan/orders')
  return res.data
}

export async function deleteXiaocanOrdersBatch(ids: number[]): Promise<{ deleted: number }> {
  const res = await client.post<{ deleted: number }>('/xiaocan/orders/delete-batch', { ids })
  return res.data
}

export async function fetchXiaocanRebates(): Promise<XiaocanRebateList> {
  const res = await client.get<XiaocanRebateList>('/xiaocan/rebates')
  return res.data
}

export async function addXiaocanRebate(req: XiaocanRebateCreateReq): Promise<XiaocanRebateItem> {
  const res = await client.post<XiaocanRebateItem>('/xiaocan/rebates', req)
  return res.data
}

export async function updateXiaocanRebate(id: number, req: XiaocanRebateCreateReq): Promise<XiaocanRebateItem> {
  const res = await client.put<XiaocanRebateItem>(`/xiaocan/rebates/${id}`, req)
  return res.data
}

export async function deleteXiaocanRebate(id: number): Promise<{ deleted: number }> {
  const res = await client.delete<{ deleted: number }>(`/xiaocan/rebates/${id}`)
  return res.data
}

export async function deleteAllXiaocanRebates(): Promise<{ deleted: number }> {
  const res = await client.delete<{ deleted: number }>('/xiaocan/rebates')
  return res.data
}

export interface TaskResult {
  task_id: string
  status: string
  message: string
  progress: number
  result: Record<string, any> | null
  error: string | null
}

export async function fetchTaskStatus(taskId: string): Promise<TaskResult> {
  const res = await client.get<TaskResult>(`/tasks/${taskId}`)
  return res.data
}

export interface DashboardData {
  stats: Stats
  daily_trend: DailyTrend
  natural_trend: NaturalTrend
  actual_received_trend: ActualReceivedTrend
}

export async function fetchDashboard(date_from?: string, date_to?: string): Promise<DashboardData> {
  const res = await client.get<DashboardData>('/orders/dashboard', {
    params: { date_from, date_to },
  })
  return res.data
}
