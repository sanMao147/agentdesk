"""Qdrant 向量库适配器。

实现与内存版 VectorStore 完全一致的接口：
- add / search / save / load / chunks / __len__

依赖 qdrant-client（可选）。集合不存在时按向量维度自动创建。
使用 UUID5 确保 chunk_id 到 Qdrant point ID 的稳定映射。
"""
from __future__ import annotations

import uuid
from typing import List

from app.config import settings
from app.rag.store import Chunk


class QdrantStore:
    """Qdrant 向量存储适配器。

    使用 Qdrant 的 collection 存储知识库 chunk：
    - collection: 由 settings.qdrant_collection 指定
    - vector distance: 余弦相似度
    - payload: 存储 doc_id, chunk_id, text 元数据

    注意：Qdrant 本身已持久化，save/load 为空操作。
    """

    def __init__(self) -> None:
        from qdrant_client import QdrantClient

        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection

    def _ensure(self, dim: int) -> None:
        """确保 collection 存在且维度匹配。

        如果 collection 不存在，自动创建。
        """
        from qdrant_client.models import Distance, VectorParams

        names = [c.name for c in self.client.get_collections().collections]
        if self.collection not in names:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def add(self, chunks: List[Chunk]) -> None:
        """添加 chunk 到 Qdrant。

        使用 UUID5 基于 chunk_id 生成稳定的 point ID，
        保证同一 chunk_id 的重复写入会覆盖而非重复。
        """
        from qdrant_client.models import PointStruct

        if not chunks:
            return

        self._ensure(len(chunks[0].embedding))

        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, c.chunk_id)),
                vector=c.embedding,
                payload={"doc_id": c.doc_id, "chunk_id": c.chunk_id, "text": c.text},
            )
            for c in chunks
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query_vec: List[float], top_k: int = 5):
        """余弦相似度检索。"""
        hits = self.client.search(
            collection_name=self.collection,
            query_vector=query_vec,
            limit=top_k,
        )
        out = []
        for h in hits:
            p = h.payload or {}
            out.append((Chunk(p["doc_id"], p["chunk_id"], p["text"], []), float(h.score)))
        return out

    @property
    def chunks(self) -> List[Chunk]:
        """列出所有 chunk。

        使用 scroll API 全量扫描 collection。
        """
        res, _ = self.client.scroll(
            collection_name=self.collection,
            with_payload=True,
            with_vectors=True,
            limit=10000,
        )
        return [Chunk(p.payload["doc_id"], p.payload["chunk_id"],
                      p.payload["text"], p.vector or []) for p in res]

    def save(self, path: str) -> None:
        """保存（空操作）。Qdrant 已自动持久化。"""
        pass

    def load(self, path: str) -> None:
        """加载（空操作）。数据已在 Qdrant 中。"""
        pass

    def __len__(self) -> int:
        """获取 chunk 总数。"""
        try:
            return self.client.count(collection_name=self.collection).count
        except Exception:
            return 0
