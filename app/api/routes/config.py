"""配置路由：GET /api/config · PATCH /api/config。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.errors import ApiError
from app.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigPatch(BaseModel):
    chat_model: str | None = None


def _config_resource() -> dict[str, Any]:
    """组装完整 config 资源视图；n_chunks 由 index 路由的辅助函数读取。"""
    from app.api.routes.index import get_index_info  # 局部导入，避免循环依赖

    info = get_index_info()
    return {
        "use_llm": bool(settings.use_llm),
        "vector_backend": settings.vector_backend,
        "top_k": settings.top_k,
        "max_iterations": settings.max_iterations,
        "chat_model": settings.chat_model,
        "embedding_model": settings.embedding_model,
        "n_chunks": info["n_chunks"],
        "index_signature": settings.index_signature,
    }


@router.get("")
def get_config() -> dict[str, Any]:
    return _config_resource()


@router.patch("")
def patch_config(patch: ConfigPatch) -> dict[str, Any]:
    new_model = (patch.chat_model or "").strip()
    if new_model:
        if not settings.use_llm:
            raise ApiError(
                code="offline_mode",
                message="离线 fallback 不调用大模型，切换无效（需在 .env 配 key）",
                status=400,
            )
        settings.set_chat_model(new_model)
    return _config_resource()
