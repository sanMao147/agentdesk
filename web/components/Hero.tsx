import type { Config } from "@/lib/api";

export interface HeroProps {
  config: Config;
}

export function Hero({ config }: HeroProps) {
  const live = config.use_llm;

  return (
    <section
      className="relative overflow-hidden border border-stroke rounded-l p-[30px_32px] mb-5"
      style={{
        background: "var(--surface)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,.06)",
      }}
    >
      {/* 单色细微光晕，替代彩色 conic 渐变 */}
      <div
        className="absolute w-[300px] h-[300px] -right-[100px] -top-[120px] rounded-full opacity-[0.18] blur-[70px]"
        style={{ background: "var(--brand)" }}
      />

      <h1 className="relative text-[2rem] font-extrabold tracking-tight m-0 text-ink">
        Agentic RAG 控制台
      </h1>

      <p className="relative mt-2 text-muted text-[0.96rem] leading-relaxed max-w-[760px] m-0">
        LangGraph 编排的多智能体检索增强系统 · 把
        <b className="text-ink">查询改写 → 混合检索 → 工具调用 → 带证据生成 → 反思重试</b>
        的全过程实时可视化。
      </p>

      <div className="relative mt-4 flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-2 px-[13px] py-1.5 rounded-full text-[0.78rem] font-semibold border border-stroke-2 bg-surface-2 text-ink backdrop-blur">
          <span
            className={`inline-block w-2 h-2 rounded-full ${live ? "text-ok" : "text-warn"}`}
            style={{ backgroundColor: "currentColor", boxShadow: "0 0 12px currentColor" }}
          />
          {live ? "真实大模型" : "离线 Fallback"}
        </span>
        <span className="inline-flex items-center gap-2 px-[13px] py-1.5 rounded-full text-[0.78rem] font-semibold border border-stroke-2 bg-surface-2 text-muted backdrop-blur">
          🧩 混合检索 向量+BM25+Rerank
        </span>
        <span className="inline-flex items-center gap-2 px-[13px] py-1.5 rounded-full text-[0.78rem] font-semibold border border-stroke-2 bg-surface-2 text-muted backdrop-blur">
          🛠️ MCP 工具层
        </span>
        <span className="inline-flex items-center gap-2 px-[13px] py-1.5 rounded-full text-[0.78rem] font-semibold border border-stroke-2 bg-surface-2 text-muted backdrop-blur">
          🔁 Critic 反思循环
        </span>
        <span className="inline-flex items-center gap-2 px-[13px] py-1.5 rounded-full text-[0.78rem] font-semibold border border-stroke-2 bg-surface-2 text-muted backdrop-blur">
          📚 {config.n_chunks} chunks
        </span>
      </div>
    </section>
  );
}
