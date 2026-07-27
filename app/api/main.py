"""FastAPI 入口：RESTful API（统一 /api 前缀，复数名词资源）。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.routes.config import router as config_router
from app.api.routes.health import router as health_router
from app.api.routes.index import router as index_router
from app.api.routes.memories import router as memories_router
from app.api.routes.queries import router as queries_router
from app.api.routes.sessions import router as sessions_router
from app.config import settings

app = FastAPI(title="AgentDesk API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(config_router)
app.include_router(sessions_router)
app.include_router(index_router)
app.include_router(queries_router)
app.include_router(memories_router)
