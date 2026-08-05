"""会话管理路由。

端点：POST /api/sessions
功能：创建新的会话，返回唯一的 session_id。

session_id 用于：
1. 关联同一用户的多轮对话（短期记忆上下文）
2. 跟踪对话历史和执行链路
3. 支持多会话并行
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter

# 创建路由实例，前缀为 /api/sessions，标签为 sessions
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=201)
def create_session() -> dict[str, Any]:
    """创建新会话。

    生成一个 UUID 作为会话标识符，前端在后续查询请求中携带此 ID。

    返回格式：
        {"session_id": "hex_string"}

    状态码：201 Created
    """
    return {"session_id": uuid.uuid4().hex}
