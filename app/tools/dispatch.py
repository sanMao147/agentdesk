"""工具调用分发器。

根据配置选择工具调用方式：
- 本地模式（默认）：直接调用 registry 中的工具（进程内，零开销）
- MCP 模式：通过 MCP 协议调用远程工具子进程

两条路径返回统一结构 {ok, result/error}，上层 Agent 无感知。

这使得系统可以平滑地从"内置工具"迁移到"外部 MCP 工具"。
"""
from __future__ import annotations

from app.config import settings
from app.tools.builtins import registry

_mcp_client = None


def _get_mcp():
    """获取 MCP 客户端单例（懒加载）。"""
    global _mcp_client
    if _mcp_client is None:
        from app.tools.mcp_client import MCPClient
        _mcp_client = MCPClient()
        _mcp_client.initialize()
    return _mcp_client


def call(name: str, args: dict) -> dict:
    """调用工具。

    根据 settings.use_mcp 选择调用路径：
    - True: 走 MCP 协议（spawn 子进程，stdio JSON-RPC）
    - False: 走本地 registry（直接调用 handler）

    Args:
        name: 工具名称
        args: 工具参数

    Returns:
        统一格式的调用结果：
            成功：{"ok": True, "result": "...", "via": "mcp"/"local"}
            失败：{"ok": False, "error": "...", "via": "mcp"/"local"}
    """
    if getattr(settings, "use_mcp", False):
        try:
            res = _get_mcp().call_tool(name, args)
            content = res.get("content", [])
            text = content[0]["text"] if content else ""
            if res.get("isError"):
                return {"ok": False, "error": text, "via": "mcp"}
            return {"ok": True, "result": text, "via": "mcp"}
        except Exception as e:
            return {"ok": False, "error": f"mcp transport failed: {e}", "via": "mcp"}

    # 本地模式
    out = registry.call_tool(name, args)
    out["via"] = "local"
    return out
