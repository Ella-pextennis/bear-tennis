"""Xiaocan (小蚕) orders + rebate settlements endpoints."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from ..db import get_conn
from ..models import (
    BatchDeleteRequest,
    DeleteResult,
    XiaocanImportResult,
    XiaocanOrderRow,
    XiaocanOrdersPage,
    XiaocanRebateCreateReq,
    XiaocanRebateItem,
    XiaocanRebateList,
)
from ..models import TaskResult
from ..services.tasks import submit_xiaocan_import
from ..services.xiaocan_importer import import_xiaocan_excel, update_xiaocan_marks

router = APIRouter()


def _to_xiaocan_row(row: tuple) -> XiaocanOrderRow:
    return XiaocanOrderRow(
        id=row[0],
        xiaocan_order_no=row[1],
        platform=row[2],
        order_time=row[3],
        platform_order_no=row[4],
        settlement_amount=_dec(row[5]),
        imported_at=row[6],
    )


def _dec(v) -> Optional[Decimal]:
    if v is None:
        return None
    return Decimal(str(v))


@router.post("/xiaocan/upload", response_model=TaskResult, tags=["xiaocan"])
async def upload_xiaocan_excel(file: UploadFile = File(...)) -> TaskResult:
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xlsm 文件")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")

    task_id = submit_xiaocan_import(data)
    return TaskResult(task_id=task_id, status="pending", message="任务已提交，请轮询获取进度")


@router.get("/xiaocan/orders", response_model=XiaocanOrdersPage, tags=["xiaocan"])
def list_xiaocan_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    platform: Optional[str] = Query(None),
    matched: Optional[bool] = Query(None, description="true=仅匹配上的，false=仅未匹配的"),
    order_no: Optional[str] = Query(None, description="搜索小蚕订单编号或平台订单编号"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    sort: str = Query("order_time", pattern="^(order_time|settlement_amount|platform|xiaocan_order_no)$"),
    dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> XiaocanOrdersPage:
    filters = []
    params: dict[str, object] = {}
    if platform:
        filters.append("platform = %(platform)s")
        params["platform"] = platform.strip()
    if order_no:
        filters.append(
            "(xiaocan_order_no LIKE %(order_no)s OR platform_order_no LIKE %(order_no)s)"
        )
        params["order_no"] = f"%{order_no.strip()}%"
    if date_from:
        filters.append("order_time >= %(date_from)s")
        params["date_from"] = date_from.strip()
    if date_to:
        filters.append("order_time < DATE_ADD(%(date_to)s, INTERVAL 1 DAY)")
        params["date_to"] = date_to.strip()
    if matched is True:
        filters.append(
            "EXISTS (SELECT 1 FROM coffee_orders co WHERE co.platform_order_no = COALESCE(NULLIF(TRIM(xo.platform_order_no), ''), xo.xiaocan_order_no))"
        )
    elif matched is False:
        filters.append(
            "NOT EXISTS (SELECT 1 FROM coffee_orders co WHERE co.platform_order_no = COALESCE(NULLIF(TRIM(xo.platform_order_no), ''), xo.xiaocan_order_no))"
        )
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    direction = "ASC" if dir.lower() == "asc" else "DESC"
    offset = (page - 1) * size

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM xiaocan_orders xo {where}", params)
        total = cur.fetchone()[0]

        cur.execute(
            f"""
            SELECT id, xiaocan_order_no, platform, order_time, platform_order_no,
                   settlement_amount, imported_at
            FROM xiaocan_orders xo
            {where}
            ORDER BY {sort} IS NULL ASC, {sort} {direction}, id ASC
            LIMIT %(size)s OFFSET %(offset)s
            """,
            {**params, "offset": offset, "size": size},
        )
        rows = cur.fetchall()
        items = [_to_xiaocan_row(r) for r in rows]
        cur.close()
    finally:
        conn.close()

    return XiaocanOrdersPage(total=total, page=page, size=size, items=items)


@router.delete("/xiaocan/orders", response_model=DeleteResult, tags=["xiaocan"])
def delete_all_xiaocan_orders() -> DeleteResult:
    """Truncate xiaocan_orders and reset all coffee_orders.is_xiaocan to 0."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE xiaocan_orders")
        deleted_rows = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        cur.close()
        conn.commit()

        # Reset is_xiaocan marks
        cur = conn.cursor()
        cur.execute("UPDATE coffee_orders SET is_xiaocan = 0")
        cur.close()
        conn.commit()
    finally:
        conn.close()
    return DeleteResult(deleted=deleted_rows)


