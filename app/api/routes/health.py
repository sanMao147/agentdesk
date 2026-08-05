"""健康检查路由。

端点：GET /api/health
功能：返回服务健康状态，用于负载均衡/监控系统检测服务是否存活。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

# 创建路由实例，前缀为 /api（注意：健康检查端点在 /api/health）
router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict[str, Any]:
    """健康检查。

    返回简单的 OK 状态。在更复杂的实现中可以加入：
    - 数据库连接检查
    - 向量存储连接检查
    - 内存使用情况
    """
    return {"status": "ok"}
