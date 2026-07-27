import { Eyebrow } from "@/components/ui/Eyebrow";
import { Pill } from "@/components/ui/Pill";
import { MEM_KIND } from "@/lib/constants";

export interface MemoryPanelProps {
  recalledMemories: { kind: string; text: string }[];
  memoryWrites: { kind: string; text: string; version: number }[];
}

export function MemoryPanel({ recalledMemories, memoryWrites }: MemoryPanelProps) {
  if (!recalledMemories.length && !memoryWrites.length) return null;

  return (
    <div>
      <Eyebrow>Memory · 本轮记忆</Eyebrow>

      {recalledMemories.length > 0 && (
        <div>
          <div className="text-faint text-[0.75rem] mb-1.5">召回（注入到本次回答的用户画像）</div>
          {recalledMemories.map((m, i) => {
            const [icon, label, color] = MEM_KIND[m.kind] || ["🧠", "记忆", "#9aa6c4"];
            return (
              <div
                key={i}
                className="border border-stroke rounded-m p-3.5 mb-3 transition hover:translate-x-1 hover:border-stroke-2"
              >
                <div className="flex items-center justify-between gap-2.5">
                  <Pill color={color}>
                    {icon} {label}
                  </Pill>
                  <span className="font-mono text-[0.74rem] text-muted">召回 · 注入回答</span>
                </div>
                <div className="text-[#c3cbe6] text-[0.84rem] leading-relaxed mt-2">{m.text}</div>
              </div>
            );
          })}
        </div>
      )}

      {memoryWrites.length > 0 && (
        <div>
          <div className="text-faint text-[0.75rem] mt-2.5 mb-1.5">本轮写入 / 更新（经去重·冲突演化）</div>
          <div className="flex flex-wrap">
            {memoryWrites.map((w, i) => {
              const [icon, label, color] = MEM_KIND[w.kind] || ["🧠", "记忆", "#9aa6c4"];
              const tag = Number(w.version) > 1 ? "冲突更新" : "写入";
              return (
                <Pill key={i} color={color}>
                  {icon} {tag}·{label} v{w.version}：{w.text}
                </Pill>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
