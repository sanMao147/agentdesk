"""索引路由：GET /api/index · POST /api/index/rebuilds。

辅助函数 get_index_info/rebuild_index 也被 config 路由复用。
"""
from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter

from app.config import settings
from app.rag.indexer import INDEX_PATH, build_index

router = APIRouter(prefix="/api/index", tags=["index"])

_META_PATH = os.path.join(os.path.dirname(INDEX_PATH), "index_meta.json")


def get_index_info() -> dict[str, Any]:
    """读 INDEX_PATH 得 n_chunks，读 index_meta.json 得 index_signature。"""
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
        pass

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
    """清缓存 + 清检索器单例 + 重建索引 + 写 index_meta.json。

    镜像 streamlit_app._rebuild_index 的逻辑；返回重建后的 get_index_info()。
    """
    # 清掉旧维度的 embedding 缓存与检索器单例（离线 256 ↔ 真实 1024 维度不匹配）
    try:
        from app.rag.cache import cache as _c
        getattr(_c, "_mem", {}).clear()
    except Exception:
        pass
    try:
        import app.graph.nodes as _n
        _n._retriever = None
    except Exception:
        pass
    len(build_index())  # 计数本身不使用；重建副作用已落盘到 INDEX_PATH
    try:
        os.makedirs(os.path.dirname(_META_PATH), exist_ok=True)
        with open(_META_PATH, "w", encoding="utf-8") as f:
            json.dump(settings.index_signature, f)
    except Exception:
        pass
    return get_index_info()


@router.get("")
def get_index() -> dict[str, Any]:
    return get_index_info()


@router.post("/rebuilds", status_code=201)
def rebuild() -> dict[str, Any]:
    return rebuild_index()
