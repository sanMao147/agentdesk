"use client";

import { useEffect, useState } from "react";
import type { MemoryList } from "@/lib/api";
import { listMemories } from "@/lib/api";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Pill } from "@/components/ui/Pill";
import { MEM_KIND } from "@/lib/constants";

export interface MemoryEvolutionProps {
  userId: string;
  refreshKey: number;
}

export function MemoryEvolution({ userId, refreshKey }: MemoryEvolutionProps) {
  const [records, setRecords] = useState<MemoryList | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await listMemories(userId);
        if (!cancelled) setRecords(data);
      } catch {
        if (!cancelled) setRecords({ live: [], dead: [] });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId, refreshKey]);

  const hasRecords = !!(records && (records.live.length || records.dead.length));

  return (
    <div>
      <Eyebrow className="mt-2">Memory evolution · 演化审计</Eyebrow>
      {loading ? (
        <div className="text-faint text-[0.78rem]">加载中…</div>
      ) : hasRecords && records ? (
        <div>
          {[...records.live]
            .sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0))
            .map((r) => {
              const [icon, label, color] = MEM_KIND[r.kind] || ["🧠", "记忆", "#9aa6c4"];
              const superseded = records.dead.filter((o) => o.superseded_by === r.mem_id);
              return (
                <div key={r.mem_id} className="border border-stroke rounded-m p-3 mb-3">
                  <div className="flex items-center justify-between">
                    <Pill color={color}>
                      {icon} {label} v{r.version}
                    </Pill>
                    <span className="font-mono text-[0.74rem] text-muted">命中 {r.use_count} 次</span>
                  </div>
                  <div className="text-[#c3cbe6] text-[0.84rem] leading-relaxed mt-1.5">{r.text}</div>
                  {superseded.map((o) => (
                    <div key={o.mem_id} className="text-faint text-[0.72rem] line-through mt-1">
                      v{o.version} {o.text}（已被取代）
                    </div>
                  ))}
                </div>
              );
            })}
          <div className="text-faint text-[0.72rem] mt-0.5">
            现行 {records.live.length} 条 · 审计留痕 {records.dead.length} 条
          </div>
        </div>
      ) : (
        <div className="text-faint text-[0.78rem]">该用户暂无长期记忆（多问几轮自述偏好即可看到积累）</div>
      )}
    </div>
  );
}
