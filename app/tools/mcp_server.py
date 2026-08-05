"""MCP 服务端实现（stdio 传输）。

纯标准库实现 MCP JSON-RPC 2.0 over stdio。
服务端从 stdin 逐行读取 JSON-RPC 请求，向 stdout 逐行写出响应。

实现三个核心方法：
- initialize: 握手，返回协议版本与能力
- tools/list: 工具发现（返回可用工具列表及参数 Schema）
- tools/call: 工具调用（转发到本地 registry 执行）

运行方式：
    python -m app.tools.mcp_server

生产环境可直接替换为官方 mcp SDK（from mcp.server import Server），
方法契约保持一致；手写实现是为了无依赖、可离线演示传输层原理。
"""
from __future__ import annotations

import json
import sys

from app.tools.builtins import registry

# MCP 协议版本
PROTOCOL_VERSION = "2024-11-05"


def _handle(req: dict) -> dict | None:
    """处理 JSON-RPC 请求。

    根据 method 字段分发到对应的处理逻辑：
    - notifications/initialized: 通知，无响应
    - initialize: 握手，返回协议版本和能力
    - tools/list: 列出工具，转换为 MCP inputSchema 格式
    - tools/call: 调用工具，统一包装为 {content, isError} 格式
    - 其他: 返回 method not found 错误

    Args:
        req: JSON-RPC 请求对象

    Returns:
        JSON-RPC 响应对象（通知返回 None）
    """
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    # 通知（无 id）不需要响应
    if method == "notifications/initialized":
        return None

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {"name": "agentdesk-tools", "version": "0.1.0"},
            "capabilities": {"tools": {}},
        }

    elif method == "tools/list":
        # 转换为 MCP 工具描述格式
        tools = []
        for t in registry.list_tools():
            props = {
                k: {"type": "string" if v == "str" else "number"}
                for k, v in t["params"].items()
            }
            tools.append({
                "name": t["name"],
                "description": t["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": props,
                    "required": t["required"],
                },
            })
        result = {"tools": tools}

    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        out = registry.call_tool(name, args)
        text = out.get("result") if out.get("ok") else f"ERROR: {out.get('error')}"
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "content": [{"type": "text", "text": str(text)}],
                "isError": not out.get("ok"),
            },
        }

    else:
        # 未知方法
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }

    return {"jsonrpc": "2.0", "id": rid, "result": result}


def main() -> None:
    """主循环：逐行读取 stdin 请求并写回 stdout 响应。

    这是 MCP stdio 传输的核心逻辑：
    1. 从 stdin 读取一行 JSON-RPC 请求
    2. 调用 _handle() 处理
    3. 将响应写回 stdout（JSON-RPC 规定：stdin 读，stdout 写，互不干扰）
    """
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = _handle(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
