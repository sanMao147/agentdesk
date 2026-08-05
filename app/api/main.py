"""FastAPI 应用入口。

本文档是 AgentDesk 后端服务的启动文件，负责：
1. 创建 FastAPI 应用实例
2. 配置 CORS 跨域中间件
3. 注册全局异常处理器
4. 挂载所有 API 路由

整体架构采用 RESTful 风格，统一 /api 前缀，使用复数名词资源命名。
"""
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

# 创建 FastAPI 应用实例，设置标题和版本号
app = FastAPI(title="AgentDesk API", version="0.5.0")

# 配置 CORS 中间件
# 从 settings.cors_origins 解析允许的跨域来源（逗号分隔）
# 允许的 HTTP 方法：GET（查询）、POST（创建）、PATCH（更新）、OPTIONS（预检）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],  # 允许所有请求头
    allow_credentials=False,  # 不允许携带 Cookie/凭证
)

# 注册全局异常处理器
# 所有未捕获的异常都会被转换为统一的 {"error": {"code", "message"}} 格式
register_exception_handlers(app)

# 挂载路由（按功能模块分组）
# - health: 健康检查接口
# - config: 配置管理接口
# - sessions: 会话管理接口
# - index: 索引管理接口
# - queries: 查询执行接口
# - memories: 记忆管理接口
app.include_router(health_router)
app.include_router(config_router)
app.include_router(sessions_router)
app.include_router(index_router)
app.include_router(queries_router)
app.include_router(memories_router)
