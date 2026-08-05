"""LangGraph 图构建与执行。

本模块负责：
1. 组装 LangGraph StateGraph，定义节点间的执行顺序和条件边
2. 提供 run_query 入口函数，执行完整的 Agent 编排流程

图结构：
    memory_retrieve → planner → retrieval → tool → writer → critic
                                                         ↓ (条件)
                                              忠实/超时 → memory_write → (条件) → END
                                                              ↓ 需要摘要
                                                           summarize → END

降级策略：langgraph 不可用时退化为等价的顺序+循环执行，保证任何环境可演示。
"""
from __future__ import annotations

import uuid

from app.config import settings
from app.graph.state import AgentState
from app.graph.nodes import (
    memory_retrieve_node, planner_node, retrieval_node, tool_node,
    writer_node, critic_node, should_retry,
    memory_write_node, summarize_node, need_summarize_edge,
)


def _build_compiled():
    """构建并编译 LangGraph 状态图。

    定义所有节点和边：
    1. 添加节点：每个节点对应一个处理函数
    2. 设置入口点：从 memory_retrieve 开始
    3. 添加普通边：定义节点间的固定顺序
    4. 添加条件边：根据条件动态选择下一节点

    条件边说明：
    - critic → should_retry: 评判后判断是重试还是结束
    - memory_write → need_summarize_edge: 写入后判断是否需要摘要压缩
    """
    from langgraph.graph import StateGraph, END

    g = StateGraph(AgentState)

    # 添加所有节点
    g.add_node("memory_retrieve", memory_retrieve_node)
    g.add_node("planner", planner_node)
    g.add_node("retrieval", retrieval_node)
    g.add_node("tool", tool_node)
    g.add_node("writer", writer_node)
    g.add_node("critic", critic_node)
    g.add_node("memory_write", memory_write_node)
    g.add_node("summarize", summarize_node)

    # 设置入口
    g.set_entry_point("memory_retrieve")

    # 定义主执行链路（固定顺序）
    g.add_edge("memory_retrieve", "planner")
    g.add_edge("planner", "retrieval")
    g.add_edge("retrieval", "tool")
    g.add_edge("tool", "writer")
    g.add_edge("writer", "critic")

    # 条件边 1：评判后决定重试或结束
    # - retry → 回到 retrieval 节点重新检索
    # - end → 进入 memory_write 节点
    g.add_conditional_edges("critic", should_retry,
                            {"retry": "retrieval", "end": "memory_write"})

    # 条件边 2：记忆写入后决定是否需要摘要压缩
    # - summarize → 进入 summarize 节点
    # - end → 直接结束
    g.add_conditional_edges("memory_write", need_summarize_edge,
                            {"summarize": "summarize", "end": END})

    # 摘要压缩后结束
    g.add_edge("summarize", END)

    return g.compile()


# 全局编译缓存（懒加载，避免每次请求都重新编译）
_compiled = None


def _init_state(query: str, user_id: str, session_id: str) -> AgentState:
    """初始化 Agent 状态。

    创建初始状态对象，包含基础信息和空的执行轨迹。
    """
    return {"query": query, "user_id": user_id, "session_id": session_id,
            "trace": [], "iterations": 0}


def _run_sequential(state: AgentState) -> AgentState:
    """顺序执行（降级模式）。

    当 langgraph 不可用时，使用简单的顺序+循环执行模拟图的行为。
    逻辑与 LangGraph 完全一致，保证结果相同。

    执行流程：
    1. memory_retrieve → planner
    2. 循环：retrieval → tool → writer → critic，直到 should_retry 返回 "end"
    3. memory_write
    4. 如果需要摘要 → summarize
    """
    state.update(memory_retrieve_node(state))
    state.update(planner_node(state))

    # 重试循环
    while True:
        state.update(retrieval_node(state))
        state.update(tool_node(state))
        state.update(writer_node(state))
        state.update(critic_node(state))
        if should_retry(state) == "end":
            break

    # 记忆写入
    state.update(memory_write_node(state))

    # 摘要压缩
    if need_summarize_edge(state) == "summarize":
        state.update(summarize_node(state))

    return state


def run_query(query: str, user_id: str = "anonymous",
              session_id: str | None = None) -> AgentState:
    """执行查询（主入口）。

    完整执行 Agent 编排流程，包括：
    1. 记忆召回 → 查询改写 → 混合检索 → 工具调用 → 答案生成 → 忠实度评判
    2. 根据评判结果决定是否重试
    3. 记忆写入和摘要压缩

    容错策略：
    - 优先使用 LangGraph 编译模式
    - 失败时自动降级为顺序执行模式
    - 最后尝试写 trace 日志（失败不影响返回）

    Args:
        query: 用户问题文本
        user_id: 用户标识（默认 "anonymous"）
        session_id: 会话标识（可选，不传则自动生成）

    Returns:
        AgentState: 包含完整执行结果的状态字典
    """
    # 自动生成 session_id（如果未提供）
    session_id = session_id or uuid.uuid4().hex
    global _compiled

    try:
        # 优先使用 LangGraph 编译模式
        if _compiled is None:
            _compiled = _build_compiled()
        result = _compiled.invoke(_init_state(query, user_id, session_id))
    except Exception:
        # 降级：使用顺序执行模式
        result = _run_sequential(_init_state(query, user_id, session_id))

    # 异步落盘执行轨迹（用于调试和评测）
    try:
        from app.graph.trace_log import log_trace
        log_trace(result)  # 写入 eval/reports/traces.jsonl
    except Exception:
        pass  # 落盘失败不影响主流程

    return result
