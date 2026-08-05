"""共享 FastAPI 依赖模块。

提供 get_settings() 依赖函数，用于在路由中注入全局配置。
当前为占位实现，便于后续扩展依赖注入（DI）模式。
"""
from __future__ import annotations

from app.config import settings


def get_settings():
    """返回全局 settings 单例。

    FastAPI 支持将函数作为依赖注入到路由参数中，
    这样做的好处是：
    1. 统一获取配置的入口
    2. 便于后续替换为 mock 对象进行单元测试
    3. 可以在此处添加缓存、校验等逻辑
    """
    return settings
