"""执行链路日志记录。

每次 run_query 结束后，将本轮执行的 trace 信息追加写入 JSONL 文件。
一行一条记录，便于 grep/回放分析。

设计：
- 默认开启（settings.trace_log / 环境变量 TRACE_LOG；设 0 关闭）
- 只写 JSON 可序列化字段（evidence 等含 dataclass 的不写）
- 任何异常都吞掉，绝不影响主问答流程
"""
from __future__ import annotations

import json
import os
import time

from app.config import settings

# 日志文件路径
TRACE_PATH = "eval/reports/traces.jsonl"


def log_trace(state: dict) -> None:
    """记录执行轨迹到 JSONL 文件。

    从最终状态中提取关键信息（不含不可序列化的 dataclass 对象），
    追加写入到 TRACE_PATH。

    记录字段：
    - ts: 时间戳
    - user_id: 用户标识
    - session_id: 会话标识
    - query: 用户问题
    - answer: 生成的答案
    - iterations: 迭代次数
    - verify: 忠实度评判结果
    - citations: 引用来源
    - recalled_memories: 召回的记忆
    - memory_writes: 写入的记忆
    - trace: 执行轨迹（每个节点的摘要）
    """
    if not getattr(settings, "trace_log", True):
        return

    try:
        os.makedirs(os.path.dirname(TRACE_PATH), exist_ok=True)
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "query": state.get("query"),
            "answer": state.get("answer"),
            "iterations": state.get("iterations"),
            "verify": state.get("verify"),
            "citations": state.get("citations"),
            "recalled_memories": state.get("recalled_memories"),
            "memory_writes": state.get("memory_writes"),
            "trace": state.get("trace"),
        }
        with open(TRACE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 落盘失败不影响主流程
