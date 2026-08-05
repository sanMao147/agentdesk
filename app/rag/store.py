"""内存向量存储（最小可用实现）。

实现与 Qdrant/PGVector 兼容的接口，便于替换：
- add: 添加 chunk 列表
- search: 余弦相似度检索
- save: 持久化为 JSON
- load: 从 JSON 加载
- chunks: 返回所有 chunk
- __len__: chunk 总数

使用 numpy 矩阵运算高效计算余弦相似度。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import List

import numpy as np


@dataclass
class Chunk:
    """文档片段。

    Attributes:
        doc_id: 来源文档 ID
        chunk_id: 片段唯一标识（doc_id#index）
        text: 片段文本
        embedding: 向量表示
    """
    doc_id: str
    chunk_id: str
    text: str
    embedding: List[float]


class VectorStore:
    """进程内向量存储。

    使用 numpy 矩阵批量计算余弦相似度，性能优于逐对计算。
    适合中小规模知识库（数千至数万 chunk）。

    数据结构：
    - _chunks: List[Chunk]，存储所有片段
    - _matrix: np.ndarray，预计算的 embedding 矩阵（None 表示需要重建）
    """

    def __init__(self) -> None:
        self._chunks: List[Chunk] = []
        self._matrix = None

    def add(self, chunks: List[Chunk]) -> None:
        """添加 chunk 到存储。

        追加后将 _matrix 置为 None，下次 search 时重建矩阵。
        """
        self._chunks.extend(chunks)
        self._matrix = None  # 标记矩阵需要重建

    def _ensure_matrix(self) -> None:
        """确保 embedding 矩阵已构建。

        延迟初始化：仅在首次 search 或 add 后需要时构建。
        """
        if self._matrix is None and self._chunks:
            self._matrix = np.array([c.embedding for c in self._chunks], dtype=np.float32)

    def search(self, query_vec: List[float], top_k: int = 5):
        """余弦相似度检索。

        使用矩阵运算高效计算：
        scores = (matrix @ query) / (||matrix|| * ||query||)

        Args:
            query_vec: 查询向量
            top_k: 返回最相似的 k 条

        Returns:
            [(Chunk, score), ...] 按分数降序排列
        """
        self._ensure_matrix()
        if not self._chunks or self._matrix is None:
            return []

        q = np.array(query_vec, dtype=np.float32)
        qn = np.linalg.norm(q) or 1.0  # 避免除零
        mn = np.linalg.norm(self._matrix, axis=1)
        mn[mn == 0] = 1.0  # 避免除零

        # 批量计算余弦相似度
        scores = (self._matrix @ q) / (mn * qn)
        idx = np.argsort(-scores)[:top_k]

        return [(self._chunks[i], float(scores[i])) for i in idx]

    def save(self, path: str) -> None:
        """持久化为 JSON 文件。"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in self._chunks], f, ensure_ascii=False)

    def load(self, path: str) -> None:
        """从 JSON 文件加载。"""
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._chunks = [Chunk(**d) for d in data]
        self._matrix = None  # 标记矩阵需要重建

    @property
    def chunks(self) -> List[Chunk]:
        """返回所有 chunk。"""
        return self._chunks

    def __len__(self) -> int:
        return len(self._chunks)
