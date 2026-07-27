"""会话路由：POST /api/sessions。"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=201)
def create_session() -> dict[str, Any]:
    return {"session_id": uuid.uuid4().hex}
