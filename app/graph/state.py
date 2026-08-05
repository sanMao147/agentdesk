"""LangGraph 全局 State 定义。

AgentState 是 LangGraph 图中所有节点共享的状态对象。
每个节点读取状态中的部分字段，处理后将结果写回状态。

状态字段按功能分组：
- 基础信息：query（用户问题）、plan（改写计划）、queries（改写后的查询列表）
- 检索结果：evidence（证据片段列表）
- 工具结果：tool_results（工具调用结果列表）
- 生成结果：answer（答案）、citations（引用来源）
- 评判结果：verify（忠实度评判）
- 执行控制：iterations（迭代次数）、trace（执行轨迹）
- 记忆层：user_id、session_id、working_memory、recalled_memories、memory_writes

所有字段均为 total=False，即可以只提供部分字段（LangGraph 会自动合并）。
"""
from __future__ import annotations

from typing import List, TypedDict

from app.rag.retriever import Evidence


class AgentState(TypedDict, total=False):
    """Agent 全局状态定义。

    LangGraph 的节点通过读取和写入这个字典来传递数据。
    每个节点只关注自己需要的字段，不必关心其他字段。
    """
    # —— 基础信息 ——
    query: str                              # 用户原始问题
    plan: str                               # 查询改写计划（多条查询用 " | " 拼接）
    queries: List[str]                      # 改写后的多条检索查询

    # —— 检索结果 ——
    evidence: List[Evidence]                # 检索到的证据片段（含向量分数）

    # —— 工具结果 ——
    tool_results: List[dict]                # 工具调用结果列表

    # —— 生成结果 ——
    answer: str                             # 最终生成的答案
    citations: List[str]                    # 答案引用的 chunk_id 列表

    # —— 评判结果 ——
    verify: dict                            # 忠实度评判结果（faithful, score, method 等）

    # —— 执行控制 ——
    iterations: int                         # 已执行的迭代次数（用于重试判定）
    trace: List[dict]                       # 执行轨迹（每个节点的输入输出摘要）

    # —— 记忆层 ——
    user_id: str                            # 用户标识（用于记忆隔离）
    session_id: str                         # 会话标识（用于多轮对话上下文）
    working_memory: dict                    # 短期工作记忆（对话历史 + 摘要）
    recalled_memories: List[dict]           # 本轮召回的长期记忆
    memory_writes: List[dict]               # 本轮新写入的记忆
