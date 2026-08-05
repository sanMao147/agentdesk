"""统一错误响应处理模块。

所有未捕获异常均会被转换为统一的 JSON 错误格式：
    {"error": {"code": "错误码", "message": "错误描述"}}

支持的异常类型：
- ApiError: 业务异常，由业务代码主动抛出
- RequestValidationError: 请求参数校验失败（422）
- HTTPException: HTTP 协议级异常（如 404）
- Exception: 兜底异常，返回 500

设计思路：
- 前端只需处理一种错误格式，简化错误展示逻辑
- 错误码 (code) 使用 snake_case 风格，便于前端 switch/case 处理
- 详细错误信息仅在开发环境暴露
"""
from __future__ import annotations

import logging
import traceback
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """业务异常类。

    用于在业务逻辑中主动抛出的错误，携带：
    - code: 机器可读的错误码（snake_case）
    - message: 人类可读的错误描述
    - status: HTTP 状态码（默认 400）

    使用示例：
        raise ApiError(code="invalid_query", message="查询不能为空", status=400)
    """

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


def _phrase_to_snake(phrase: str) -> str:
    """将 HTTP 状态码短语转换为 snake_case 错误码。

    例如：
        "Not Found" → "not_found"
        "Bad Request" → "bad_request"
    """
    return phrase.lower().replace(" ", "_").replace("-", "_")


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器到 FastAPI 应用。

    每个处理器将特定类型的异常转换为统一的 JSON 响应格式。
    """
    log = logging.getLogger("app.api.errors")

    @app.exception_handler(ApiError)
    async def _api_error_handler(_: Any, exc: ApiError) -> JSONResponse:
        """处理业务异常。

        业务异常携带明确的 code 和 status，直接返回。
        """
        return JSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message}},
            media_type="application/json",
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Any, exc: RequestValidationError) -> JSONResponse:
        """处理请求参数校验失败。

        当请求体不符合 Pydantic 模型定义时触发，返回 422 状态码。
        """
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": str(exc)}},
            media_type="application/json",
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(_: Any, exc: StarletteHTTPException) -> JSONResponse:
        """处理 HTTP 协议级异常。

        同时覆盖 Starlette 路由层抛出的 HTTPException（如 404 Not Found）与
        FastAPI 的 HTTPException（后者是前者的子类，会被同一 handler 捕获）。

        错误码从 HTTP 状态码短语自动推导。
        """
        try:
            phrase = HTTPStatus(exc.status_code).phrase
            code = _phrase_to_snake(phrase)
        except ValueError:
            # 未知状态码，使用通用格式
            code = f"http_{exc.status_code}"
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": exc.detail}},
            media_type="application/json",
        )

    @app.exception_handler(Exception)
    async def _generic_exception_handler(_: Any, exc: Exception) -> JSONResponse:
        """兜底异常处理器。

        捕获所有未被上述处理器覆盖的异常，返回 500 状态码。
        同时记录完整堆栈到日志，便于排查。
        """
        log.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": str(exc)}},
            media_type="application/json",
        )
