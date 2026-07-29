import type { WorkingMemory } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Eyebrow } from "@/components/ui/Eyebrow";

export interface ChatHistoryProps {
  workingMemory: WorkingMemory;
  sessionId: string;
}

export function ChatHistory({ workingMemory, sessionId }: ChatHistoryProps) {
  const msgs = workingMemory.messages ?? [];
  const summary = workingMemory.running_summary ?? "";
  if (!msgs.length && !summary) return null;

  return (
    <div>
      <Eyebrow>对话历史 · 本会话短期记忆</Eyebrow>
      <Card>
        {summary ? (
          <div className="border-l-[3px] border-brand pl-3 pr-3 py-2 mb-2 bg-brand/10 rounded-lg">
            <div className="text-faint text-[0.72rem] mb-1">
              🗜️ 滚动摘要（已压缩的旧轮次）
            </div>
            <div className="text-muted text-[0.84rem] leading-relaxed">
              {summary}
            </div>
          </div>
        ) : null}
        {msgs.map((m, i) => {
          const isUser = m.role === "user";
          return (
            <div
              key={i}
              className={`flex my-1.5 ${isUser ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[78%] border border-stroke-2 rounded-xl px-3 py-2 ${isUser ? "bg-brand/16" : "bg-surface-2"}`}
              >
                <div className="text-faint text-[0.68rem] mb-1">
                  {isUser ? "🧑 用户" : "🤖 助手"}
                </div>
                <div className="text-ink text-[0.85rem] leading-relaxed whitespace-pre-wrap">
                  {(m.content ?? "").slice(0, 500)}
                </div>
              </div>
            </div>
          );
        })}
      </Card>
      <div className="text-faint text-[0.72rem] -mt-1 mb-1.5">
        共 {workingMemory.round_count} 轮 · 会话 {sessionId.slice(0, 8)}… · 短期记忆随会话累积，超阈值自动压缩为摘要
      </div>
    </div>
  );
}
