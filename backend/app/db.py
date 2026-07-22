"""MySQL connection helper (PyMySQL, pure Python — no native deps).

Connections are opened lazily per request via get_conn(). init_pool()/close_pool()
are no-ops preserved for lifespan symmetry with the previous Oracle pool. This means
the backend boots even when MySQL is unavailable — connection errors surface
per-request instead of crashing startup.
"""
from __future__ import annotations

import logging

import pymysql

from .config import get_settings

logger = logging.getLogger(__name__)


def init_pool() -> None:
    """No-op. MySQL connections are opened lazily per request via get_conn()."""
    pass


def close_pool() -> None:
    """No-op. Connections are closed per-request in route handlers."""
    pass


def get_conn() -> pymysql.connections.Connection:
    """Open a new MySQL connection. Caller is responsible for closing it.

    Use as: conn = get_conn(); try: ... finally: conn.close()
    """
    settings = get_settings()
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_database,
        charset="utf8mb4",
        autocommit=False,
    )


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def _index_exists(cur, table: str, index_name: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s
        """,
        (table, index_name),
    )
    return cur.fetchone() is not None


def ensure_schema() -> None:
    """Idempotent schema migration: add new columns / tables if missing.

    Called once on application startup. Safe to run multiple times.
    Failures are logged but do not crash startup — per-request errors will surface
    the actual problem if MySQL is unreachable.
    """
    try:
        conn = get_conn()
    except Exception as e:  # noqa: BLE001
        logger.warning("ensure_schema: cannot connect to MySQL, skipping migration: %s", e)
        return

    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS coffee_orders (
              id                 INT AUTO_INCREMENT PRIMARY KEY,
              order_no           VARCHAR(100),
              order_date         DATETIME,
              store_name         VARCHAR(100),
              queue_no           VARCHAR(50),
              order_source       VARCHAR(50),
              delivery_method    VARCHAR(50),
              status             VARCHAR(50),
              payment_method     VARCHAR(50),
              member_no          VARCHAR(50),
              customer_name      VARCHAR(100),
              phone              VARCHAR(20),
              address            VARCHAR(500),
              product_name       VARCHAR(200),
              flavor_group       VARCHAR(50),
              unit_price         DECIMAL(12, 2),
              quantity           DECIMAL(12, 2),
              amount             DECIMAL(12, 2),
              remark             VARCHAR(500),
              logistics_no       VARCHAR(100),
              weight             VARCHAR(50),
              is_order_header    TINYINT NOT NULL DEFAULT 0,
              platform_order_no  VARCHAR(50),
              discount_amount    DECIMAL(12, 2),
              is_xiaocan         TINYINT NOT NULL DEFAULT 0,
              updated_at         DATETIME NULL,
              imported_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_order_header_date (is_order_header, order_date),
              INDEX idx_order_source (is_order_header, order_source),
              INDEX idx_member_no (is_order_header, member_no),
              INDEX idx_platform_order_no (platform_order_no),
              INDEX idx_is_xiaocan (is_xiaocan)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        if not _column_exists(cur, "coffee_orders", "is_xiaocan"):
            cur.execute("ALTER TABLE coffee_orders ADD COLUMN is_xiaocan TINYINT NOT NULL DEFAULT 0")
            logger.info("Added column coffee_orders.is_xiaocan")
        if not _column_exists(cur, "coffee_orders", "updated_at"):
            cur.execute("ALTER TABLE coffee_orders ADD COLUMN updated_at DATETIME NULL")
            logger.info("Added column coffee_orders.updated_at")
        if not _column_exists(cur, "coffee_orders", "platform_order_no"):
            cur.execute("ALTER TABLE coffee_orders ADD COLUMN platform_order_no VARCHAR(50)")
            logger.info("Added column coffee_orders.platform_order_no")
        if not _column_exists(cur, "coffee_orders", "discount_amount"):
            cur.execute("ALTER TABLE coffee_orders ADD COLUMN discount_amount DECIMAL(12, 2)")
            logger.info("Added column coffee_orders.discount_amount")

        if not _index_exists(cur, "coffee_orders", "idx_order_header_date"):
            cur.execute("CREATE INDEX idx_order_header_date ON coffee_orders (is_order_header, order_date)")
            logger.info("Added index idx_order_header_date")
        if not _index_exists(cur, "coffee_orders", "idx_order_source"):
            cur.execute("CREATE INDEX idx_order_source ON coffee_orders (is_order_header, order_source)")
            logger.info("Added index idx_order_source")
        if not _index_exists(cur, "coffee_orders", "idx_member_no"):
            cur.execute("CREATE INDEX idx_member_no ON coffee_orders (is_order_header, member_no)")
            logger.info("Added index idx_member_no")
        if not _index_exists(cur, "coffee_orders", "idx_platform_order_no"):
            cur.execute("CREATE INDEX idx_platform_order_no ON coffee_orders (platform_order_no)")
            logger.info("Added index idx_platform_order_no")
        if not _index_exists(cur, "coffee_orders", "idx_is_xiaocan"):
            cur.execute("CREATE INDEX idx_is_xiaocan ON coffee_orders (is_xiaocan)")
            logger.info("Added index idx_is_xiaocan")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS xiaocan_orders (
              id                 INT AUTO_INCREMENT PRIMARY KEY,
              xiaocan_order_no   VARCHAR(50),
              platform           VARCHAR(50),
              order_time         DATETIME,
              platform_order_no  VARCHAR(50),
              settlement_amount DECIMAL(12, 2),
              imported_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_xiaocan_platform_order_no (platform_order_no),
              INDEX idx_xiaocan_order_time (order_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS xiaocan_rebate_settlements (
              id           INT AUTO_INCREMENT PRIMARY KEY,
              settle_date  DATE NOT NULL,
              amount       DECIMAL(12, 2) NOT NULL,
              remark       VARCHAR(500),
              created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_rebate_settle_date (settle_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cur.close()
        conn.commit()
    except Exception as e:  # noqa: BLE001
        logger.error("ensure_schema migration failed: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()

