"""GET /api/orders - paginated, filterable, sortable order rows."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..db import get_conn
from ..models import BatchDeleteRequest, DeleteResult, OrderRow, OrdersPage

router = APIRouter()

ALLOWED_SORT = {
    "order_date": "order_date",
    "amount": "amount",
    "unit_price": "unit_price",
    "quantity": "quantity",
    "store_name": "store_name",
    "order_no": "order_no",
    "platform_order_no": "platform_order_no",
    "discount_amount": "discount_amount",
    "is_xiaocan": "is_xiaocan",
    "updated_at": "updated_at",
}


def _to_order_row(row: tuple) -> OrderRow:
    return OrderRow(
        id=row[0],
        order_no=row[1],
        order_date=row[2],
        store_name=row[3],
        queue_no=row[4],
        order_source=row[5],
        delivery_method=row[6],
        status=row[7],
        payment_method=row[8],
        member_no=row[9],
        customer_name=row[10],
        phone=row[11],
        address=row[12],
        product_name=row[13],
        flavor_group=row[14],
        unit_price=_dec(row[15]),
        quantity=_dec(row[16]),
        amount=_dec(row[17]),
        remark=row[18],
        logistics_no=row[19],
        weight=row[20],
        is_order_header=row[21],
        imported_at=row[22],
        platform_order_no=row[23] if len(row) > 23 else None,
        discount_amount=_dec(row[24]) if len(row) > 24 else None,
        is_xiaocan=row[25] if len(row) > 25 else 0,
        updated_at=row[26] if len(row) > 26 else None,
    )


def _dec(v) -> Optional[Decimal]:
    if v is None:
        return None
    return Decimal(str(v))


@router.get("/orders/filters", tags=["orders"])
def list_filter_options() -> dict:
    """Distinct values for dropdown filters."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT store_name FROM coffee_orders
            WHERE store_name IS NOT NULL
            GROUP BY store_name ORDER BY store_name
            """
        )
        stores = [r[0] for r in cur.fetchall()]
        cur.execute(
            """
            SELECT order_source FROM coffee_orders
            WHERE order_source IS NOT NULL
            GROUP BY order_source ORDER BY order_source
            """
        )
        sources = [r[0] for r in cur.fetchall()]
        cur.execute(
            """
            SELECT status FROM coffee_orders
            WHERE status IS NOT NULL
            GROUP BY status ORDER BY status
            """
        )
        statuses = [r[0] for r in cur.fetchall()]
        cur.close()
    finally:
        conn.close()
    return {"stores": stores, "sources": sources, "statuses": statuses}


@router.delete("/orders", response_model=DeleteResult, tags=["orders"])
def delete_all_orders() -> DeleteResult:
    """Delete every row in coffee_orders (full wipe)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM coffee_orders")
        deleted = cur.rowcount
        cur.close()
        conn.commit()
    finally:
        conn.close()
    return DeleteResult(deleted=deleted)


@router.post("/orders/delete-batch", response_model=DeleteResult, tags=["orders"])
def delete_orders_batch(req: BatchDeleteRequest) -> DeleteResult:
    """Delete orders by a list of header row IDs, cascading to detail rows by order_no."""
    if not req.ids:
        return DeleteResult(deleted=0)
    conn = get_conn()
    try:
        cur = conn.cursor()
        placeholders = ",".join(["%s"] * len(req.ids))
        cur.execute(
            f"SELECT DISTINCT order_no FROM coffee_orders WHERE id IN ({placeholders})",
            list(req.ids),
        )
        order_nos = [r[0] for r in cur.fetchall() if r[0]]
        if not order_nos:
            cur.close()
            return DeleteResult(deleted=0)
        no_placeholders = ",".join(["%s"] * len(order_nos))
        cur.execute(
            f"DELETE FROM coffee_orders WHERE order_no IN ({no_placeholders})",
            order_nos,
        )
        deleted = cur.rowcount
        cur.close()
        conn.commit()
    finally:
        conn.close()
    return DeleteResult(deleted=deleted)


@router.get("/orders", response_model=OrdersPage)
def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    order_no: Optional[str] = Query(None),
    platform_order_no: Optional[str] = Query(None),
    store: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    sort: str = Query("order_date", pattern="^(order_date|amount|unit_price|quantity|store_name|order_no|platform_order_no|discount_amount|is_xiaocan|updated_at)$"),
    dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> OrdersPage:
    if sort not in ALLOWED_SORT:
        raise HTTPException(status_code=400, detail=f"非法排序字段：{sort}")
    sort_col = ALLOWED_SORT[sort]
    direction = "ASC" if dir.lower() == "asc" else "DESC"

    filters = ["is_order_header = 1"]
    params: dict[str, object] = {}
    if order_no:
        filters.append("order_no LIKE %(order_no)s")
        params["order_no"] = f"%{order_no.strip()}%"
    if platform_order_no:
        filters.append("platform_order_no LIKE %(platform_order_no)s")
        params["platform_order_no"] = f"%{platform_order_no.strip()}%"
    if store:
        filters.append("store_name = %(store)s")
        params["store"] = store.strip()
    if source:
        filters.append("order_source = %(source)s")
        params["source"] = source.strip()
    if product:
        filters.append("UPPER(product_name) LIKE UPPER(%(product)s)")
        params["product"] = f"%{product.strip()}%"
    if status:
        filters.append("status = %(status)s")
        params["status"] = status.strip()
    if date_from:
        filters.append("order_date >= %(date_from)s")
        params["date_from"] = date_from.strip()
    if date_to:
        filters.append("order_date < DATE_ADD(%(date_to)s, INTERVAL 1 DAY)")
        params["date_to"] = date_to.strip()
    where = "WHERE " + " AND ".join(filters)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM coffee_orders {where}", params)
        total = cur.fetchone()[0]

        offset = (page - 1) * size
        # MySQL has no NULLS LAST syntax; emulate by sorting NULLs to the end
        # regardless of direction: `col IS NULL ASC` puts non-NULL (0) first.
        cur.execute(
            f"""
            SELECT id, order_no, order_date, store_name, queue_no, order_source,
                   delivery_method, status, payment_method, member_no, customer_name,
                   phone, address, product_name, flavor_group, unit_price, quantity,
                   amount, remark, logistics_no, weight, is_order_header, imported_at,
                   platform_order_no, discount_amount, is_xiaocan, updated_at
            FROM coffee_orders
            {where}
            ORDER BY {sort_col} IS NULL ASC, {sort_col} {direction}, id ASC
            LIMIT %(size)s OFFSET %(offset)s
            """,
            {**params, "offset": offset, "size": size},
        )
        rows = cur.fetchall()
        items = [_to_order_row(r) for r in rows]
        cur.close()
    finally:
        conn.close()

    return OrdersPage(total=total, page=page, size=size, items=items)
