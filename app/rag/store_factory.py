"""向量库后端工厂。

根据配置选择向量库后端：
- 优先 Qdrant（如果配置了 vector_backend=qdrant 且可连通）
- 回退内存存储（VectorStore）

设计：工厂模式，调用方无需关心具体后端实现。
"""
from __future__ import annotations

import time

from app.config import settings
from app.rag.store import VectorStore


def get_store(max_retries: int = 5, retry_delay: float = 3.0):
    """获取向量存储单例。

    回退逻辑：
    1. 检查 vector_backend 配置
    2. 如果是 "qdrant"，尝试导入 QdrantStore 并连接
    3. 连接失败则降级为 VectorStore（内存实现）

    保证任何环境都能运行，不强制依赖外部服务。
    """
    if getattr(settings, "vector_backend", "memory") == "qdrant":
        for attempt in range(1, max_retries + 1):
            try:
                from app.rag.qdrant_store import QdrantStore
                store = QdrantStore()
                # 验证连接：尝试获取 collections 列表
                store.client.get_collections()
                print(f"[store] using Qdrant @ {settings.qdrant_url}")
                return store
            except Exception as e:
                print(f"[store] Qdrant attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    print(f"[store] Qdrant unavailable ({e}); fallback to memory")

    return VectorStore()
