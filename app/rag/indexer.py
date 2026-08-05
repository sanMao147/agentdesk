"""文档索引构建模块。

负责将 data/docs 目录下的文档（.txt / .md）切割为 chunk，
并生成向量索引落盘。

流程：
1. 扫描 data/docs 目录下的所有 .txt 和 .md 文件
2. 按 chunk_size 切割文档为小段，带 overlap 保证上下文完整
3. 批量计算每个 chunk 的 embedding
4. 写入向量存储并保存为 JSON 文件

可通过 API 触发重建（POST /api/index/rebuilds）。
"""
from __future__ import annotations

import os
from typing import List

from app.config import settings
from app.llm import embed_texts
from app.rag.store import Chunk
from app.rag.store_factory import get_store

# 索引文件持久化路径
INDEX_PATH = "data/index/store.json"


def split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """简单按字符切割，带 overlap。

    切割策略：
    - 按固定字符数切割
    - 相邻 chunk 有 overlap 个字符重叠，避免语义断裂
    - 后续可升级为语义边界切割（按段落/句子）

    Args:
        text: 待切割的文本
        chunk_size: 每段最大字符数
        overlap: 相邻段重叠字符数

    Returns:
        切割后的文本块列表
    """
    text = text.strip()
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap  # 回退 overlap 字符保证上下文
    return chunks


def build_index(docs_dir: str = "data/docs"):
    """从文档目录构建索引。

    处理流程：
    1. 遍历目录下所有 .txt / .md 文件
    2. 对每个文件进行文本切割
    3. 批量向量化所有 chunk
    4. 写入存储并持久化

    Chunk ID 格式：{filename}#{index}
    例如 sample_faq.md#0, sample_faq.md#1, ...

    Args:
        docs_dir: 文档目录路径

    Returns:
        VectorStore: 构建好的向量存储实例
    """
    store = get_store()
    all_chunks: List[Chunk] = []

    # 扫描并切割文档
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.lower().endswith((".txt", ".md")):
            continue
        path = os.path.join(docs_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        pieces = split_text(content, settings.chunk_size, settings.chunk_overlap)
        for i, piece in enumerate(pieces):
            all_chunks.append(Chunk(
                doc_id=fname,
                chunk_id=f"{fname}#{i}",
                text=piece,
                embedding=[],
            ))

    # 批量计算 embedding
    embeddings = embed_texts([c.text for c in all_chunks])
    for c, emb in zip(all_chunks, embeddings):
        c.embedding = emb

    # 写入存储并持久化
    store.add(all_chunks)
    store.save(INDEX_PATH)

    return store
