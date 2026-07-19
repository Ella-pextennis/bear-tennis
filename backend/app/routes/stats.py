"""GET /api/orders/stats - dashboard summary with caching."""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Optional

from fastapi import APIRouter, Query

from ..db import get_conn
from ..models import ActualReceivedTrend, ActualReceivedTrendItem, DailyTrend, DailyTrendItem, DashboardData, NaturalTrend, NaturalTrendItem, Stats
from ..services.cache import get_cache, invalidate_cache, set_cache

router = APIRouter()


def _compute_stats() -> Stats:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              COUNT(*),
              COUNT(DISTINCT order_no),
              IFNULL(SUM(CASE WHEN is_order_header = 1 THEN amount END), 0),
              COUNT(DISTINCT store_name),
              MAX(imported_at)
            FROM coffee_orders
            """
        )
        row = cur.fetchone()

        cur.execute(
            """
            SELECT order_source, COUNT(DISTINCT order_no)
            FROM coffee_orders
            WHERE is_order_header = 1 AND order_source IS NOT NULL
            GROUP BY order_source
            """
        )
        source_breakdown: dict[str, int] = {}
        for src, cnt in cur.fetchall():
            src = src or "未知"
            source_breakdown[src] = source_breakdown.get(src, 0) + (cnt or 0)

        cur.execute(
            """
            SELECT COUNT(DISTINCT order_no)
            FROM coffee_orders
            WHERE is_order_header = 1
              AND member_no IS NOT NULL
              AND TRIM(member_no) != ''
            """
        )
        member_orders_count = cur.fetchone()[0] or 0

        cur.execute(
            """
            SELECT COUNT(DISTINCT order_no)
            FROM coffee_orders
            WHERE is_order_header = 1
              AND (member_no IS NULL OR TRIM(member_no) = '')
              AND (
                order_source IS NULL
                OR (
                  order_source NOT LIKE %(meituan)s
                  AND order_source NOT LIKE %(eleme1)s
                  AND order_source NOT LIKE %(eleme2)s
                )
              )
            """,
            {"meituan": "%美团%", "eleme1": "%饿了么%", "eleme2": "%饿百%"},
        )
        non_member_orders_count = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM xiaocan_orders")
        xiaocan_orders_count = cur.fetchone()[0] or 0

        meituan_count = sum(
            cnt for src, cnt in source_breakdown.items() if "美团" in src
        )
        eleme_count = sum(
            cnt for src, cnt in source_breakdown.items()
            if "饿了么" in src or "饿百" in src
        )
        natural_online_orders = meituan_count + eleme_count - xiaocan_orders_count

        cur.execute("SELECT IFNULL(SUM(amount), 0) FROM xiaocan_rebate_settlements")
        rebate_total_raw = cur.fetchone()[0]
        xiaocan_rebate_total = (
            Decimal(str(rebate_total_raw)) if rebate_total_raw not in (None, 0) else None
        )

        cur.close()
    finally:
        conn.close()

    if not row:
        return Stats(total_rows=0, orders_count=0, total_amount=None, stores_count=0, latest_import_at=None)

    total_rows, orders_count, total_amount, stores_count, latest = row
    total_amount_dec = Decimal(str(total_amount)) if total_amount not in (None, 0) else None
    actual_received = None
    if total_amount_dec is not None:
        rebate_val = xiaocan_rebate_total or Decimal("0")
        actual_received = total_amount_dec - rebate_val
        if actual_received <= Decimal("0"):
            actual_received = None

    return Stats(
        total_rows=total_rows or 0,
        orders_count=orders_count or 0,
        total_amount=total_amount_dec,
        stores_count=stores_count or 0,
        latest_import_at=latest if isinstance(latest, datetime) else None,
        source_breakdown=source_breakdown,
        member_orders_count=member_orders_count,
        non_member_orders_count=non_member_orders_count,
        xiaocan_orders_count=xiaocan_orders_count,
        xiaocan_rebate_total=xiaocan_rebate_total,
        natural_online_orders=natural_online_orders,
        actual_received=actual_received,
    )


@router.get("/orders/stats", response_model=Stats)
def get_stats() -> Stats:
    cached = get_cache("stats")
    if cached:
        return cached
    result = _compute_stats()
    set_cache("stats", result)
    return result


def _classify_source(source: str) -> str:
    """Return 'meituan', 'eleme', or 'other' for a given order source string."""
    if not source:
        return "other"
    if "美团" in source:
        return "meituan"
    if "饿了么" in source or "饿百" in source:
        return "eleme"
    return "other"


@router.get("/orders/stats/daily-trend", response_model=DailyTrend, tags=["stats"])
def get_daily_trend(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
) -> DailyTrend:
    """Daily order counts split by channel bucket (meituan / eleme / other).

    Only order-header rows (is_order_header=1) with non-null order_date and
    order_source are counted. Dates are returned in ascending order.
    """
    cache_key = f"daily_trend_{date_from}_{date_to}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    filters = ["is_order_header = 1", "order_date IS NOT NULL", "order_source IS NOT NULL"]
    params: dict[str, object] = {}
    if date_from:
        filters.append("order_date >= %(date_from)s")
        params["date_from"] = date_from
    if date_to:
        filters.append("order_date < DATE_ADD(%(date_to)s, INTERVAL 1 DAY)")
        params["date_to"] = date_to
    where = "WHERE " + " AND ".join(filters)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT DATE(order_date), order_source, COUNT(DISTINCT order_no)
            FROM coffee_orders
            {where}
            GROUP BY DATE(order_date), order_source
            ORDER BY DATE(order_date) ASC
            """,
            params,
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    by_date: Dict[str, DailyTrendItem] = {}
    for raw_date, src, cnt in rows:
        if raw_date is None:
            continue
        if isinstance(raw_date, datetime):
            date_str = raw_date.strftime("%Y-%m-%d")
        elif isinstance(raw_date, date):
            date_str = raw_date.strftime("%Y-%m-%d")
        else:
            date_str = str(raw_date)[:10]

        item = by_date.get(date_str)
        if item is None:
            item = DailyTrendItem(date=date_str)
            by_date[date_str] = item

        src_name = src or "未知"
        bucket = _classify_source(src_name)
        setattr(item, bucket, getattr(item, bucket) + (cnt or 0))
        item.detail[src_name] = item.detail.get(src_name, 0) + (cnt or 0)

    items = [by_date[k] for k in sorted(by_date.keys())]
    result = DailyTrend(items=items)
    set_cache(cache_key, result)
    return result


