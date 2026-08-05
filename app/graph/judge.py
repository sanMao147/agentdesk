"""忠实度评判模块（Faithfulness Judge）。

判断生成的答案是否被检索证据支撑，即答案中的事实是否都有来源依据。

评判方法：
1. 有 LLM 时：LLM-as-judge，让模型分析答案与证据的对应关系（更准确）
2. 无 LLM 时：启发式方法，计算答案词项在证据中的覆盖率（零依赖、可离线）

返回格式：
    {
        "faithful": bool,      # 是否忠实（score >= 阈值）
        "score": float,        # 忠实度得分 (0~1)
        "method": str,         # 评判方法（"llm" / "heuristic"）
        "reason": str,         # 简短说明（仅 LLM 模式有）
        "detail": {            # 推导明细（供前端展示）
            "n_answer": int,
            "n_match": int,
            "used_tool": bool,
            "n_evidence": int
        }
    }

阈值：THRESHOLD = 0.6，得分 >= 0.6 判定为忠实。
"""
from __future__ import annotations

import json
import re

from app.config import settings
from app.llm import chat
from app.rag.tokenize import tokenize

# 忠实度判定阈值
THRESHOLD = 0.6


def _heuristic(answer: str, evidence, tool_text: str = "") -> float:
    """启发式忠实度计算。

    计算答案词项在证据（含工具输出）中的覆盖率：
    score = |答案词 ∩ 证据词| / |答案词|

    这是一个简化的忠实度指标，高重叠率意味着答案更可能被证据支撑。
    """
    ans = set(tokenize(answer))
    if not ans:
        return 0.0
    ev = set()
    for e in evidence:
        ev |= set(tokenize(e.text))
    # 工具输出同样算作"支撑"
    if tool_text:
        ev |= set(tokenize(tool_text))
    return len(ans & ev) / len(ans)


def judge(question: str, answer: str, evidence, tool_results=None) -> dict:
    """执行忠实度评判。

    流程：
    1. 提取工具输出文本（如有）
    2. 优先使用 LLM 评判（更准确）
    3. LLM 不可用或解析失败时回退启发式方法

    工具结果处理：计算器/统计工具的输出同样是"事实依据"，
    必须纳入忠实度判定，否则工具类正确答案会被误判为不可信。
    """
    # 提取工具输出文本
    tool_text = "\n".join(
        r["out"]["result"] for r in (tool_results or [])
        if isinstance(r.get("out"), dict) and r["out"].get("ok") and r["out"].get("result")
    )
    n_evidence = len(list(evidence))

    # 优先使用 LLM 评判
    if settings.use_llm and answer.strip():
        ctx = "\n\n".join(f"[{e.chunk_id}] {e.text}" for e in evidence)
        if tool_text:
            ctx += f"\n\n[工具结果]\n{tool_text}"

        system = (
            "你是严格的事实核查员。判断【答案】中的每条事实是否都能由【证据】支撑。"
            "【证据】包含检索资料与工具结果，工具结果（如统计数字）视为权威依据。"
            "score = 被证据支撑的事实比例（0~1，1 表示完全支撑、无臆造）。"
            "只输出 JSON：{\"score\": 数字, \"reason\": \"简短说明\"}"
        )
        user = f"问题：{question}\n\n答案：{answer}\n\n证据：\n{ctx}"

        try:
            raw = chat(system, user)
            # 从模型输出中提取 JSON（可能包含额外文本）
            m = re.search(r"\{.*\}", raw, re.S)
            obj = json.loads(m.group(0))
            score = max(0.0, min(1.0, float(obj.get("score"))))
            return {"faithful": score >= THRESHOLD, "score": round(score, 3),
                    "reason": str(obj.get("reason", ""))[:200], "method": "llm",
                    "detail": {"used_tool": bool(tool_text), "n_evidence": n_evidence}}
        except Exception:
            pass  # LLM 评判失败，回退启发式

    # —— 启发式兜底 ——
    ans_set = set(tokenize(answer))
    ev_set = set()
    for e in evidence:
        ev_set |= set(tokenize(e.text))
    if tool_text:
        ev_set |= set(tokenize(tool_text))

    score = (len(ans_set & ev_set) / len(ans_set)) if ans_set else 0.0
    return {"faithful": score >= THRESHOLD, "score": round(score, 3), "method": "heuristic",
            "detail": {"n_answer": len(ans_set), "n_match": len(ans_set & ev_set),
                       "used_tool": bool(tool_text), "n_evidence": n_evidence}}
