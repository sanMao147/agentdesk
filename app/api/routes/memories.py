"""记忆管理路由。

端点：GET /api/users/{user_id}/memories
功能：获取指定用户的所有记忆记录。

记忆分类：
- live: 现行有效的记忆（superseded_by 为空）
- dead: 已被新值取代的旧记忆（superseded_by 指向新记忆 ID）

设计：记忆故障不阻断主流程，异常时优雅降级为空列表。
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

# 创建路由实例，前缀为 /api/users
router = APIRouter(prefix="/api/users", tags=["memories"])
_log = logging.getLogger(__name__)


@router.get("/{user_id}/memories")
def list_memories(user_id: str) -> dict[str, Any]:
    """获取指定用户的所有记忆。

    将记忆分为两个桶：
    - live: 当前生效的记忆（未被覆盖）
    - dead: 已被取代的旧记忆（保留审计痕迹）

    记忆存储故障时降级返回空列表，不影响主流程。
    """
    try:
        from app.memory.store import get_memory_store
        recs = get_memory_store().list_by_user(user_id)
    except Exception:
        _log.exception("list_by_user failed for user_id=%s", user_id)
        return {"live": [], "dead": []}

    # 遍历所有记忆，按 superseded_by 是否为空分桶
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
            # 有 superseded_by 表示已被新记忆取代
            dead.append(item)
        else:
            live.append(item)
    return {"live": live, "dead": dead}
