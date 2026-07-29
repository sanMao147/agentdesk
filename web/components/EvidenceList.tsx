import type { Evidence } from "@/lib/api";
import { Eyebrow } from "@/components/ui/Eyebrow";

export interface EvidenceListProps {
  evidence: Evidence[];
}

export function EvidenceList({ evidence }: EvidenceListProps) {
  return (
    <div>
      <Eyebrow>Retrieved evidence</Eyebrow>
      {evidence.map((e, i) => {
        const score = Number(e.score) || 0;
        const width = Math.max(5, Math.min(100, Math.round(score * 100)));
        const text = (e.text || "").slice(0, 240);
        return (
          <div
            key={i}
            className="border border-stroke rounded-m p-3.5 mb-3 transition hover:translate-x-1 hover:border-stroke-2"
          >
            <div className="flex items-center justify-between gap-2.5">
              <div className="flex items-center gap-2.5">
                <span
                  className="w-[22px] h-[22px] rounded-md grid place-items-center text-[0.72rem] font-bold text-bg flex-shrink-0"
                  style={{ backgroundColor: "var(--brand)" }}
                >
                  {i + 1}
                </span>
                <span className="font-mono text-[0.8rem] font-semibold text-ink">{e.chunk_id}</span>
              </div>
              <span className="font-mono text-[0.74rem] text-muted">
                {e.doc_id} · {e.score.toFixed(4)}
              </span>
            </div>
            <div className="h-1.5 rounded bg-[rgba(255,255,255,0.07)] overflow-hidden my-2.5">
              <div
                className="h-full rounded shadow-[0_0_14px_rgba(16,185,129,0.4)]"
                style={{ width: `${width}%`, backgroundColor: "var(--brand)" }}
              />
            </div>
            <div className="text-muted text-[0.84rem] leading-relaxed">{text}…</div>
          </div>
        );
      })}
    </div>
  );
}
