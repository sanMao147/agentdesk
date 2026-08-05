"""配置管理路由。

提供服务配置的查询和修改接口：
- GET /api/config: 获取当前完整配置
- PATCH /api/config: 部分更新配置（当前仅支持切换 chat_model）

配置资源视图包含：LLM 开关、向量后端、检索参数、模型信息、索引状态等。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.errors import ApiError
from app.config import settings

# 创建路由实例，前缀为 /api/config
router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigPatch(BaseModel):
    """配置更新请求体。

    当前仅支持切换 chat_model，后续可扩展更多字段。

    Attributes:
        chat_model: 新的聊天模型名称（可选，不填则不修改）
    """
    chat_model: str | None = None


def _config_resource() -> dict[str, Any]:
    """组装完整的配置资源视图。

    聚合 settings 配置和索引状态信息，返回给前端展示。
    """
    # 局部导入避免循环依赖
    from app.api.routes.index import get_index_info

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
    """获取当前配置。

    返回完整的配置信息，包括：
    - LLM 状态（是否使用、模型名）
    - 检索参数（top_k、max_iterations）
    - 向量后端（memory/qdrant）
    - 索引统计（chunk 数量、签名）
    """
    return _config_resource()


@router.patch("")
def patch_config(patch: ConfigPatch) -> dict[str, Any]:
    """部分更新配置。

    当前支持：切换 chat_model
    前置条件：系统必须处于在线模式（配置了 OPENAI_API_KEY）

    异常情况：
    - 离线模式下尝试切换模型 → 返回 400 offline_mode

    返回更新后的完整配置视图。
    """
    new_model = (patch.chat_model or "").strip()
    if new_model:
        if not settings.use_llm:
            raise ApiError(
                code="offline_mode",
                message="离线 fallback 不调用大模型，切换无效（需在 .env 配 key）",
                status=400,
            )
        # 切换模型：同步更新 settings 和环境变量
        # 使 app/llm.py:chat() 下次调用时直接读到新值
        settings.set_chat_model(new_model)
    return _config_resource()
