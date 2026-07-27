"""记忆路由：GET /api/users/{user_id}/memories。

按 superseded_by 是否为空分桶为 {live: [...], dead: [...]}。
list_by_user 失败时优雅降级为空列表（记忆故障不阻断主流程）。
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/users", tags=["memories"])
_log = logging.getLogger(__name__)


@router.get("/{user_id}/memories")
def list_memories(user_id: str) -> dict[str, Any]:
    try:
        from app.memory.store import get_memory_store
        recs = get_memory_store().list_by_user(user_id)
    except Exception:
        _log.exception("list_by_user failed for user_id=%s", user_id)
        return {"live": [], "dead": []}

    live: list[dict[str, Any]] = []
    dead: list[dict[str, Any]] = []
    for r in recs:
        item = {
            "mem_id": getattr(r, "mem_id", None),
            "kind": getattr(r, "kind", None),
            "text": getattr(r, "text", None),
            "version": getattr(r, "version", None),
            "use_count": getattr(r, "use_count", None),
            "updated_at": getattr(r, "updated_at", None),
            "superseded_by": getattr(r, "superseded_by", None),
        }
        if getattr(r, "superseded_by", None):
            dead.append(item)
        else:
            live.append(item)
    return {"live": live, "dead": dead}
