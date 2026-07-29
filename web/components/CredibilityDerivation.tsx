import type { ReactNode } from "react";
import type { ToolResult, Verify } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Eyebrow } from "@/components/ui/Eyebrow";

export interface CredibilityDerivationProps {
  verify: Verify;
  evidenceCount: number;
  toolResults: ToolResult[];
}

export function CredibilityDerivation({
  verify,
  evidenceCount,
  toolResults,
}: CredibilityDerivationProps) {
  const score = Number(verify.score) || 0;
  const faithful = Boolean(verify.faithful);
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  const gaugeColor = faithful
    ? "#10b981"
    : score >= 0.4
      ? "#f59e0b"
      : "#ef4444";

  const method = verify.method || "-";
  const detail =
    (verify.detail as Record<string, unknown> | null | undefined) ?? {};
  const reason = String(verify.reason ?? "");
  const usedTool = Boolean(
    detail.used_tool ?? toolResults.some((r) => r.out?.ok),
  );

  // ① 评判方式
  const methodLabel =
    method === "llm"
      ? "LLM 裁判"
      : method === "heuristic"
        ? "启发式兜底"
        : method;

  // ③ 计算
  let calcNode: ReactNode;
  if (method === "heuristic") {
    const nm = detail.n_match ?? "?";
    const na = detail.n_answer ?? "?";
    calcNode = (
      <>
        启发式：命中词 <b>{String(nm)}</b> ÷ 答案词 <b>{String(na)}</b> ={" "}
        <b>{score.toFixed(2)}</b>　
        <span className="text-faint">
          score = |答案∩(证据∪工具)| / |答案|
        </span>
      </>
    );
  } else if (method === "llm") {
    calcNode = (
      <>
        LLM 裁判逐条核对 → <b>{score.toFixed(2)}</b>
        {reason ? (
          <>
            <br />
            <span className="text-faint">裁判说明：{reason}</span>
          </>
        ) : null}
      </>
    );
  } else {
    calcNode = (
      <>
        score = <b>{score.toFixed(2)}</b>
      </>
    );
  }

  // ④ 阈值判定
  const verdict = faithful
    ? "✅ score ≥ 0.6 → 可信回答"
    : "⚠️ score < 0.6 → 证据支撑不足";

  return (
    <div>
      <Eyebrow className="mt-1.5">可信度推导 · 这次怎么算的</Eyebrow>
      <Card>
        <div className="text-[0.82rem] text-muted leading-loose">
          <div>
            ① 评判方式：<b className="text-ink">{methodLabel}</b>
          </div>
          <div>
            ② 依据：检索证据 <b className="text-ink">{evidenceCount}</b> 条 · 工具结果{" "}
            <b className="text-ink">{usedTool ? "有" : "无"}</b>
          </div>
          <div>③ 计算：{calcNode}</div>
          <div>④ 阈值判定：{verdict}</div>
        </div>

        {/* Ruler */}
        <div className="relative h-6 mt-2.5">
          <div
            className="absolute top-[7px] left-0 right-0 h-2.5 rounded-sm"
            style={{
              background:
                "linear-gradient(90deg, #ef4444 0 40%, #f59e0b 40% 60%, #10b981 60% 100%)",
            }}
          />
          <div className="absolute top-[3px] left-[60%] w-0.5 h-[18px] bg-ink opacity-85" />
          <div
            className="absolute top-1"
            style={{ left: `${pct}%`, transform: "translateX(-50%)" }}
          >
            <div
              className="w-3.5 h-3.5 rounded-full border-2 border-bg"
              style={{
                backgroundColor: gaugeColor,
                boxShadow: `0 0 8px ${gaugeColor}`,
              }}
            />
          </div>
        </div>
        <div className="relative h-3.5 text-[0.64rem] text-faint">
          <span className="absolute left-0">0.0</span>
          <span className="absolute left-[60%] -translate-x-1/2">0.6 阈值</span>
          <span className="absolute right-0">1.0</span>
        </div>
      </Card>
    </div>
  );
}
