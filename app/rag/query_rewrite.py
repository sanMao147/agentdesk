"""查询改写（Multi-Query）。

将用户的原始问题扩展成多条语义等价或聚焦子意图的检索查询，
提升向量检索的召回率。

改写策略：
- 有 LLM 时：让模型生成同义/拆解变体
- 离线时：回退为原问题（不进行改写）

改写示例：
    原问题："项目有多少个文档？"
    改写结果：["项目有多少个文档？", "文档数量统计", "知识库中的文档总数"]
"""
from __future__ import annotations

import json
from typing import List

from app.config import settings
from app.llm import chat


def rewrite(query: str, n: int = 3) -> List[str]:
    """查询改写。

    将用户问题扩展为 n 条检索查询变体。
    原问题始终保留在首位，确保原始语义不丢失。

    Args:
        query: 用户原始问题
        n: 生成的变体数量

    Returns:
        查询列表（首元素为原问题）
    """
    if not settings.use_llm:
        return [query]  # 离线模式直接返回原问题

    system = (
        "你是检索查询改写器。把用户问题改写成 {n} 条语义等价或"
        "聚焦子意图的检索查询，便于向量/关键词检索。"
        "只输出 JSON 数组，例如 [\"q1\",\"q2\"]。".format(n=n)
    )

    try:
        raw = chat(system, query)
        # 从模型输出中提取 JSON 数组
        start, end = raw.find("["), raw.rfind("]")
        variants = json.loads(raw[start: end + 1])
        variants = [v for v in variants if isinstance(v, str) and v.strip()]

        # 原问题保留在首位，去重，限制总数
        out = [query] + [v for v in variants if v != query]
        return out[: n + 1]
    except Exception:
        return [query]  # 改写失败则回退原问题
