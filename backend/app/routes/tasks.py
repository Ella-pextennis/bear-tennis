"""GET /api/tasks/{task_id} - Async task status polling."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import TaskResult
from ..services.tasks import get_task

router = APIRouter()


@router.get("/tasks/{task_id}", response_model=TaskResult, tags=["tasks"])
def get_task_status(task_id: str) -> TaskResult:
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskResult(
        task_id=task.task_id,
        status=task.status.value,
        message=task.message,
        progress=task.progress,
        result=task.result,
        error=task.error,
    )