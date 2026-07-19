"""Simple in-memory cache for aggregated stats.

Cache expires after 5 minutes by default.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    data: Any
    created_at: float = field(default_factory=time.time)


_cache: Dict[str, CacheEntry] = {}
DEFAULT_TTL = 300


def get_cache(key: str) -> Optional[Any]:
    """Get cached data if not expired."""
    entry = _cache.get(key)
    if not entry:
        return None
    if time.time() - entry.created_at > DEFAULT_TTL:
        del _cache[key]
        return None
    return entry.data


def set_cache(key: str, data: Any) -> None:
    """Cache data with default TTL."""
    _cache[key] = CacheEntry(data=data)


def invalidate_cache() -> None:
    """Clear all cached data."""
    _cache.clear()


def get_or_compute(key: str, compute_fn, ttl: int = DEFAULT_TTL) -> Any:
    """Get cached data or compute and cache it."""
    entry = _cache.get(key)
    if entry and time.time() - entry.created_at < ttl:
        return entry.data
    data = compute_fn()
    _cache[key] = CacheEntry(data=data)
    return data