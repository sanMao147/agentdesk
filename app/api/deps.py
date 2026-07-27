"""共享 FastAPI 依赖（占位，便于后续扩展 DI）。"""
from __future__ import annotations

from app.config import settings


def get_settings():
    """返回全局 settings 单例。"""
    return settings
