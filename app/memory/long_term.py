"""长期记忆管理。

负责记忆的"生产"与"消费"：
- 生产（写入）：从对话中抽取值得记住的信息 → 向量化 → 经演化处理后写入
- 消费（检索）：根据当前问题召回相关记忆 → 注入到 prompt 中

抽取策略：规则触发（零成本、可解释）
命中自述型模式（"我是…""我只看…""记住…"）即抽取该子句为一条记忆。
后续可平滑升级为 LLM 结构化抽取（接口不变）。
"""
from __future__ import annotations

import re
from typing import List

from app.llm import embed_query, embed_texts
from app.memory.evolution import MemoryEvolution
from app.memory.schema import (
    KIND_EVENT,
    KIND_FACT,
    KIND_PREFERENCE,
    MemoryRecord,
    now,
)
from app.memory.store import get_memory_store

# 子句切分符（按标点切分对话为独立子句）
_SPLIT = re.compile(r"[，。；、,.;\n]+")

# 抽取规则：正则模式 → 记忆类型
# 命中即把该子句作为一条记忆
_RULES = [
    # 事实类：个人身份/职业
    (re.compile(r"(我是|我叫|我的名字|我来自|我在.{0,8}(工作|上班)|我的职业)"), KIND_FACT),
    # 偏好类：个人喜好/习惯
    (re.compile(r"(只看|只关注|只要|偏好|喜欢|习惯|以后都|默认用|我倾向)"), KIND_PREFERENCE),
    # 事实类：显式要求记住
    (re.compile(r"(记住|请记住|备注|提醒我)"), KIND_FACT),
    # 事件类：发生过的事情
    (re.compile(r"(上次|刚才|今天|昨天).{0,12}(完成|提交|发生|做了)"), KIND_EVENT),
]

# 问句特征：以疑问词结尾的子句不抽取（避免把问题当事实存进去）
_QUESTION = re.compile(r"(吗|呢|怎么|如何|为什么|多少|哪些|是不是|？|\?)\s*$")


class LongTermMemory:
    """长期记忆管理器。

    封装记忆的完整生命周期：
    1. extract: 从对话中抽取值得记住的信息
    2. write: 向量化 + 演化处理 + 写入存储
    3. retrieve: 根据查询召回相关记忆

    演化处理包括：
    - 去重：相似度 >= 阈值视为同一条，更新而非新增
    - 冲突：同一事实有新值时覆盖旧值（保留审计链）
    - 淘汰：TTL 过期 + 容量上限 LRU
    """

    def __init__(self) -> None:
        self.store = get_memory_store()
        self.evolution = MemoryEvolution(self.store)

    # ---------- 生产（写入） ----------

    def extract(self, query: str, answer: str = "") -> List[dict]:
        """从用户输入里抽取值得长期记住的偏好/事实。

        策略：规则触发
        1. 按标点切分 query 为子句
        2. 对每个子句匹配抽取规则
        3. 排除问句（避免把问题当事实存）
        4. 去重后返回

        返回格式：[{"kind": "fact", "text": "我是张三"}, ...]
        """
        items: List[dict] = []
        seen = set()

        for clause in _SPLIT.split(query or ""):
            c = clause.strip()
            if len(c) < 3 or c in seen:
                continue

            for pat, kind in _RULES:
                if pat.search(c) and not _QUESTION.search(c):
                    items.append({"kind": kind, "text": c})
                    seen.add(c)
                    break

        return items

    def write(self, user_id: str, items: List[dict]) -> List[MemoryRecord]:
        """将抽取项写入长期记忆。

        流程：
        1. 批量向量化所有待写入的文本
        2. 为每条记录创建 MemoryRecord
        3. 调用 evolution.apply() 执行演化决策（去重/冲突/新增）
        4. 触发容量淘汰（evict_if_needed）

        返回实际写入的记录列表（可能包含更新的旧记录）。
        """
        if not user_id or not items:
            return []

        texts = [it["text"] for it in items]
        vectors = embed_texts(texts)

        written: List[MemoryRecord] = []
        for it, vec in zip(items, vectors):
            rec = MemoryRecord(user_id=user_id, text=it["text"],
                               kind=it.get("kind", KIND_FACT), embedding=vec)
            written.append(self.evolution.apply(rec))

        # 容量淘汰
        self.evolution.evict_if_needed(user_id)

        return written

    # ---------- 消费（检索） ----------

    def retrieve(self, user_id: str, query: str, top_k: int = 3) -> List[MemoryRecord]:
        """召回与当前问题相关的长期记忆。

        流程：
        1. 对 query 做向量化
        2. 在记忆存储中做余弦相似度检索
        3. 更新命中记忆的热度指标（last_used_at, use_count）
        4. 回写更新后的记录

        返回命中的记忆记录列表（按相似度降序）。
        """
        if not user_id or not query:
            return []

        qv = embed_query(query)
        hits = self.store.search(user_id, qv, top_k=top_k)

        recalled: List[MemoryRecord] = []
        for rec, _score in hits:
            # 更新热度指标
            rec.last_used_at = now()
            rec.use_count += 1
            self.store.upsert(rec)
            recalled.append(rec)

        return recalled
