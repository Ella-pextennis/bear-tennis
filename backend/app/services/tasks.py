"""Async task management with thread pool.

Uploads are processed asynchronously to avoid HTTP timeout.
Frontend polls task status via /api/tasks/{task_id}.
"""
from __future__ import annotations

import asyncio
import io
import uuid
from dataclasses import dataclass, field
from enum import Enum
from threading import Thread
from typing import Any, Dict, Optional

from ..db import get_conn
from .cache import invalidate_cache
from .importer import import_excel
from .xiaocan_importer import import_xiaocan_excel, update_xiaocan_marks


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskInfo:
    task_id: str
    status: TaskStatus
    progress: float = 0.0
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0)


_tasks: Dict[str, TaskInfo] = {}


def _run_coffee_import(task_id: str, file_bytes: bytes) -> None:
    task = _tasks.get(task_id)
    if not task:
        return
    task.status = TaskStatus.RUNNING
    task.progress = 10.0
    task.message = "开始解析 Excel..."

    try:
        task.progress = 30.0
        task.message = "解析完成，开始导入数据库..."

        conn = get_conn()
        try:
            result = import_excel(conn, file_bytes)
            update_xiaocan_marks(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        task.progress = 100.0
        task.status = TaskStatus.SUCCESS
        task.message = "导入完成"
        task.result = {
            "total_rows": result.total_rows,
            "orders_count": result.orders_count,
            "total_amount": str(result.total_amount) if result.total_amount else None,
            "stores_count": result.stores_count,
            "skipped_empty_rows": result.skipped_empty_rows,
        }
        invalidate_cache()
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.message = "导入失败"
        task.error = str(e)


def _run_xiaocan_import(task_id: str, file_bytes: bytes) -> None:
    task = _tasks.get(task_id)
    if not task:
        return
    task.status = TaskStatus.RUNNING
    task.progress = 10.0
    task.message = "开始解析小蚕订单 Excel..."

    try:
        task.progress = 30.0
        task.message = "解析完成，开始导入数据库..."

        conn = get_conn()
        try:
            result = import_xiaocan_excel(conn, file_bytes)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        task.progress = 100.0
        task.status = TaskStatus.SUCCESS
        task.message = "导入完成"
        task.result = {
            "total_rows": result.total_rows,
            "matched_count": result.matched_count,
            "unmatched_count": result.unmatched_count,
        }
        invalidate_cache()
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.message = "导入失败"
        task.error = str(e)


def submit_coffee_import(file_bytes: bytes) -> str:
    """Submit a coffee orders import task and return task_id."""
    task_id = str(uuid.uuid4())
    _tasks[task_id] = TaskInfo(task_id=task_id, status=TaskStatus.PENDING)
    thread = Thread(target=_run_coffee_import, args=(task_id, file_bytes), daemon=True)
    thread.start()
    return task_id


def submit_xiaocan_import(file_bytes: bytes) -> str:
    """Submit a xiaocan orders import task and return task_id."""
    task_id = str(uuid.uuid4())
    _tasks[task_id] = TaskInfo(task_id=task_id, status=TaskStatus.PENDING)
    thread = Thread(target=_run_xiaocan_import, args=(task_id, file_bytes), daemon=True)
    thread.start()
    return task_id


def get_task(task_id: str) -> Optional[TaskInfo]:
    """Get task status by ID."""
    return _tasks.get(task_id)


def clean_stale_tasks(max_age_hours: int = 24) -> None:
    """Remove completed/failed tasks older than max_age_hours."""
    import time
    cutoff = time.time() - max_age_hours * 3600
    to_remove = [tid for tid, task in _tasks.items() if task.status in (TaskStatus.SUCCESS, TaskStatus.FAILED) and task.created_at < cutoff]
    for tid in to_remove:
        del _tasks[tid]