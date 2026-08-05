"""极简 BM25 实现（纯 Python，无额外依赖）。

BM25 是基于概率检索模型的关键词匹配算法，
弥补向量检索对专有名词、数字、缩写等精确匹配的不足。

本实现特点：
- 纯 Python，零外部依赖
- 与向量检索互补，组成混合检索（Hybrid Search）
- 参数：k1=1.5（词频饱和参数）、b=0.75（文档长度归一化参数）
"""
from __future__ import annotations

import math
from collections import Counter
from typing import List

from app.rag.store import Chunk
from app.rag.tokenize import tokenize


class BM25:
    """BM25 关键词检索器。

    基于 Okapi BM25 算法实现，用于混合检索的关键词召回路径。

    算法公式：
    score(Q, D) = Σ IDF(q) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))

    其中：
    - tf: 词项频率
    - dl: 文档长度（词数）
    - avgdl: 平均文档长度
    - IDF: 逆文档频率

    k1 控制词频饱和（默认 1.5）：值越大，词频增加带来的得分提升越明显
    b 控制文档长度归一化（默认 0.75）：值越大，长文档的惩罚越强
    """

    def __init__(self, chunks: List[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.chunks = chunks

        # 对每个 chunk 进行分词
        self.docs = [tokenize(c.text) for c in chunks]
        self.doc_len = [len(d) for d in self.docs]
        self.avgdl = (sum(self.doc_len) / len(self.docs)) if self.docs else 0.0

        # 计算词频（TF）
        self.freqs = [Counter(d) for d in self.docs]

        # 计算逆文档频率（IDF）
        df: Counter = Counter()
        for d in self.docs:
            for term in set(d):
                df[term] += 1
        n = len(self.docs)
        # IDF = ln(1 + (N - df + 0.5) / (df + 0.5))
        self.idf = {
            term: math.log(1 + (n - f + 0.5) / (f + 0.5))
            for term, f in df.items()
        }

    def search(self, query: str, top_k: int = 20) -> List[tuple[Chunk, float]]:
        """BM25 检索。

        对每个文档计算 BM25 得分，返回 top_k 条结果。
        得分为 0 的文档被过滤掉。

        Args:
            query: 检索查询
            top_k: 返回数量

        Returns:
            [(Chunk, score), ...] 按分数降序排列
        """
        if not self.docs:
            return []

        q_terms = tokenize(query)
        scores: List[float] = []

        # 对每个文档计算 BM25 得分
        for i, freq in enumerate(self.freqs):
            s = 0.0
            dl = self.doc_len[i] or 1

            for term in q_terms:
                if term not in freq:
                    continue

                idf = self.idf.get(term, 0.0)
                tf = freq[term]

                # BM25 公式
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                s += idf * (tf * (self.k1 + 1)) / denom

            scores.append(s)

        # 取 top_k
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])[:top_k]
        return [(self.chunks[i], scores[i]) for i in ranked if scores[i] > 0]