@router.get("/orders/stats/natural-trend", response_model=NaturalTrend, tags=["stats"])
def get_natural_trend(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
) -> NaturalTrend:
    """Daily natural online order counts.

    natural = meituan + eleme - xiaocan (per day).
    Meituan/eleme from coffee_orders, xiaocan from xiaocan_orders.
    """
    cache_key = f"natural_trend_{date_from}_{date_to}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    filters = ["is_order_header = 1", "order_date IS NOT NULL", "order_source IS NOT NULL"]
    params: dict[str, object] = {}
    if date_from:
        filters.append("order_date >= %(date_from)s")
        params["date_from"] = date_from
    if date_to:
        filters.append("order_date < DATE_ADD(%(date_to)s, INTERVAL 1 DAY)")
        params["date_to"] = date_to
    where = "WHERE " + " AND ".join(filters)

    xiaocan_params = {}
    xiaocan_filters = ["order_time IS NOT NULL"]
    if date_from:
        xiaocan_filters.append("order_time >= %(date_from)s")
        xiaocan_params["date_from"] = date_from
    if date_to:
        xiaocan_filters.append("order_time < DATE_ADD(%(date_to)s, INTERVAL 1 DAY)")
        xiaocan_params["date_to"] = date_to
    xiaocan_where = "WHERE " + " AND ".join(xiaocan_filters)

    conn = get_conn()
    try:
        cur = conn.cursor()

        cur.execute(
            f"""
            SELECT DATE(order_date), order_source, COUNT(DISTINCT order_no)
            FROM coffee_orders
            {where}
            GROUP BY DATE(order_date), order_source
            ORDER BY DATE(order_date) ASC
            """,
            params,
        )
        coffee_rows = cur.fetchall()

        cur.execute(
            f"""
            SELECT DATE(order_time), COUNT(*)
            FROM xiaocan_orders
            {xiaocan_where}
            GROUP BY DATE(order_time)
            ORDER BY DATE(order_time) ASC
            """,
            xiaocan_params,
        )
        xiaocan_rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    by_date: Dict[str, NaturalTrendItem] = {}

    for raw_date, src, cnt in coffee_rows:
        if raw_date is None:
            continue
        if isinstance(raw_date, datetime):
            date_str = raw_date.strftime("%Y-%m-%d")
        elif isinstance(raw_date, date):
            date_str = raw_date.strftime("%Y-%m-%d")
        else:
            date_str = str(raw_date)[:10]

        item = by_date.get(date_str)
        if item is None:
            item = NaturalTrendItem(date=date_str)
            by_date[date_str] = item

        src_name = src or ""
        bucket = _classify_source(src_name)
        if bucket == "meituan":
            item.meituan += cnt or 0
        elif bucket == "eleme":
            item.eleme += cnt or 0

    for raw_date, cnt in xiaocan_rows:
        if raw_date is None:
            continue
        if isinstance(raw_date, datetime):
            date_str = raw_date.strftime("%Y-%m-%d")
        elif isinstance(raw_date, date):
            date_str = raw_date.strftime("%Y-%m-%d")
        else:
            date_str = str(raw_date)[:10]

        item = by_date.get(date_str)
        if item is None:
            item = NaturalTrendItem(date=date_str)
            by_date[date_str] = item
        item.xiaocan += cnt or 0

    for item in by_date.values():
        item.natural = item.meituan + item.eleme - item.xiaocan

    items = [by_date[k] for k in sorted(by_date.keys())]
    result = NaturalTrend(items=items)
    set_cache(cache_key, result)
    return result


