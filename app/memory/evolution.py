"""记忆演化机制。

负责记忆写入时的决策处理：
- INSERT: 新增记忆（无相似项）
- UPDATE: 去重更新（相似度过高，视为同一条，刷新元数据）
- CONFLICT_OVERWRITE: 冲突覆盖（同一事实有新值，覆盖旧值）

以及写入后的淘汰策略：
- TTL 过期淘汰（仅 event 类）
- 容量上限 LRU 淘汰

阈值与上限全部走 settings，可在 .env 配置。
冲突覆盖仅对 fact 生效且保留审计痕迹（不物理删旧值）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.config import settings
from app.memory.schema import KIND_EVENT, KIND_FACT, MemoryRecord, now

# 写入动作枚举
INSERT = "insert"
UPDATE = "update"               # 去重：同一条，刷新 use_count/updated_at
CONFLICT_OVERWRITE = "conflict_overwrite"  # 同一事实新取值：覆盖，旧值留痕


@dataclass
class WriteDecision:
    """写入决策结果。

    Attributes:
        action: 动作类型（insert/update/conflict_overwrite）
        target: 被命中的旧记录（UPDATE/CONFLICT 时使用）
    """
    action: str
    target: Optional[MemoryRecord] = None


class MemoryEvolution:
    """记忆演化处理器。

    参数来源：
    - dedup: 去重阈值（默认 0.92，余弦相似度 >= 此值视为同一条）
    - conflict: 冲突阈值（默认 0.80，相似度 >= 此值且同类型视为冲突）
    - event_ttl: 事件记忆过期时间（默认 30 天）
    - max_per_user: 每用户记忆上限（默认 500 条）
    """

    def __init__(self, store) -> None:
        self.store = store
        self.dedup = float(getattr(settings, "mem_dedup_threshold", 0.92))
        self.conflict = float(getattr(settings, "mem_conflict_threshold", 0.80))
        self.event_ttl = float(getattr(settings, "mem_event_ttl_days", 30)) * 86400.0
        self.max_per_user = int(getattr(settings, "mem_max_per_user", 500))

    def resolve_write(self, new: MemoryRecord) -> WriteDecision:
        """根据与已有记忆的最相似项决定写入动作。

        决策逻辑：
        1. 无命中 → INSERT（新增）
        2. 相似度 >= dedup → UPDATE（去重，刷新元数据）
        3. 相似度 >= conflict 且同类型为 fact → CONFLICT_OVERWRITE（冲突覆盖）
        4. 其他 → INSERT（新增，可能是不同的记忆）

        Args:
            new: 待写入的新记忆记录

        Returns:
            WriteDecision: 决策结果
        """
        hits = self.store.search(new.user_id, new.embedding, top_k=1)

        if not hits:
            return WriteDecision(INSERT)

        rec, sim = hits[0]

        if sim >= self.dedup:
            # 高度相似 → 去重更新
            return WriteDecision(UPDATE, rec)

        if sim >= self.conflict and rec.kind == new.kind == KIND_FACT:
            # 中等相似的同类事实 → 冲突覆盖
            return WriteDecision(CONFLICT_OVERWRITE, rec)

        # 新的独立记忆
        return WriteDecision(INSERT)

    def apply(self, new: MemoryRecord) -> MemoryRecord:
        """执行写入决策，返回最终落库的现行记录。

        三种决策的执行逻辑：
        1. UPDATE: 递增 use_count，更新时间戳，写回旧记录
        2. CONFLICT_OVERWRITE: 旧记录标记 superseded_by（保留审计），
           新记录 version = 旧 version + 1，写入新记录
        3. INSERT: 直接写入新记录
        """
        decision = self.resolve_write(new)

        if decision.action == UPDATE and decision.target is not None:
            # 去重更新：刷新元数据
            old = decision.target
            old.use_count += 1
            old.updated_at = now()
            old.last_used_at = now()
            self.store.upsert(old)
            return old

        if decision.action == CONFLICT_OVERWRITE and decision.target is not None:
            # 冲突覆盖：旧值留审计痕迹
            old = decision.target
            old.superseded_by = new.mem_id  # 标记被新值取代
            old.updated_at = now()
            self.store.upsert(old)

            # 新值版本递增
            new.version = old.version + 1
            self.store.upsert(new)
            return new

        # INSERT: 直接写入
        self.store.upsert(new)
        return new

    def evict_if_needed(self, user_id: str) -> List[str]:
        """执行淘汰策略，返回被删除的 mem_id 列表。

        淘汰顺序：
        1. TTL 过期：event 类型且创建时间超过 event_ttl
        2. 容量上限：LRU 淘汰（last_used_at 最早 + use_count 加权保护热点）

        注意：只对现行记忆（superseded_by 为 None）执行淘汰。
        """
        recs = [r for r in self.store.list_by_user(user_id) if r.superseded_by is None]
        to_delete: List[str] = []
        t = now()

        # 1) TTL 过期淘汰（仅 event 类）
        survivors: List[MemoryRecord] = []
        for r in recs:
            if r.kind == KIND_EVENT and (t - r.created_at) > self.event_ttl:
                to_delete.append(r.mem_id)
            else:
                survivors.append(r)

        # 2) 容量上限 LRU 淘汰
        # 排序键：last_used_at + use_count * 3600（使用次数越多越难被淘汰）
        if len(survivors) > self.max_per_user:
            survivors.sort(key=lambda r: (r.last_used_at + r.use_count * 3600.0))
            overflow = len(survivors) - self.max_per_user
            to_delete.extend(r.mem_id for r in survivors[:overflow])

        if to_delete:
            self.store.delete(user_id, to_delete)

        return to_delete
