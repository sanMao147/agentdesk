"""MCP 风格的本地工具注册层。

为 Agent 提供工具调用能力，支持：
1. 工具注册与发现（register / list_tools）
2. 参数 Schema 校验（类型检查 + 必填检查）
3. 工具调用与统一错误处理
4. 输出截断（防止工具输出爆 token）

设计原则：
- 工具名校验：防止 LLM 幻觉调用不存在的工具
- 结构化报错：缺参/类型错返回可读错误，不崩溃
- 安全执行：用 AST 白名单实现计算器，绝不 eval 任意代码
- 统一格式：所有工具返回 {ok, result/error}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

# 工具输出截断上限（字符），防止长输出撑爆 context window
MAX_TOOL_OUTPUT = 800


class ToolError(Exception):
    """工具执行错误。

    由工具 handler 主动抛出，用于传达可读的错误信息。
    ToolRegistry 捕获后会转换为统一的错误响应。
    """
    pass


@dataclass
class Tool:
    """工具定义。

    Attributes:
        name: 工具名称（唯一标识）
        description: 工具描述（供 LLM 理解用途）
        params: 参数 Schema（{参数名: 类型}）
        handler: 工具执行函数
        required: 必填参数列表
    """
    name: str
    description: str
    params: Dict[str, type]
    handler: Callable[[dict], str]
    required: List[str] = field(default_factory=list)


class ToolRegistry:
    """工具注册表。

    管理所有可用的工具，提供注册、发现和调用功能。
    类似 MCP 的工具注册机制，但简化为进程内实现。
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具。"""
        self._tools[tool.name] = tool

    def list_tools(self) -> List[dict]:
        """列出所有可用工具的元信息。

        返回格式供 LLM 理解可用工具，或供前端展示。
        """
        return [
            {
                "name": t.name,
                "description": t.description,
                "params": {k: v.__name__ for k, v in t.params.items()},
                "required": t.required,
            }
            for t in self._tools.values()
        ]

    def call_tool(self, name: str, args: dict) -> dict:
        """调用指定工具。

        执行流程：
        1. 工具名校验（拒绝不存在的工具）
        2. 必填参数检查
        3. 参数类型校验
        4. 执行 handler（捕获 ToolError 和通用异常）
        5. 输出截断

        返回格式：
            成功：{"ok": True, "result": "...", "truncated": False}
            失败：{"ok": False, "error": "...", "available": [...]}  # 未知工具时
                  {"ok": False, "error": "..."}  # 其他错误
        """
        # 1) 工具名校验
        if name not in self._tools:
            return {
                "ok": False,
                "error": f"unknown tool: {name}",
                "available": list(self._tools.keys()),
            }

        tool = self._tools[name]
        args = args or {}

        # 2) 必填参数检查
        for r in tool.required:
            if r not in args:
                return {"ok": False, "error": f"missing required param: {r}"}

        # 3) 参数类型校验
        for k, v in args.items():
            if k in tool.params and not isinstance(v, tool.params[k]):
                return {
                    "ok": False,
                    "error": f"param '{k}' expected {tool.params[k].__name__}, got {type(v).__name__}",
                }

        # 4) 执行 handler + 统一错误处理
        try:
            out = tool.handler(args)
        except ToolError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            # 兜底：绝不允许工具异常打断整条链
            return {"ok": False, "error": f"tool crashed: {e}"}

        # 5) 输出截断
        truncated = False
        if isinstance(out, str) and len(out) > MAX_TOOL_OUTPUT:
            out = out[:MAX_TOOL_OUTPUT] + " ...[truncated]"
            truncated = True

        return {"ok": True, "result": out, "truncated": truncated}
