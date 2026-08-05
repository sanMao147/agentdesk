"""记忆专用存储层。

提供与 RAG 向量库一致的接口，支持两种后端实现：
- InMemoryMemoryStore: 进程内存储（dict + numpy 余弦相似度）
- QdrantMemoryStore: Qdrant 存储（生产环境推荐）

接口定义：
    upsert(rec)                 -> None          # 插入或更新记忆
    search(user_id, vec, top_k) -> List[(MemoryRecord, score)]  # 相似度检索
    delete(user_id, mem_ids)    -> None          # 批量删除
    list_by_user(user_id)       -> List[MemoryRecord]  # 列出用户所有记忆

后端选择逻辑：vector_backend=qdrant 且可连通 → Qdrant；否则回退内存。
记忆向量库使用独立 collection（settings.mem_collection），
不与 RAG 知识库混用，避免"知识"与"记忆"互相污染检索。
"""
from __future__ import annotations

import uuid
from typing import List, Tuple

import numpy as np

from app.config import settings
from app.memory.schema import MemoryRecord


def _cosine(a: List[float], b: List[float]) -> float:
    """计算两个向量的余弦相似度。"""
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(va @ vb / (na * nb))


class InMemoryMemoryStore:
    """进程内记忆存储。

    使用 dict 存储记忆，numpy 计算余弦相似度。
    重启即丢失，仅用于无 Qdrant 的演示场景。

    数据结构：user_id -> {mem_id -> MemoryRecord}
    """

    def __init__(self) -> None:
        self._data: dict[str, dict[str, MemoryRecord]] = {}

    def upsert(self, rec: MemoryRecord) -> None:
        """插入或更新一条记忆。"""
        self._data.setdefault(rec.user_id, {})[rec.mem_id] = rec

    def search(self, user_id: str, vec: List[float], top_k: int = 3) -> List[Tuple[MemoryRecord, float]]:
        """余弦相似度检索。

        只召回"现行"记忆（superseded_by 为 None 的未被覆盖的记忆）。
        """
        bucket = self._data.get(user_id, {})
        scored = [
            (rec, _cosine(vec, rec.embedding))
            for rec in bucket.values()
            if rec.superseded_by is None and rec.embedding  # 只检索现行且有向量的记忆
        ]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]

    def delete(self, user_id: str, mem_ids: List[str]) -> None:
        """批量删除记忆。"""
        bucket = self._data.get(user_id, {})
        for mid in mem_ids:
            bucket.pop(mid, None)

    def list_by_user(self, user_id: str) -> List[MemoryRecord]:
        """列出指定用户的所有记忆（含被覆盖的旧记忆）。"""
        return list(self._data.get(user_id, {}).values())

    @property
    def backend(self) -> str:
        return "memory"


class QdrantMemoryStore:
    """Qdrant 记忆存储。

    使用 Qdrant 的 payload 过滤实现多租户隔离（按 user_id 过滤）。
    集合不存在时自动创建，向量维度与 embedding 模型一致。
    """

    def __init__(self) -> None:
        from qdrant_client import QdrantClient

        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.mem_collection
        self._ready = False

    def _ensure(self, dim: int) -> None:
        """确保 collection 存在且维度正确。"""
        if self._ready:
            return
        from qdrant_client.models import Distance, VectorParams

        names = [c.name for c in self.client.get_collections().collections]
        if self.collection not in names:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
        self._ready = True

    @staticmethod
    def _pid(mem_id: str) -> str:
        """生成 Qdrant 点 ID。

        使用 UUID5 基于 mem_id 生成，确保同一 mem_id 始终映射到同一点 ID，
        实现 upsert 覆盖。
        """
        return str(uuid.uuid5(uuid.NAMESPACE_URL, mem_id))

    def upsert(self, rec: MemoryRecord) -> None:
        """插入或更新一条记忆到 Qdrant。"""
        from qdrant_client.models import PointStruct

        if not rec.embedding:
            return
        self._ensure(len(rec.embedding))
        self.client.upsert(
            collection_name=self.collection,
            points=[PointStruct(
                id=self._pid(rec.mem_id),
                vector=rec.embedding,
                payload=rec.to_payload(),
            )],
        )

    def _user_filter(self, user_id: str):
        """构建 user_id 过滤器（Qdrant payload 过滤语法）。"""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        return Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])

    def search(self, user_id: str, vec: List[float], top_k: int = 3) -> List[Tuple[MemoryRecord, float]]:
        """在指定用户范围内进行向量检索。"""
        try:
            hits = self.client.search(
                collection_name=self.collection,
                query_vector=vec,
                query_filter=self._user_filter(user_id),
                limit=top_k,
            )
        except Exception:
            return []  # collection 尚未创建（冷启动）等情况：视为无记忆

        out: List[Tuple[MemoryRecord, float]] = []
        for h in hits:
            p = h.payload or {}
            if p.get("superseded_by"):
                continue  # 跳过已被覆盖的旧记忆
            out.append((MemoryRecord.from_payload(p), float(h.score)))
        return out

    def delete(self, user_id: str, mem_ids: List[str]) -> None:
        """按点 ID 批量删除。"""
        from qdrant_client.models import PointIdsList

        if not mem_ids:
            return
        self.client.delete(
            collection_name=self.collection,
            points_selector=PointIdsList(points=[self._pid(m) for m in mem_ids]),
        )

    def list_by_user(self, user_id: str) -> List[MemoryRecord]:
        """滚动列出指定用户的所有记忆。"""
        try:
            res, _ = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=self._user_filter(user_id),
                with_payload=True,
                with_vectors=True,
                limit=10000,
            )
        except Exception:
            return []
        return [MemoryRecord.from_payload(p.payload or {}, p.vector or []) for p in res]

    @property
    def backend(self) -> str:
        return "qdrant"


# 全局单例（懒加载）
_memory_store = None


def get_memory_store():
    """获取记忆存储单例（懒加载工厂）。

    与 rag.store_factory.get_store() 同构的回退逻辑：
    1. 优先尝试 Qdrant 连接
    2. 失败则回退进程内存储
    """
    global _memory_store
    if _memory_store is not None:
        return _memory_store

    if getattr(settings, "vector_backend", "memory") == "qdrant":
        try:
            store = QdrantMemoryStore()
            store.client.get_collections()  # 探活
            print(f"[memory] using Qdrant @ {settings.qdrant_url} / {settings.mem_collection}")
            _memory_store = store
            return _memory_store
        except Exception as e:
            print(f"[memory] Qdrant unavailable ({e}); fallback to memory")

    _memory_store = InMemoryMemoryStore()
    return _memory_store
