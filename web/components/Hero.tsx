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
        background:
          "linear-gradient(135deg, rgba(124,92,255,.20), rgba(34,211,238,.10) 55%, rgba(255,255,255,.02))",
        boxShadow:
          "0 30px 80px -40px rgba(91,140,255,.55), inset 0 1px 0 rgba(255,255,255,.08)",
      }}
    >
      <div
        className="absolute w-[340px] h-[340px] -right-[90px] -top-[150px] rounded-full opacity-30 blur-[60px]"
        style={{
          background:
            "conic-gradient(from 120deg, #7c5cff, #22d3ee, #f472b6, #7c5cff)",
          animation: "spin 18s linear infinite",
        }}
      />

      <h1
        className="relative text-[2rem] font-extrabold tracking-tight m-0"
        style={{
          background: "linear-gradient(90deg, #fff, #cdd6ff 60%, #9fe9ff)",
          WebkitBackgroundClip: "text",
          backgroundClip: "text",
          WebkitTextFillColor: "transparent",
          color: "transparent",
        }}
      >
        Agentic RAG 控制台
      </h1>

      <p className="relative mt-2 text-[#c5cdf0] text-[0.96rem] leading-relaxed max-w-[760px] m-0">
        LangGraph 编排的多智能体检索增强系统 · 把
        <b>查询改写 → 混合检索 → 工具调用 → 带证据生成 → 反思重试</b>
        的全过程实时可视化。
      </p>

      <div className="relative mt-4 flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-2 px-[13px] py-1.5 rounded-full text-[0.78rem] font-semibold border border-stroke-2 bg-surface-2 text-[#d7dcf5] backdrop-blur">
          <span
            className={`inline-block w-2 h-2 rounded-full ${live ? "text-ok" : "text-warn"}`}
            style={{ backgroundColor: "currentColor", boxShadow: "0 0 12px currentColor" }}
          />
          {live ? "真实大模型" : "离线 Fallback"}
        </span>
        <span className="inline-flex items-center gap-2 px-[13px] py-1.5 rounded-full text-[0.78rem] font-semibold border border-stroke-2 bg-surface-2 text-[#d7dcf5] backdrop-blur">
          🧩 混合检索 向量+BM25+Rerank
        </span>
        <span className="inline-flex items-center gap-2 px-[13px] py-1.5 rounded-full text-[0.78rem] font-semibold border border-stroke-2 bg-surface-2 text-[#d7dcf5] backdrop-blur">
          🛠️ MCP 工具层
        </span>
        <span className="inline-flex items-center gap-2 px-[13px] py-1.5 rounded-full text-[0.78rem] font-semibold border border-stroke-2 bg-surface-2 text-[#d7dcf5] backdrop-blur">
          🔁 Critic 反思循环
        </span>
        <span className="inline-flex items-center gap-2 px-[13px] py-1.5 rounded-full text-[0.78rem] font-semibold border border-stroke-2 bg-surface-2 text-[#d7dcf5] backdrop-blur">
          📚 {config.n_chunks} chunks
        </span>
      </div>
    </section>
  );
}
