"""MCP 客户端实现。

通过 stdio JSON-RPC 协议与 MCP 服务端子进通信。
这是 MCP（Model Context Protocol）stdio 传输的简化实现。

用法：
    with MCPClient() as c:
        tools = c.list_tools()
        out = c.call_tool("calculator", {"expression": "1+2"})

生产环境可替换为官方 mcp SDK。
"""
from __future__ import annotations

import json
import subprocess
import sys
from typing import List


class MCPClient:
    """MCP 协议客户端（stdio 传输）。

    通过子进程与 MCP 服务端通信：
    - 启动子进程（默认 python -m app.tools.mcp_server）
    - 通过 stdin/stdout 行级 JSON-RPC 交互
    - 支持 initialize / tools/list / tools/call 三个方法

    协议版本：2024-11-05（MCP 最新版）
    """

    def __init__(self, server_module: str = "app.tools.mcp_server") -> None:
        """初始化 MCP 客户端。

        Args:
            server_module: 服务端 Python 模块路径
        """
        self._proc = subprocess.Popen(
            [sys.executable, "-m", server_module],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._id = 0  # 请求 ID 计数器
        self._initialized = False

    def _rpc(self, method: str, params: dict | None = None, notify: bool = False):
        """发送 JSON-RPC 请求并接收响应。

        Args:
            method: RPC 方法名
            params: 方法参数
            notify: 是否为通知（无响应）

        Returns:
            响应结果（通知返回 None）
        """
        msg = {"jsonrpc": "2.0", "method": method}
        if not notify:
            self._id += 1
            msg["id"] = self._id
        if params is not None:
            msg["params"] = params

        assert self._proc.stdin and self._proc.stdout
        self._proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

        if notify:
            return None

        line = self._proc.stdout.readline()
        return json.loads(line)

    def initialize(self) -> dict:
        """执行 MCP 握手。

        发送 initialize 请求 + notifications/initialized 通知。

        Returns:
            服务端能力信息
        """
        resp = self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "agentdesk", "version": "0.1.0"},
        })
        self._rpc("notifications/initialized", notify=True)
        self._initialized = True
        return resp["result"]

    def list_tools(self) -> List[dict]:
        """列出服务端可用的工具。"""
        if not self._initialized:
            self.initialize()
        return self._rpc("tools/list")["result"]["tools"]

    def call_tool(self, name: str, arguments: dict) -> dict:
        """调用指定工具。

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            MCP 协议格式的调用结果
        """
        if not self._initialized:
            self.initialize()
        return self._rpc("tools/call", {"name": name, "arguments": arguments})["result"]

    def close(self) -> None:
        """关闭客户端，终止子进程。"""
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:
            self._proc.kill()

    def __enter__(self) -> "MCPClient":
        """上下文管理器支持。"""
        self.initialize()
        return self

    def __exit__(self, *exc) -> None:
        """上下文管理器支持。"""
        self.close()
