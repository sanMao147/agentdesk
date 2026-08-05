"""记忆层数据模型定义。

本模块定义了记忆系统的核心数据结构：
- MemoryRecord: 一条长期记忆记录（含演化所需的审计字段）
- WorkingMemory: 一个会话的短期工作记忆（对话 buffer + 滚动 summary）

记忆 ID 设计：使用 (user_id + 归一化文本) 的 MD5 哈希作为 mem_id，
使「同一用户的同一句话」天然定位到同一条记忆，便于去重与 upsert 覆盖。

记忆类型：
- KIND_FACT: 语义记忆（事实类，如"我是张三"）
- KIND_PREFERENCE: 偏好记忆（如"我喜欢蓝色"）
- KIND_EVENT: 情景记忆（如"昨天完成了报告"）
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from typing import List, Optional

# —— 记忆类型常量 ——
KIND_FACT = "fact"           # 事实：稳定的个人信息
KIND_PREFERENCE = "preference"  # 偏好：个人喜好
KIND_EVENT = "event"         # 事件：发生过的事情（可较快过期）
VALID_KINDS = {KIND_FACT, KIND_PREFERENCE, KIND_EVENT}


def now() -> float:
    """获取当前时间戳（秒）。"""
    return time.time()


def normalize_text(text: str) -> str:
    """归一化文本：转小写 + 合并空格。

    使 "Hello  World" 与 "hello world" 被视为相同内容。
    """
    return " ".join(text.lower().split())


def make_mem_id(user_id: str, text: str) -> str:
    """生成记忆 ID。

    格式：mem:{md5_hash}
    基于 user_id + 归一化文本生成，确保同一用户的同一句话映射到同一 ID。
    """
    raw = f"{user_id}:{normalize_text(text)}"
    return "mem:" + hashlib.md5(raw.encode("utf-8")).hexdigest()


@dataclass
class MemoryRecord:
    """长期记忆记录。

    包含完整的生命周期管理字段：
    - 标识：mem_id（唯一标识）、user_id（所属用户）
    - 内容：text（记忆文本）、kind（类型）
    - 向量：embedding（用于相似度检索）
    - 时间：created_at、updated_at、last_used_at
    - 使用：use_count（被召回次数）
    - 演化：version（版本号）、superseded_by（被哪条新记忆取代）

    演化机制：
    - 冲突覆盖时，旧记录的 superseded_by 指向新记录的 mem_id
    - 新记录的 version = 旧记录的 version + 1
    - 旧记录不会物理删除，保留完整的审计链
    """
    user_id: str
    text: str
    kind: str = KIND_FACT
    embedding: List[float] = field(default_factory=list)
    mem_id: str = ""
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)
    last_used_at: float = field(default_factory=now)
    use_count: int = 0
    version: int = 1
    superseded_by: Optional[str] = None

    def __post_init__(self) -> None:
        """数据类初始化后处理。

        - 校验记忆类型（无效类型回退为 fact）
        - 自动生成 mem_id（如果未指定）
        """
        if self.kind not in VALID_KINDS:
            self.kind = KIND_FACT
        if not self.mem_id:
            self.mem_id = make_mem_id(self.user_id, self.text)

    def to_payload(self) -> dict:
        """转换为存储 payload（不含向量，向量单独存储）。

        用于写入 Qdrant payload 或 JSON 序列化。
        """
        d = asdict(self)
        d.pop("embedding", None)
        return d

    @classmethod
    def from_payload(cls, payload: dict, embedding: Optional[List[float]] = None) -> "MemoryRecord":
        """从存储 payload 反序列化。

        Args:
            payload: 存储的字段字典
            embedding: 向量数据（单独存储，从外部注入）
        """
        data = dict(payload)
        return cls(
            user_id=data.get("user_id", ""),
            text=data.get("text", ""),
            kind=data.get("kind", KIND_FACT),
            embedding=embedding or [],
            mem_id=data.get("mem_id", ""),
            created_at=float(data.get("created_at", now())),
            updated_at=float(data.get("updated_at", now())),
            last_used_at=float(data.get("last_used_at", now())),
            use_count=int(data.get("use_count", 0)),
            version=int(data.get("version", 1)),
            superseded_by=data.get("superseded_by"),
        )


@dataclass
class WorkingMemory:
    """短期工作记忆（会话级）。

    存储一个会话的对话历史和滚动摘要：
    - session_id: 会话标识
    - messages: 最近的对话轮次 [{role, content, ts}]
    - running_summary: 历史轮次的滚动摘要（由 LLM 压缩生成）
    - round_count: 对话轮次计数（用于触发摘要压缩）

    记忆策略：保留「running_summary + 最近 K 轮原文」，
    超过阈值时自动将旧轮次压缩进 summary。
    """
    session_id: str
    messages: List[dict] = field(default_factory=list)   # [{"role","content","ts"}]
    running_summary: str = ""
    round_count: int = 0

    def to_dict(self) -> dict:
        """序列化为字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WorkingMemory":
        """从字典反序列化。"""
        return cls(
            session_id=d.get("session_id", ""),
            messages=list(d.get("messages", [])),
            running_summary=d.get("running_summary", ""),
            round_count=int(d.get("round_count", 0)),
        )
