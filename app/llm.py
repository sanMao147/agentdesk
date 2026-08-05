"""LLM 与 Embedding 的统一封装层。

设计哲学：**优雅降级**。

有 OPENAI_API_KEY 时 → 调用真实 API（GPT-4o / text-embedding-3-small）
无 OPENAI_API_KEY 时 → 确定性 fallback（哈希向量 + 模板拼接）

这使得系统在无网络、无 API Key 的环境下也能端到端跑通，
非常适合本地开发和演示。

Embedding 缓存策略：
- Redis 可用时 → Redis 缓存（跨进程共享，持久化）
- Redis 不可用时 → 内存缓存（进程内有效）
- 缓存 Key = hash(text)，避免重复计算

缓存命中流程：
1. 对每个文本检查缓存
2. 命中 → 直接使用，跳过 API 调用
3. 未命中 → 批量调用 _embed_raw()，结果回填缓存
"""
from __future__ import annotations

import hashlib
from typing import List

import numpy as np

from app.config import settings

# Embedding 维度（离线 fallback 使用 256 维，真实模型可能更高）
EMBED_DIM = 256


def _tokens(text: str) -> List[str]:
    """离线分词器（仅用于 fallback embedding）。

    策略：空格分词 + 字符 bigram
    - "hello world" → ["hello", "world", "hell", "ello", "llo ", ...]

    注意：这不是真正的 NLP 分词，仅为哈希向量提供稳定的 token 序列。
    真实 embedding 由模型内部处理。
    """
    text = text.lower()
    toks = text.split()
    chars = [c for c in text if not c.isspace()]
    bigrams = [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]
    return toks + bigrams


def _hash_embedding(text: str, dim: int = EMBED_DIM) -> List[float]:
    """基于哈希的确定性 Embedding（离线 fallback）。

    算法：
    1. 将文本分词为 tokens
    2. 对每个 token 计算 MD5 哈希，映射到 dim 维空间的某个位置
    3. 累加各位置的权重
    4. L2 归一化

    特点：
    - 确定性：相同文本始终得到相同向量
    - 无需外部依赖
    - 语义质量有限，但足以演示检索流程

    这是经典的 "random indexing" / "hashing trick" 思想。
    """
    vec = np.zeros(dim, dtype=np.float32)
    for token in _tokens(text):
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def _embed_raw(texts: List[str]) -> List[List[float]]:
    """原始 Embedding 计算（无缓存）。

    根据 settings.use_llm 选择路径：
    - True → 调用 OpenAI Embedding API
    - False → 使用哈希 fallback

    API 调用配置：
    - timeout=30s：防止接口挂起导致前端无限转圈
    - max_retries=1：快速失败，不做重试
    """
    if not settings.use_llm:
        return [_hash_embedding(t) for t in texts]

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=30.0,
        max_retries=1,
    )
    resp = client.embeddings.create(model=settings.embedding_model, input=texts)
    return [d.embedding for d in resp.data]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """带缓存的批量 Embedding。

    优化策略：
    1. 逐个检查缓存，分离命中和未命中
    2. 仅对未命中的文本调用 _embed_raw()（批量计算）
    3. 将新计算结果回填缓存

    当文本有重复时，此策略可大幅减少 API 调用次数。

    Args:
        texts: 待计算的文本列表

    Returns:
        与输入文本一一对应的向量列表
    """
    from app.rag.cache import cache

    out: List[List[float]] = [None] * len(texts)  # type: ignore
    miss_idx, miss_texts = [], []

    # 第一遍：检查缓存
    for i, t in enumerate(texts):
        c = cache.get(t)
        if c is not None:
            out[i] = c  # 缓存命中
        else:
            miss_idx.append(i)
            miss_texts.append(t)

    # 第二遍：批量计算未命中的
    if miss_texts:
        computed = _embed_raw(miss_texts)
        for i, t, vec in zip(miss_idx, miss_texts, computed):
            out[i] = vec
            cache.set(t, vec)  # 回填缓存

    return out


def embed_query(text: str) -> List[float]:
    """单文本 Embedding（带缓存）。

    便捷方法，内部委托给 embed_texts()。

    Args:
        text: 待计算的文本

    Returns:
        向量列表
    """
    return embed_texts([text])[0]


def chat(system: str, user: str) -> str:
    """对话接口（带离线 fallback）。

    根据 settings.use_llm 选择路径：
    - True → 调用真实 Chat Completions API
    - False → 返回模板拼接的占位文本

    调用配置：
    - temperature=0.2：低温度，追求确定性输出（适合 RAG 场景）
    - timeout=30s：30 秒超时保护
    - max_retries=1：单次重试

    Args:
        system: 系统提示词（角色定义）
        user: 用户消息

    Returns:
        模型生成的文本内容
    """
    if not settings.use_llm:
        # 离线模式：返回模板，让前端看到"有东西"
        return "[offline] no OPENAI_API_KEY; stitched answer from evidence:\n\n" + user

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=30.0,
        max_retries=1,
    )
    resp = client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""
