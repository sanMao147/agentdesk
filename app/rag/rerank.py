"""Rerank（重排）模块。

将召回回来的候选文档按「与 query 的相关性」重新排序，
决定最终喂给 writer 的证据顺序（top_k）。

重排质量直接决定答案质量，是 RAG 管线的关键环节。

两种重排方法：
1. 离线兜底：词项重叠数 + IDF 同分裁决（零依赖，可离线）
2. 可插拔 cross-encoder：设 RERANK_MODEL 环境变量时启用
"""
from __future__ import annotations

import math
import os
from collections import Counter
from typing import List

from app.rag.store import Chunk
from app.rag.tokenize import tokenize

# ── 可插拔 cross-encoder 相关 ──
_CE_TRIED = False   # 是否已尝试加载
_CE_MODEL = None     # cross-encoder 实例


def _get_cross_encoder():
    """惰性加载 cross-encoder 模型。

    只尝试一次，失败则永久回退到离线打分。
    通过环境变量 RERANK_MODEL 控制是否启用。
    """
    global _CE_TRIED, _CE_MODEL
    if _CE_TRIED:
        return _CE_MODEL

    _CE_TRIED = True
    model_name = os.environ.get("RERANK_MODEL", "").strip()
    if not model_name:
        return None  # 未配置 → 走离线兜底

    try:
        from sentence_transformers import CrossEncoder  # 可选依赖
        _CE_MODEL = CrossEncoder(model_name)
    except Exception:
        _CE_MODEL = None  # 依赖缺失或加载失败 → 回退

    return _CE_MODEL


def _candidate_idf(candidates: List[Chunk]) -> dict:
    """在候选池内统计 IDF。

    与标准 IDF 不同，这里只在候选文档集合内统计，
    使区分词（罕见词）获得更高权重。

    Args:
        candidates: 候选文档列表

    Returns:
        {term: idf_score} 字典
    """
    n = len(candidates)
    df: Counter = Counter()
    for c in candidates:
        for term in set(tokenize(c.text)):
            df[term] += 1
    # IDF = ln(1 + (N - df + 0.5) / (df + 0.5))
    return {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}


def _lexical_score(query: str, text: str, idf: dict, idf_total: float) -> float:
    """词法相关性打分。

    score = 命中 query 词数 + IDF 加成(∈[0,1))

    设计：
    - 整数部分 = 命中词数（主键，保证稳健性）
    - 小数部分 = IDF 加成（同分裁决，不跨越整数边界）
    - 加成封顶 0.999，绝不把匹配更多词的文档挤下去

    这样做的好处：
    - 主键排序稳健（匹配词数多的文档排名更靠前）
    - 同分情况下用 IDF 区分（区分词多的排名靠前）
    - 完全零依赖，可离线运行
    """
    q_terms = set(tokenize(query))
    if not q_terms:
        return 0.0

    matched = q_terms & set(tokenize(text))
    base = float(len(matched))

    # IDF 加成：归一化到 [0, 1)
    bonus = (sum(idf.get(t, 0.0) for t in matched) / idf_total) if idf_total > 0 else 0.0

    return base + min(bonus, 0.999)


def rerank(query: str, candidates: List[Chunk], top_k: int = 5) -> List[tuple[Chunk, float]]:
    """重排候选文档。

    优先使用 cross-encoder（更准确但需要 GPU/大模型），
    不可用时回退到词法打分（零依赖、可离线）。

    Args:
        query: 检索查询
        candidates: 候选文档列表
        top_k: 返回数量

    Returns:
        [(Chunk, score), ...] 按分数降序排列
    """
    if not candidates:
        return []

    # 尝试 cross-encoder
    ce = _get_cross_encoder()
    if ce is not None:
        try:
            # cross-encoder 逐对打分
            scores = ce.predict([(query, c.text) for c in candidates])
            scored = [(c, float(s)) for c, s in zip(candidates, scores)]
            scored.sort(key=lambda x: -x[1])
            return scored[:top_k]
        except Exception:
            pass  # 运行期失败 → 落回离线兜底

    # —— 离线兜底：词法打分 ——
    idf = _candidate_idf(candidates)
    idf_total = sum(idf.get(t, 0.0) for t in set(tokenize(query)))

    scored = [(c, _lexical_score(query, c.text, idf, idf_total)) for c in candidates]
    scored.sort(key=lambda x: -x[1])

    return scored[:top_k]
