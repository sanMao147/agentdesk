"""Embedding 缓存。

降低重复检索/重复文本的 embedding 计算与 API 调用开销。

缓存策略：
- 优先 Redis（可选依赖），支持跨进程共享
- 回退进程内 dict，单进程有效

Key 格式：emb:{md5(model + text)}
Value 格式：JSON 序列化的 float 列表

TTL：Redis 中 1 小时，内存中无过期
"""
from __future__ import annotations

import hashlib
import json
from typing import List, Optional

from app.config import settings


class EmbeddingCache:
    """Embedding 缓存管理器。

    存储文本到向量的映射，避免重复计算。
    支持 Redis 和进程内 dict 两种后端。
    """

    def __init__(self) -> None:
        self._mem: dict[str, List[float]] = {}
        self._redis = None

        # 尝试连接 Redis
        url = getattr(settings, "redis_url", "")
        if url:
            try:
                import redis  # 可选依赖

                self._redis = redis.from_url(url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None  # 连接不上就退化为内存

    @staticmethod
    def _key(text: str) -> str:
        """生成缓存键。

        格式：emb:{md5(embedding_model:text)}
        将模型名纳入 key，确保不同模型的 embedding 不会互相污染。
        """
        raw = f"{settings.embedding_model}:{text}"
        return "emb:" + hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        """获取缓存。

        Redis 优先，回退内存。
        """
        k = self._key(text)
        if self._redis is not None:
            v = self._redis.get(k)
            return json.loads(v) if v else None
        return self._mem.get(k)

    def set(self, text: str, vec: List[float]) -> None:
        """写入缓存。

        Redis 中设置 1 小时 TTL。
        """
        k = self._key(text)
        if self._redis is not None:
            self._redis.set(k, json.dumps(vec), ex=3600)
        else:
            self._mem[k] = vec

    @property
    def backend(self) -> str:
        """返回当前使用的缓存后端。"""
        return "redis" if self._redis is not None else "memory"


# 全局缓存单例
cache = EmbeddingCache()
