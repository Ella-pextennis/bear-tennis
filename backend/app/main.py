"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import close_pool, ensure_schema, init_pool
from .models import HealthCheck
from .routes import orders, stats, upload, xiaocan


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    init_pool()
    ensure_schema()
    try:
        yield
    finally:
        close_pool()


app = FastAPI(
    title="BearmeCoffee 订单大盘 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(orders.router, prefix="/api", tags=["orders"])
app.include_router(stats.router, prefix="/api", tags=["stats"])
app.include_router(xiaocan.router, prefix="/api", tags=["xiaocan"])


@app.get("/api/health", response_model=HealthCheck, tags=["system"])
def health() -> HealthCheck:
    from .db import get_conn

    db_status = "ok"
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:  # noqa: BLE001
        db_status = f"error: {e}"
    return HealthCheck(status="ok" if db_status == "ok" else "degraded", db=db_status)
