"""内置工具定义。

提供两个内置工具：
1. calculator: 安全计算器（用 AST 白名单实现，绝不 eval 任意代码）
2. kb_stats: 知识库统计（查询文档数量）

所有工具通过 ToolRegistry 注册，遵循统一的接口契约。
"""
from __future__ import annotations

import ast
import operator as op

from app.tools.registry import Tool, ToolRegistry, ToolError

# ---- 安全计算器 ----
# 使用 AST 白名单实现，仅支持基础算术运算
# 这是面试中常被问到的安全考点：如何在 Python 中安全执行用户输入的表达式
_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _eval_node(node):
    """安全 AST 节点求值。

    递归遍历 AST，只允许：
    - 数字常量（int/float）
    - 二元运算（加减乘除幂取模）
    - 一元运算（正负号）

    拒绝函数调用、属性访问、字符串等危险操作。
    """
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ToolError("only numeric constants allowed")
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))

    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))

    raise ToolError("unsupported expression")


def _calculator(args: dict) -> str:
    """计算器工具 handler。

    使用 AST 解析表达式，在白名单内安全求值。

    Args:
        args: {"expression": "(210-205)/205*100"}

    Returns:
        计算结果字符串
    """
    expr = args["expression"]
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise ToolError(f"invalid expression: {expr}")
    return str(_eval_node(tree.body))


def _kb_stats(args: dict) -> str:
    """知识库统计工具 handler。

    查询当前知识库的文档数量和 chunk 数量。
    用于回答"知识库有多少文档？"等统计类问题。

    Args:
        args: {} （无需参数）

    Returns:
        统计信息字符串
    """
    from app.rag.indexer import INDEX_PATH
    from app.rag.store import VectorStore

    store = VectorStore()
    store.load(INDEX_PATH)
    docs = sorted({c.doc_id for c in store.chunks})
    return (
        f"文档总数={len(docs)}（权威值：回答文档数量时直接采用此数，请勿自行数列表）"
        f"；chunk 总数={len(store)}。文档列表：{', '.join(docs)}"
    )


def build_registry() -> ToolRegistry:
    """构建并返回包含所有内置工具的注册表。"""
    reg = ToolRegistry()

    # 注册计算器
    reg.register(Tool(
        name="calculator",
        description="计算一个算术表达式，例如 (210-205)/205*100",
        params={"expression": str},
        required=["expression"],
        handler=_calculator,
    ))

    # 注册知识库统计
    reg.register(Tool(
        name="kb_stats",
        description="返回知识库的文档与 chunk 统计",
        params={},
        required=[],
        handler=_kb_stats,
    ))

    return reg


# 全局注册表单例
registry = build_registry()
