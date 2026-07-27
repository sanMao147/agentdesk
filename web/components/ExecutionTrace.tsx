import type { TraceStep } from "@/lib/api";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { NODE_LABELS } from "@/lib/constants";

export interface ExecutionTraceProps {
  trace: TraceStep[];
}

function computeDescription(step: TraceStep): string {
  switch (step.node) {
    case "memory_retrieve":
      return `召回 ${step.recalled?.length || 0} 条长期记忆` + (step.has_short ? "· 有短期上下文" : "");
    case "planner":
      return `改写 → ${step.queries?.join(" / ") || ""}`;
    case "retrieval":
      return `iter ${step.iter} · ${step.mode} · ${step.hits?.length || 0} 命中`;
    case "tool":
      return `调用 ${step.called?.join(", ") || "（无）"}`;
    case "writer":
      return `生成答案 · 标注 ${step.citations?.length || 0} 条引用`;
    case "critic":
      return `faithful=${step.faithful} · score=${step.score}`;
    case "memory_write":
      return `写入 ${step.wrote?.join(", ") || "（无新记忆）"}`;
    case "summarize":
      return `压缩短期记忆 · summary ${step.summary_len} 字`;
    default:
      return "";
  }
}

export function ExecutionTrace({ trace }: ExecutionTraceProps) {
  return (
    <div>
      <Eyebrow>Execution trace</Eyebrow>
      <div className="relative ml-1.5 pl-[22px]">
        <div
          className="absolute left-[5px] top-1.5 bottom-1.5 w-0.5"
          style={{ background: "linear-gradient(180deg, #7c5cff, #22d3ee)" }}
        />
        {trace.map((step, i) => {
          const title = NODE_LABELS[step.node]?.[0] || step.node;
          const description = computeDescription(step);
          return (
            <div key={i} className="relative pl-1 pb-4">
              <div
                className="absolute -left-[22px] top-[3px] w-[13px] h-[13px] rounded-full bg-grad border-2 border-transparent"
                style={{ boxShadow: "0 0 0 4px rgba(124,92,255,0.12)" }}
              />
              <div className="text-[0.86rem] font-bold text-[#e7ebff]">{title}</div>
              <div className="text-[0.78rem] text-muted mt-0.5 leading-relaxed">{description}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