@router.get("/orders/stats/actual-received-trend", response_model=ActualReceivedTrend, tags=["stats"])
def get_actual_received_trend(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
) -> ActualReceivedTrend:
    """Daily actual received amount trend.

    actual_received = total_amount - rebate_amount (per day).
    Total amount from coffee_orders order headers, rebate from xiaocan_rebate_settlements.
    """
    cache_key = f"actual_received_trend_{date_from}_{date_to}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    filters = ["is_order_header = 1", "order_date IS NOT NULL"]
    params: dict[str, object] = {}
    if date_from:
        filters.append("order_date >= %(date_from)s")
        params["date_from"] = date_from
    if date_to:
        filters.append("order_date < DATE_ADD(%(date_to)s, INTERVAL 1 DAY)")
        params["date_to"] = date_to
    where = "WHERE " + " AND ".join(filters)

    rebate_params = {}
    rebate_filters = ["settle_date IS NOT NULL"]
    if date_from:
        rebate_filters.append("settle_date >= %(date_from)s")
        rebate_params["date_from"] = date_from
    if date_to:
        rebate_filters.append("settle_date <= %(date_to)s")
        rebate_params["date_to"] = date_to
    rebate_where = "WHERE " + " AND ".join(rebate_filters)

    conn = get_conn()
    try:
        cur = conn.cursor()

        cur.execute(
            f"""
            SELECT DATE(order_date), IFNULL(SUM(amount), 0)
            FROM coffee_orders
            {where}
            GROUP BY DATE(order_date)
            ORDER BY DATE(order_date) ASC
            """,
            params,
        )
        coffee_rows = cur.fetchall()

        cur.execute(
            f"""
            SELECT settle_date, IFNULL(SUM(amount), 0)
            FROM xiaocan_rebate_settlements
            {rebate_where}
            GROUP BY settle_date
            ORDER BY settle_date ASC
            """,
            rebate_params,
        )
        rebate_rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    by_date: Dict[str, ActualReceivedTrendItem] = {}

    for raw_date, amt in coffee_rows:
        if raw_date is None:
            continue
        if isinstance(raw_date, datetime):
            date_str = raw_date.strftime("%Y-%m-%d")
        elif isinstance(raw_date, date):
            date_str = raw_date.strftime("%Y-%m-%d")
        else:
            date_str = str(raw_date)[:10]

        item = by_date.get(date_str)
        if item is None:
            item = ActualReceivedTrendItem(date=date_str)
            by_date[date_str] = item
        item.total_amount += Decimal(str(amt)) if amt else Decimal("0")

    for raw_date, amt in rebate_rows:
        if raw_date is None:
            continue
        if isinstance(raw_date, datetime):
            date_str = raw_date.strftime("%Y-%m-%d")
        elif isinstance(raw_date, date):
            date_str = raw_date.strftime("%Y-%m-%d")
        else:
            date_str = str(raw_date)[:10]

        item = by_date.get(date_str)
        if item is None:
            item = ActualReceivedTrendItem(date=date_str)
            by_date[date_str] = item
        item.rebate_amount += Decimal(str(amt)) if amt else Decimal("0")

    for item in by_date.values():
        item.actual_received = item.total_amount - item.rebate_amount

    items = [by_date[k] for k in sorted(by_date.keys())]
    result = ActualReceivedTrend(items=items)
    set_cache(cache_key, result)
    return result


@router.get("/orders/dashboard", response_model=DashboardData, tags=["stats"])
def get_dashboard(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
) -> DashboardData:
    """Combined dashboard data - reduces multiple API calls to one."""
    cache_key = f"dashboard_{date_from}_{date_to}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    stats = _compute_stats()
    daily_trend = get_daily_trend(date_from, date_to)
    natural_trend = get_natural_trend(date_from, date_to)
    actual_received_trend = get_actual_received_trend(date_from, date_to)

    result = DashboardData(
        stats=stats,
        daily_trend=daily_trend,
        natural_trend=natural_trend,
        actual_received_trend=actual_received_trend,
    )
    set_cache(cache_key, result)
    return result
