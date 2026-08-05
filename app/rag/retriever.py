"""RAG 检索器。

实现混合检索 + Rerank 的完整检索管线：
1. 向量检索（语义相似度）
2. BM25 关键词检索（精确匹配）
3. RRF（Reciprocal Rank Fusion）融合两路结果
4. 可选 Rerank 重排提升精度

支持多查询融合（retrieve_multi），用于 Multi-Query 场景。

召回流程：
    query → embed_query → Vector Search ─┐
                                         ├→ RRF Fusion → Rerank → Top-K Evidence
    query → tokenize → BM25 Search ──────┘
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.config import settings
from app.llm import embed_query
from app.rag.bm25 import BM25
from app.rag.indexer import INDEX_PATH
from app.rag.rerank import rerank
from app.rag.store import Chunk
from app.rag.store_factory import get_store

# 候选池大小：召回阶段先取 CANDIDATE_N 条，再由 Rerank 精排
CANDIDATE_N = 20
# RRF 融合参数：k 值越大，排名越靠后的文档影响越小
RRF_K = 60


@dataclass
class Evidence:
    """证据片段。

    Attributes:
        doc_id: 来源文档 ID（文件名）
        chunk_id: 片段唯一标识（doc_id#index）
        text: 片段文本内容
        score: 相关性得分（RRF 融合后或 Rerank 后）
    """
    doc_id: str
    chunk_id: str
    text: str
    score: float


class Retriever:
    """混合检索器。

    封装完整的检索管线：
    - 初始化时加载索引、创建 BM25 实例
    - 支持向量检索、BM25 检索、混合检索
    - 支持 RRF 融合和 Rerank 重排

    使用全局单例，避免每次请求重新加载索引。
    """

    def __init__(self) -> None:
        self.store = get_store()
        self.store.load(INDEX_PATH)  # 加载索引到内存
        self.bm25 = BM25(self.store.chunks)  # 基于当前 chunk 构建 BM25 索引

    def _vector(self, query: str, n: int) -> List[Chunk]:
        """向量检索：语义相似度召回 top_n 条。"""
        qv = embed_query(query)
        return [c for c, _ in self.store.search(qv, top_k=n)]

    def _bm25(self, query: str, n: int) -> List[Chunk]:
        """BM25 检索：关键词精确匹配召回 top_n 条。"""
        return [c for c, _ in self.bm25.search(query, top_k=n)]

    @staticmethod
    def _rrf(rank_lists: List[List[Chunk]]) -> List[tuple]:
        """RRF 融合（Reciprocal Rank Fusion）。

        融合多路检索结果，对每个文档计算分数：
        score = Σ 1/(k + rank_i)，rank_i 是文档在第 i 路结果中的排名

        RRF 的优点：
        - 无需归一化不同检索器的分数
        - 对排名靠后的文档影响递减（由 k 控制）
        - 鲁棒性强，适合融合异构检索方法
        """
        scores = {}
        by_id = {}
        for lst in rank_lists:
            for rank, c in enumerate(lst):
                by_id[c.chunk_id] = c
                scores[c.chunk_id] = scores.get(c.chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
        fused = sorted(scores.items(), key=lambda x: -x[1])
        return [(by_id[cid], s) for cid, s in fused]

    def retrieve(self, query: str, mode: str = "hybrid", use_rerank: bool = True,
                 top_k: int | None = None) -> List[Evidence]:
        """单查询检索。"""
        return self.retrieve_multi([query], mode=mode, use_rerank=use_rerank, top_k=top_k)

    def retrieve_multi(self, queries: List[str], mode: str = "hybrid",
                       use_rerank: bool = True, top_k: int | None = None) -> List[Evidence]:
        """多查询融合检索。

        流程：
        1. 对每个查询分别执行向量检索和 BM25 检索
        2. 将所有结果合并后通过 RRF 融合
        3. 取 top CANDIDATE_N 条作为候选
        4. 可选 Rerank 精排，最终返回 top_k 条证据

        Args:
            queries: 多个检索查询（由 planner 改写生成）
            mode: "hybrid"（向量+BM25）或 "vector"（仅向量）
            use_rerank: 是否启用 Rerank 重排
            top_k: 最终返回的证据数量

        Returns:
            按相关性降序排列的证据列表
        """
        k = top_k or settings.top_k
        rank_lists: List[List[Chunk]] = []

        # 对每个查询执行检索
        for q in queries:
            rank_lists.append(self._vector(q, CANDIDATE_N))
            if mode == "hybrid":
                rank_lists.append(self._bm25(q, CANDIDATE_N))

        # 融合多路结果
        if mode == "vector" and len(rank_lists) == 1:
            # 单路向量检索：直接用原始排名
            fused = [(c, 1.0 / (RRF_K + i + 1)) for i, c in enumerate(rank_lists[0])]
        else:
            fused = self._rrf(rank_lists)

        # 截取候选
        candidates = [c for c, _ in fused][:CANDIDATE_N]

        # Rerank 精排
        if use_rerank:
            reranked = rerank(queries[0], candidates, top_k=k)
            return [Evidence(c.doc_id, c.chunk_id, c.text, s) for c, s in reranked]

        # 不 Rerank 直接截取
        return [Evidence(c.doc_id, c.chunk_id, c.text, s) for c, s in fused[:k]]
