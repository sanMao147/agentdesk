import type { Verify } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Gauge } from "@/components/ui/Gauge";

export interface AnswerCardProps {
  answer: string;
  verify: Verify;
}

export function AnswerCard({ answer, verify }: AnswerCardProps) {
  const score = Number(verify.score) || 0;
  const faithful = Boolean(verify.faithful);
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  const gaugeColor = faithful
    ? "#34d399"
    : score >= 0.4
      ? "#fbbf24"
      : "#fb7185";

  return (
    <div>
      <Eyebrow>Answer</Eyebrow>
      <Card>
        <div className="flex items-center gap-4">
          <Gauge pct={pct} color={gaugeColor} />
          <div>
            <div className="font-bold text-white">
              {faithful ? "✅ 可信回答" : "⚠️ 证据支撑不足"}
            </div>
            <div className="text-muted text-[0.8rem] mt-1">
              faithfulness = 答案被检索证据支撑的比例
            </div>
          </div>
        </div>
        <div className="mt-3.5 text-ink text-[0.95rem] leading-7 whitespace-pre-wrap">
          {answer || "（无答案）"}
        </div>
      </Card>
    </div>
  );
}
