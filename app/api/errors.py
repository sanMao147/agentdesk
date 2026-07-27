"""统一错误响应：所有未捕获异常均以 {"error": {"code", "message"}} 形式返回。"""
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
    """业务异常：携带 code/message/status，由全局 handler 转为统一错误体。"""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


def _phrase_to_snake(phrase: str) -> str:
    """HTTP 状态短语 → lower snake（如 "Not Found" → "not_found"）。"""
    return phrase.lower().replace(" ", "_").replace("-", "_")


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，统一错误响应体格式。"""
    log = logging.getLogger("app.api.errors")

    @app.exception_handler(ApiError)
    async def _api_error_handler(_: Any, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message}},
            media_type="application/json",
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Any, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": str(exc)}},
            media_type="application/json",
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(_: Any, exc: StarletteHTTPException) -> JSONResponse:
        # 同时覆盖 Starlette 路由层抛出的 HTTPException（如 404 Not Found）与
        # fastapi.HTTPException（后者是前者的子类，会被同一 handler 捕获）。
        try:
            phrase = HTTPStatus(exc.status_code).phrase
            code = _phrase_to_snake(phrase)
        except ValueError:
            code = f"http_{exc.status_code}"
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": exc.detail}},
            media_type="application/json",
        )

    @app.exception_handler(Exception)
    async def _generic_exception_handler(_: Any, exc: Exception) -> JSONResponse:
        log.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": str(exc)}},
            media_type="application/json",
        )
