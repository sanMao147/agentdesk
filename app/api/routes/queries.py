"""查询执行路由。

核心端点：POST /api/queries
功能：接收用户查询，调用 LangGraph Agent 编排执行完整的问答流程。

流程包括：
1. 记忆召回（短期工作记忆 + 长期记忆）
2. 查询改写（Multi-Query 扩展）
3. 混合检索（向量 + BM25 + Rerank）
4. 工具调用（计算器、知识库统计）
5. 答案生成（LLM 基于证据生成回答）
6. 忠实度评判（Faithfulness Check）
7. 记忆写入（将本轮交互存入记忆系统）

异常通过 ApiError 包装为统一错误体。
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.errors import ApiError
from app.graph.build_graph import run_query

# 创建路由实例，前缀为 /api/queries
router = APIRouter(prefix="/api/queries", tags=["queries"])


class QueryCreate(BaseModel):
    """查询请求体。

    Attributes:
        query: 用户的问题文本（必填）
        user_id: 用户标识，用于记忆隔离（默认 "anonymous"）
        session_id: 会话标识，用于多轮对话上下文（可选，不传则自动生成）
    """
    query: str
    user_id: str = "anonymous"
    session_id: str | None = None


class QueryResponse(BaseModel):
    """查询响应体。

    包含完整的执行结果和调试信息，供前端展示。

    Attributes:
        answer: 生成的答案文本
        citations: 引用的 chunk_id 列表
        evidence: 检索到的证据片段列表
        tool_results: 工具调用结果列表
        verify: 忠实度评判结果
        iterations: 重试次数
        trace: 执行链路追踪信息
        recalled_memories: 本轮召回的长期记忆
        memory_writes: 本轮写入的新记忆
        working_memory: 本轮更新后的短期工作记忆
    """
    answer: str
    citations: list[str]
    evidence: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    verify: dict[str, Any]
    iterations: int
    trace: list[dict[str, Any]]
    recalled_memories: list[dict[str, Any]]
    memory_writes: list[dict[str, Any]]
    working_memory: dict[str, Any]


@router.post("", response_model=QueryResponse, status_code=201)
def create_query(req: QueryCreate) -> QueryResponse:
    """执行查询。

    接收用户问题，完整执行 Agent 编排流程，返回答案及所有中间产物。

    流程：
    1. 参数校验（query 不能为空）
    2. 调用 run_query() 执行 Agent 图
    3. 格式化证据数据（截断长文本便于前端展示）
    4. 组装响应体

    异常处理：
    - 空 query → 返回 400 invalid_query
    - 执行异常 → 返回 500 run_failed（包含异常类型和消息）
    """
    if not req.query.strip():
        raise ApiError(code="invalid_query", message="query 不能为空", status=400)

    try:
        # 执行完整的 Agent 编排流程
        s = run_query(
            req.query.strip(),
            user_id=req.user_id,
            session_id=req.session_id,
        )
    except Exception as e:
        raise ApiError(
            code="run_failed",
            message=f"{type(e).__name__}: {e}",
            status=500,
        ) from e

    # 格式化证据数据
    # 将 dataclass 转为 dict，并截断 text 字段（前端展示用）
    ev = [
        asdict(e) if hasattr(e, "__dataclass_fields__") else e
        for e in s.get("evidence", [])
    ]
    evidence = [
        {
            "chunk_id": e["chunk_id"],
            "doc_id": e["doc_id"],
            "score": round(e["score"], 4),  # 保留 4 位小数
            "text": e["text"][:200],  # 截断前 200 字符，避免响应过大
        }
        for e in ev
    ]

    return QueryResponse(
        answer=s.get("answer", ""),
        citations=s.get("citations", []),
        evidence=evidence,
        tool_results=s.get("tool_results", []),
        verify=s.get("verify", {}),
        iterations=s.get("iterations", 0),
        trace=s.get("trace", []),
        recalled_memories=s.get("recalled_memories", []),
        memory_writes=s.get("memory_writes", []),
        working_memory=s.get("working_memory") or {},
    )
