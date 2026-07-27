import type { ToolResult } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Pill } from "@/components/ui/Pill";

export interface ToolCallsProps {
  toolResults: ToolResult[];
}

export function ToolCalls({ toolResults }: ToolCallsProps) {
  if (!toolResults.length) return null;
  return (
    <div>
      <Eyebrow>Tool calls</Eyebrow>
      {toolResults.map((r, i) => {
        const ok = Boolean(r.out?.ok);
        const txt = r.out?.result || r.out?.error || JSON.stringify(r.out);
        return (
          <Card key={i} className="p-3.5">
            <Pill variant={ok ? "tool" : "bad"}>
              {ok ? "✓" : "✕"} {r.tool} · via {r.out?.via || "local"}
            </Pill>
            <div className="font-mono text-[0.84rem] text-[#dfe6ff] mt-2">
              {txt}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
