"""查询路由：POST /api/queries。

调 app.graph.build_graph.run_query 执行 Agent 编排，组装响应。
异常经 ApiError 包装为统一错误体。
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.errors import ApiError
from app.graph.build_graph import run_query

router = APIRouter(prefix="/api/queries", tags=["queries"])


class QueryCreate(BaseModel):
    query: str
    user_id: str = "anonymous"
    session_id: str | None = None


class QueryResponse(BaseModel):
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
    if not req.query.strip():
        raise ApiError(code="invalid_query", message="query 不能为空", status=400)
    try:
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

    ev = [
        asdict(e) if hasattr(e, "__dataclass_fields__") else e
        for e in s.get("evidence", [])
    ]
    evidence = [
        {
            "chunk_id": e["chunk_id"],
            "doc_id": e["doc_id"],
            "score": round(e["score"], 4),
            "text": e["text"][:200],
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
