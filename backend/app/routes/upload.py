"""POST /api/upload - Excel ingestion endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from ..db import get_conn
from ..models import ImportResult
from ..services.importer import import_excel
from ..services.xiaocan_importer import update_xiaocan_marks

router = APIRouter()


@router.post("/upload", response_model=ImportResult)
async def upload_excel(request: Request, file: UploadFile = File(...)) -> ImportResult:
    settings = request.app.state.settings
    max_bytes = settings.max_upload_mb * 1024 * 1024

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xlsm 文件")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大（{len(data) // 1024 // 1024}MB），上限 {settings.max_upload_mb}MB",
        )

    conn = get_conn()
    try:
        result = import_excel(conn, data)
        update_xiaocan_marks(conn)
        conn.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Excel 解析失败：{e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败：{e}")
    finally:
        conn.close()

    return result