@router.post("/xiaocan/orders/delete-batch", response_model=DeleteResult, tags=["xiaocan"])
def delete_xiaocan_orders_batch(req: BatchDeleteRequest) -> DeleteResult:
    if not req.ids:
        return DeleteResult(deleted=0)
    conn = get_conn()
    try:
        cur = conn.cursor()
        placeholders = ",".join(["%s"] * len(req.ids))
        cur.execute(f"DELETE FROM xiaocan_orders WHERE id IN ({placeholders})", list(req.ids))
        deleted = cur.rowcount
        cur.close()
        conn.commit()

        # Refresh marks after partial deletion
        update_xiaocan_marks(conn)
        conn.commit()
    finally:
        conn.close()
    return DeleteResult(deleted=deleted)


@router.get("/xiaocan/rebates", response_model=XiaocanRebateList, tags=["xiaocan"])
def list_xiaocan_rebates() -> XiaocanRebateList:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
        """
            SELECT id, settle_date, amount, remark, created_at
            FROM xiaocan_rebate_settlements
            ORDER BY settle_date DESC, id DESC
        """
        )
        rows = cur.fetchall()
        items = [
            XiaocanRebateItem(
                id=r[0],
                settle_date=r[1],
                amount=Decimal(str(r[2])),
                remark=r[3],
                created_at=r[4],
            )
            for r in rows
        ]
        cur.execute("SELECT IFNULL(SUM(amount), 0) FROM xiaocan_rebate_settlements")
        total_amount_raw = cur.fetchone()[0]
        total_amount = Decimal(str(total_amount_raw)) if total_amount_raw else Decimal("0")
        cur.close()
    finally:
        conn.close()
    return XiaocanRebateList(
        items=items,
        total=len(items),
        total_amount=total_amount if total_amount > 0 else None,
    )


@router.post("/xiaocan/rebates", response_model=XiaocanRebateItem, tags=["xiaocan"])
def create_xiaocan_rebate(req: XiaocanRebateCreateReq) -> XiaocanRebateItem:
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="结算金额必须大于 0")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO xiaocan_rebate_settlements (settle_date, amount, remark)
            VALUES (%(settle_date)s, %(amount)s, %(remark)s)
            """,
            {
                "settle_date": req.settle_date,
                "amount": req.amount,
                "remark": req.remark,
            },
        )
        new_id = cur.lastrowid
        cur.close()
        conn.commit()

        cur = conn.cursor()
        cur.execute(
            "SELECT id, settle_date, amount, remark, created_at FROM xiaocan_rebate_settlements WHERE id = %s",
            (new_id,),
        )
        r = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    return XiaocanRebateItem(
        id=r[0],
        settle_date=r[1],
        amount=Decimal(str(r[2])),
        remark=r[3],
        created_at=r[4],
    )


@router.put("/xiaocan/rebates/{rebate_id}", response_model=XiaocanRebateItem, tags=["xiaocan"])
def update_xiaocan_rebate(rebate_id: int, req: XiaocanRebateCreateReq) -> XiaocanRebateItem:
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="结算金额必须大于 0")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE xiaocan_rebate_settlements
            SET settle_date = %(settle_date)s, amount = %(amount)s, remark = %(remark)s
            WHERE id = %(rebate_id)s
            """,
            {
                "rebate_id": rebate_id,
                "settle_date": req.settle_date,
                "amount": req.amount,
                "remark": req.remark,
            },
        )
        if cur.rowcount == 0:
            cur.close()
            raise HTTPException(status_code=404, detail="记录不存在")
        cur.close()
        conn.commit()

        cur = conn.cursor()
        cur.execute(
            "SELECT id, settle_date, amount, remark, created_at FROM xiaocan_rebate_settlements WHERE id = %s",
            (rebate_id,),
        )
        r = cur.fetchone()
        cur.close()
    finally:
        conn.close()
    return XiaocanRebateItem(
        id=r[0],
        settle_date=r[1],
        amount=Decimal(str(r[2])),
        remark=r[3],
        created_at=r[4],
    )


@router.delete("/xiaocan/rebates/{rebate_id}", response_model=DeleteResult, tags=["xiaocan"])
def delete_xiaocan_rebate(rebate_id: int) -> DeleteResult:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM xiaocan_rebate_settlements WHERE id = %s", (rebate_id,))
        deleted = cur.rowcount
        cur.close()
        conn.commit()
    finally:
        conn.close()
    return DeleteResult(deleted=deleted)


@router.delete("/xiaocan/rebates", response_model=DeleteResult, tags=["xiaocan"])
def delete_all_xiaocan_rebates() -> DeleteResult:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE xiaocan_rebate_settlements")
        deleted = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        cur.close()
        conn.commit()
    finally:
        conn.close()
    return DeleteResult(deleted=deleted)
