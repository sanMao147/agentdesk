"use client";

import type { Config } from "@/lib/api";
import { SAMPLES } from "@/lib/constants";
import { Card } from "@/components/ui/Card";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Expander } from "@/components/ui/Expander";

export interface SidebarProps {
  config: Config;
  userId: string;
  sessionId: string;
  onUserIdChange: (v: string) => void;
  onNewSession: () => void;
  onRebuildIndex: () => void;
  onPickSample: (q: string) => void;
}

export function Sidebar({
  config,
  userId,
  sessionId,
  onUserIdChange,
  onNewSession,
  onRebuildIndex,
  onPickSample,
}: SidebarProps) {
  const live = config.use_llm;

  return (
    <aside className="w-[280px] flex-shrink-0 sticky top-4 self-start max-h-[calc(100vh-2rem)] overflow-y-auto pr-2">
      <Eyebrow>Console</Eyebrow>
      <div style={{ fontSize: "1.15rem", fontWeight: 800, margin: "-4px 0 2px" }}>
        AgentDesk
      </div>
      <div className="text-muted text-[0.8rem]">Agentic RAG · 多智能体</div>

      <hr className="border-stroke my-3.5" />

      <Card className="mb-3">
        <div className="flex items-center gap-2.5">
          <span
            className={`inline-block w-2 h-2 rounded-full ${live ? "text-ok" : "text-warn"}`}
            style={{ backgroundColor: "currentColor", boxShadow: "0 0 12px currentColor" }}
          />
          <b className="text-[0.9rem]">{live ? "真实大模型" : "离线 Fallback"}</b>
        </div>
        <div className="text-faint text-[0.76rem] mt-1.5 leading-relaxed">
          {live ? "已接入 LLM/Embedding API" : "哈希向量 + 拼接答案，无需任何 key"}
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-2">
        <Card className="m-0 p-3">
          <div className="text-faint text-[0.7rem]">向量后端</div>
          <div className="font-bold mt-1">{config.vector_backend}</div>
        </Card>
        <Card className="m-0 p-3">
          <div className="text-faint text-[0.7rem]">Top-K</div>
          <div className="font-bold mt-1">{config.top_k}</div>
        </Card>
        <Card className="m-0 p-3">
          <div className="text-faint text-[0.7rem]">反思上限</div>
          <div className="font-bold mt-1">{config.max_iterations}</div>
        </Card>
        <Card className="m-0 p-3">
          <div className="text-faint text-[0.7rem]">KB chunks</div>
          <div className="font-bold mt-1">{config.n_chunks}</div>
          <button
            type="button"
            onClick={onRebuildIndex}
            className="mt-1 text-xs text-brand2 hover:underline cursor-pointer"
          >
            重建索引
          </button>
        </Card>
      </div>

      <Eyebrow className="mt-[18px]">记忆身份</Eyebrow>
      <input
        type="text"
        value={userId}
        onChange={(e) => onUserIdChange(e.target.value)}
        placeholder="user_id（记忆按此隔离）"
        className="bg-surface-2 text-ink border border-stroke-2 rounded-xl h-[52px] px-4 text-[0.95rem] placeholder:text-faint focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/25 w-full"
      />

      <div className="grid grid-cols-[3fr_2fr] gap-2 mt-2">
        <div className="text-faint text-[0.72rem] pt-2">
          会话 {sessionId.slice(0, 8)}…
        </div>
        <button
          type="button"
          onClick={onNewSession}
          className="rounded-xl border border-stroke-2 bg-surface-2 text-[#dfe4ff] font-semibold py-2 px-3 hover:border-brand hover:text-white hover:bg-brand/16 transition w-full text-sm"
        >
          新会话
        </button>
      </div>

      <Eyebrow className="mt-[18px]">试一试</Eyebrow>
      {SAMPLES.map((q) => (
        <button
          key={q}
          type="button"
          onClick={() => onPickSample(q)}
          className="w-full text-left rounded-xl border border-stroke-2 bg-surface-2 text-[#dfe4ff] font-medium py-2 px-3 mb-1.5 hover:border-brand hover:text-white hover:bg-brand/16 transition text-sm"
        >
          {q}
        </button>
      ))}

      <Expander summary="架构 / 流程" className="mt-3">
        <p className="mb-2 last:mb-0 text-[0.8rem] text-[#c3cbe6] leading-relaxed">
          <b>编排（LangGraph）</b>：planner → retrieval → tool → writer → critic；critic 不达标且未超轮数则回 retrieval 重试。
        </p>
        <p className="mb-2 last:mb-0 text-[0.8rem] text-[#c3cbe6] leading-relaxed">
          <b>检索</b>：多查询改写 → 向量 + BM25 → RRF 融合 → Rerank。
        </p>
        <p className="mb-2 last:mb-0 text-[0.8rem] text-[#c3cbe6] leading-relaxed">
          <b>工具层</b>：MCP 风格 registry（AST 白名单计算器 / kb_stats）。
        </p>
        <p className="mb-2 last:mb-0 text-[0.8rem] text-[#c3cbe6] leading-relaxed">
          <b>兜底</b>：langgraph 不可用时顺序等价执行。
        </p>
      </Expander>
    </aside>
  );
}
