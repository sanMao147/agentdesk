import type { Verify } from "@/lib/api";

export interface KpiRowProps {
  verify: Verify;
  iterations: number;
  evidenceCount: number;
}

export function KpiRow({ verify, iterations, evidenceCount }: KpiRowProps) {
  const score = Number(verify.score) || 0;
  const faithful = Boolean(verify.faithful);

  const kpis = [
    {
      ico: "🎯",
      lab: "Faithfulness",
      val: score.toFixed(2),
      sub: faithful ? "证据支撑达标" : "未达标",
    },
    {
      ico: "🔁",
      lab: "反思轮数",
      val: String(iterations),
      sub: "critic retry loop",
    },
    {
      ico: "📎",
      lab: "命中证据",
      val: String(evidenceCount),
      sub: "RRF + Rerank top-k",
    },
    {
      ico: "⚖️",
      lab: "评判方式",
      val: verify.method || "-",
      sub: "LLM-judge / 启发式",
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      {kpis.map((k) => (
        <div
          key={k.lab}
          className="border border-stroke rounded-m p-4 relative overflow-hidden h-full"
          style={{
            background:
              "linear-gradient(180deg, var(--surface-2), var(--surface))",
          }}
        >
          <div className="text-[1.05rem] leading-none">{k.ico}</div>
          <div className="text-muted text-[0.76rem] font-semibold tracking-[0.04em] mt-1.5">
            {k.lab}
          </div>
          <div className="text-[1.95rem] font-extrabold tracking-tight leading-none mt-0.5 tabular-nums">
            {k.val}
          </div>
          <div className="text-faint text-[0.74rem] mt-0.5">{k.sub}</div>
          <div className="absolute left-0 bottom-0 h-[3px] w-full bg-grad opacity-85" />
        </div>
      ))}
    </div>
  );
}
