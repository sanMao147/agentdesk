"""短期工作记忆管理。

策略：保留「running_summary + 最近 K 轮原文」
- round_count 超过 N 时触发摘要压缩
- 将旧轮次压成新 summary，只留最近 K 轮
- 存储优先 Redis（与 cache.py 同思路），连不上回退进程内 dict

ShortTermMemory 是无状态管理器，操作 WorkingMemory 数据对象。
"""
from __future__ import annotations

import json
from typing import Optional

from app.config import settings
from app.llm import chat
from app.memory.schema import WorkingMemory, now

# 会话级 TTL：1 天（秒）
_WM_TTL = 86400


class ShortTermMemory:
    """短期工作记忆管理器。

    负责会话级记忆的 CRUD 操作：
    - load: 加载会话记忆
    - persist: 保存会话记忆
    - append_turn: 追加一轮对话
    - need_summarize: 判断是否需要摘要压缩
    - build_context: 构建注入 prompt 的上下文
    - summarize: 执行摘要压缩

    存储后端：
    - 优先 Redis（如果配置了 redis_url 且可连接）
    - 回退进程内 dict（重启丢失，用于无 Redis 环境的演示）
    """

    def __init__(self) -> None:
        # 进程内存储（回退方案）
        self._mem: dict[str, str] = {}
        self._redis = None

        # 尝试连接 Redis
        url = getattr(settings, "redis_url", "")
        if url:
            try:
                import redis  # 可选依赖

                self._redis = redis.from_url(url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None  # 连接不上就退化为内存

        # 配置参数
        self.window_k = int(getattr(settings, "mem_short_window_k", 4))
        self.summarize_every_n = int(getattr(settings, "mem_summarize_every_n", 8))

    @staticmethod
    def _key(session_id: str) -> str:
        """生成 Redis 键名。"""
        return f"wm:{session_id}"

    def load(self, session_id: str) -> WorkingMemory:
        """加载会话的短期记忆。

        如果 Redis 不可用或键不存在，返回空的 WorkingMemory。
        """
        raw: Optional[str]
        if self._redis is not None:
            raw = self._redis.get(self._key(session_id))
        else:
            raw = self._mem.get(self._key(session_id))

        if raw:
            try:
                return WorkingMemory.from_dict(json.loads(raw))
            except Exception:
                pass  # 反序列化失败，返回空记忆
        return WorkingMemory(session_id=session_id)

    def persist(self, wm: WorkingMemory) -> None:
        """保存会话的短期记忆。

        Redis 设置 1 天 TTL，进程内存储无过期。
        """
        raw = json.dumps(wm.to_dict(), ensure_ascii=False)
        if self._redis is not None:
            self._redis.set(self._key(wm.session_id), raw, ex=_WM_TTL)
        else:
            self._mem[self._key(wm.session_id)] = raw

    def append_turn(self, wm: WorkingMemory, user_text: str, assistant_text: str) -> None:
        """追加一轮对话到工作记忆。

        依次添加 user 和 assistant 消息，并递增轮次计数。
        """
        wm.messages.append({"role": "user", "content": user_text, "ts": now()})
        wm.messages.append({"role": "assistant", "content": assistant_text, "ts": now()})
        wm.round_count += 1

    def need_summarize(self, wm: WorkingMemory) -> bool:
        """判断是否需要执行摘要压缩。

        条件：
        1. 轮次计数达到摘要阈值（summarize_every_n 的倍数）
        2. 消息数量超过窗口大小的两倍
        """
        return wm.round_count > 0 and wm.round_count % self.summarize_every_n == 0 \
            and len(wm.messages) > self.window_k * 2

    def build_context(self, wm: WorkingMemory) -> str:
        """构建注入 prompt 的短期上下文。

        格式：
        【对话摘要】{running_summary}

        【最近对话】
        user: ...
        assistant: ...
        ...
        """
        parts: list[str] = []
        if wm.running_summary:
            parts.append(f"【对话摘要】{wm.running_summary}")

        # 取最近 window_k * 2 条消息（即最近 K 轮对话）
        recent = wm.messages[-self.window_k * 2:]
        if recent:
            lines = [f"{m['role']}: {m['content']}" for m in recent]
            parts.append("【最近对话】\n" + "\n".join(lines))

        return "\n\n".join(parts)

    def summarize(self, wm: WorkingMemory) -> WorkingMemory:
        """压缩旧轮次为滚动摘要。

        处理流程：
        1. 将超过窗口的旧消息切分出来
        2. 调用 LLM 将旧消息压缩为简洁要点
        3. 只保留最近 K 轮原文 + 更新后的摘要

        压缩要求（System Prompt）：
        - 必须保留已确认的事实、用户偏好、未决问题
        - 不编造、不展开，输出 5 条以内
        """
        keep = self.window_k * 2
        old = wm.messages[:-keep] if len(wm.messages) > keep else []

        if not old:
            return wm  # 无需压缩

        # 将旧消息拼接为文本
        old_text = "\n".join(f"{m['role']}: {m['content']}" for m in old)

        system = (
            "把以下对话压缩成简洁要点，必须保留：已确认的事实、用户偏好、未决问题。"
            "不要编造，不要展开，输出 5 条以内。"
        )
        user = f"已有摘要：{wm.running_summary or '无'}\n\n待压缩对话：\n{old_text}"

        # 调用 LLM 生成摘要
        wm.running_summary = chat(system, user).strip()

        # 只保留最近 K 轮
        wm.messages = wm.messages[-keep:]
        return wm
