"""POST /api/upload - Excel ingestion endpoint (async task)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from ..models import TaskResult
from ..services.tasks import submit_coffee_import

router = APIRouter()


@router.post("/upload", response_model=TaskResult)
async def upload_excel(request: Request, file: UploadFile = File(...)) -> TaskResult:
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

    task_id = submit_coffee_import(data)
    return TaskResult(task_id=task_id, status="pending", message="任务已提交，请轮询获取进度")
