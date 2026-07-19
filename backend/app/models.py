"""Pydantic models for API request/response contracts."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ImportResult(BaseModel):
    total_rows: int = Field(..., description="Total data rows imported (excluding header)")
    orders_count: int = Field(..., description="Distinct order count")
    total_amount: Optional[Decimal] = Field(None, description="Sum of order-header amounts")
    stores_count: int = Field(0, description="Distinct store count")
    skipped_empty_rows: int = 0
    truncated: bool = Field(..., description="Whether existing data was truncated before insert")
    errors: List[str] = Field(default_factory=list)


class OrderRow(BaseModel):
    id: int
    order_no: Optional[str] = None
    order_date: Optional[datetime] = None
    store_name: Optional[str] = None
    queue_no: Optional[str] = None
    order_source: Optional[str] = None
    delivery_method: Optional[str] = None
    status: Optional[str] = None
    payment_method: Optional[str] = None
    member_no: Optional[str] = None
    customer_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    product_name: Optional[str] = None
    flavor_group: Optional[str] = None
    unit_price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    remark: Optional[str] = None
    logistics_no: Optional[str] = None
    weight: Optional[str] = None
    is_order_header: int = 0
    imported_at: Optional[datetime] = None
    platform_order_no: Optional[str] = None
    discount_amount: Optional[Decimal] = None
    is_xiaocan: int = 0
    updated_at: Optional[datetime] = None


class OrdersPage(BaseModel):
    total: int
    page: int
    size: int
    items: List[OrderRow]


class Stats(BaseModel):
    total_rows: int
    orders_count: int
    total_amount: Optional[Decimal] = None
    stores_count: int
    latest_import_at: Optional[datetime] = None
    source_breakdown: Dict[str, int] = Field(default_factory=dict, description="订单来源 -> 订单数（仅订单头）")
    member_orders_count: int = Field(0, description="会员单数（member_no 非空非空白）")
    non_member_orders_count: int = Field(0, description="非会员单量：会员号为空且订单来源不含美团/饿了么/饿百")
    xiaocan_orders_count: int = Field(0, description="小蚕订单总量：coffee_orders 中 is_xiaocan=1 的订单头数")
    xiaocan_rebate_total: Optional[Decimal] = Field(None, description="小蚕返现总额度：SUM(amount) FROM xiaocan_rebate_settlements")
    natural_online_orders: int = Field(0, description="自然流线上订单 = 美团 + 饿了么 - 小蚕订单总量")
    actual_received: Optional[Decimal] = Field(None, description="确收金额 = 总金额 - 小蚕订单返现总额度")


class HealthCheck(BaseModel):
    status: str
    db: str


class BatchDeleteRequest(BaseModel):
    ids: List[int] = Field(default_factory=list, description="Row IDs to delete")


class DeleteResult(BaseModel):
    deleted: int = 0


class DailyTrendItem(BaseModel):
    date: str = Field(..., description="日期 YYYY-MM-DD")
    meituan: int = 0
    eleme: int = 0
    other: int = 0
    detail: Dict[str, int] = Field(default_factory=dict, description="原始渠道名 -> 订单数")


class DailyTrend(BaseModel):
    items: List[DailyTrendItem] = Field(default_factory=list)


class NaturalTrendItem(BaseModel):
    date: str = Field(..., description="日期 YYYY-MM-DD")
    meituan: int = 0
    eleme: int = 0
    xiaocan: int = 0
    natural: int = 0


class NaturalTrend(BaseModel):
    items: List[NaturalTrendItem] = Field(default_factory=list)


class ActualReceivedTrendItem(BaseModel):
    date: str = Field(..., description="日期 YYYY-MM-DD")
    total_amount: Decimal = Field(0, description="当日总金额")
    rebate_amount: Decimal = Field(0, description="当日小蚕返现金额")
    actual_received: Decimal = Field(0, description="当日确收金额 = 总金额 - 返现金额")


class ActualReceivedTrend(BaseModel):
    items: List[ActualReceivedTrendItem] = Field(default_factory=list)


class XiaocanOrderRow(BaseModel):
    id: int
    xiaocan_order_no: Optional[str] = None
    platform: Optional[str] = None
    order_time: Optional[datetime] = None
    platform_order_no: Optional[str] = None
    settlement_amount: Optional[Decimal] = None
    imported_at: Optional[datetime] = None


class XiaocanOrdersPage(BaseModel):
    total: int
    page: int
    size: int
    items: List[XiaocanOrderRow]


class XiaocanImportResult(BaseModel):
    total_rows: int = Field(0, description="导入的小蚕订单总行数")
    matched_count: int = Field(0, description="平台订单编号与原订单匹配上的订单数")
    unmatched_count: int = Field(0, description="未匹配上的小蚕订单数")
    truncated: bool = Field(True, description="是否清空了旧数据")


class XiaocanRebateItem(BaseModel):
    id: int
    settle_date: date
    amount: Decimal
    remark: Optional[str] = None
    created_at: Optional[datetime] = None


class XiaocanRebateCreateReq(BaseModel):
    settle_date: date
    amount: Decimal
    remark: Optional[str] = None


class XiaocanRebateList(BaseModel):
    items: List[XiaocanRebateItem] = Field(default_factory=list)
    total: int = 0
    total_amount: Optional[Decimal] = None


class TaskResult(BaseModel):
    task_id: str
    status: str
    message: str = ""
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


TaskResult.model_rebuild()


class DashboardData(BaseModel):
    stats: Stats
    daily_trend: DailyTrend
    natural_trend: NaturalTrend
    actual_received_trend: ActualReceivedTrend
