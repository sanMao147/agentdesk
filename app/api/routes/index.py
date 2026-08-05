"""索引管理路由。

提供知识库索引的查询和重建接口：
- GET /api/index: 获取当前索引状态（文档数、索引签名）
- POST /api/index/rebuilds: 重建索引（清除缓存 + 重新向量化 + 落盘）

辅助函数 get_index_info/rebuild_index 也被 config 路由复用。
"""
from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter

from app.config import settings
from app.rag.indexer import INDEX_PATH, build_index

# 创建路由实例，前缀为 /api/index
router = APIRouter(prefix="/api/index", tags=["index"])

# 索引元数据文件路径（存储索引签名，用于判断是否需要重建）
_META_PATH = os.path.join(os.path.dirname(INDEX_PATH), "index_meta.json")


def get_index_info() -> dict[str, Any]:
    """读取索引状态信息。

    从 INDEX_PATH 读取已索引的 chunk 数量，
    从 index_meta.json 读取索引签名（判断 embedding 模型是否变更）。

    返回：
        {
            "n_chunks": int,           # 已索引的 chunk 数量
            "index_signature": dict,   # 索引签名（含模型信息）
            "use_llm": bool,           # 是否使用真实 LLM
            "embedding_model": str     # 当前 embedding 模型名
        }
    """
    n_chunks = -1
    try:
        if os.path.exists(INDEX_PATH):
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                n_chunks = len(data)
            elif isinstance(data, dict):
                n_chunks = len(data.get("chunks", []))
    except Exception:
        pass  # 读取失败则保持 -1，表示未知

    index_signature: Any = None
    try:
        if os.path.exists(_META_PATH):
            with open(_META_PATH, "r", encoding="utf-8") as f:
                index_signature = json.load(f)
    except Exception:
        pass

    return {
        "n_chunks": n_chunks,
        "index_signature": index_signature,
        "use_llm": bool(settings.use_llm),
        "embedding_model": settings.embedding_model,
    }


def rebuild_index() -> dict[str, Any]:
    """重建索引。

    执行步骤：
    1. 清除 embedding 缓存（旧维度的缓存会导致检索异常）
    2. 重置检索器单例（确保使用新的向量空间）
    3. 重新读取文档、切割、向量化、落盘
    4. 写入新的索引签名

    返回重建后的索引信息。
    """
    # 清除旧 embedding 缓存（处理离线 256 维 ↔ 真实 1024 维不匹配问题）
    try:
        from app.rag.cache import cache as _c
        getattr(_c, "_mem", {}).clear()
    except Exception:
        pass

    # 重置检索器单例
    try:
        import app.graph.nodes as _n
        _n._retriever = None
    except Exception:
        pass

    # 重建索引（build_index 会重新读取 data/docs 下所有文档并生成向量）
    len(build_index())  # 仅触发副作用，返回值不使用

    # 写入索引签名（用于下次启动时判断是否需要重建）
    try:
        os.makedirs(os.path.dirname(_META_PATH), exist_ok=True)
        with open(_META_PATH, "w", encoding="utf-8") as f:
            json.dump(settings.index_signature, f)
    except Exception:
        pass

    return get_index_info()


@router.get("")
def get_index() -> dict[str, Any]:
    """获取当前索引状态。

    返回索引的 chunk 数量、签名信息以及当前配置的 LLM/Embedding 模型。
    """
    return get_index_info()


@router.post("/rebuilds", status_code=201)
def rebuild() -> dict[str, Any]:
    """强制重建索引。

    清除所有缓存和旧数据，从零开始重新构建向量索引。
    适用于：
    - 更换了 embedding 模型后
    - 新增/修改了知识库文档后
    - 索引数据损坏需要修复时
    """
    return rebuild_index()
