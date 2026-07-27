"use client";

import { useCallback, useEffect, useState } from "react";
import type { Config, QueryResponse } from "@/lib/api";
import {
  ApiError,
  createQuery,
  createSession,
  getConfig,
  patchConfig,
  rebuildIndex,
} from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";
import { Hero } from "@/components/Hero";
import { AskBar } from "@/components/AskBar";
import { KpiRow } from "@/components/KpiRow";
import { ChatHistory } from "@/components/ChatHistory";
import { AnswerCard } from "@/components/AnswerCard";
import { CredibilityDerivation } from "@/components/CredibilityDerivation";
import { Citations } from "@/components/Citations";
import { ToolCalls } from "@/components/ToolCalls";
import { MemoryPanel } from "@/components/MemoryPanel";
import { EvidenceList } from "@/components/EvidenceList";
import { ExecutionTrace } from "@/components/ExecutionTrace";
import { MemoryEvolution } from "@/components/MemoryEvolution";
import { RawState } from "@/components/RawState";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { ToastProvider, useToast } from "@/components/ui/Toast";

function PageInner() {
  const [config, setConfig] = useState<Config | null>(null);
  const [userId, setUserId] = useState("alice");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [memoryRefreshKey, setMemoryRefreshKey] = useState(0);
  const toast = useToast();

  // Mount-only: fetch initial config + open a session.
  useEffect(() => {
    (async () => {
      try {
        const [cfg, sess] = await Promise.all([getConfig(), createSession()]);
        setConfig(cfg);
        setSessionId(sess.session_id);
      } catch (e) {
        toast.showToast(
          `初始化失败：${e instanceof ApiError ? e.message : String(e)}`,
          "error",
        );
      }
    })();
     
  }, []);

  const runQuery = useCallback(
    async (q: string) => {
      const trimmed = q.trim();
      if (!trimmed) return;
      setLoading(true);
      setError(null);
      try {
        const res = await createQuery({
          query: trimmed,
          user_id: userId,
          session_id: sessionId,
        });
        setQueryResponse(res);
        setMemoryRefreshKey((k) => k + 1);
      } catch (e) {
        setError(
          e instanceof ApiError ? e : new ApiError("unknown", String(e), 0),
        );
      } finally {
        setLoading(false);
      }
    },
    [userId, sessionId],
  );

  const handleNewSession = useCallback(async () => {
    try {
      const s = await createSession();
      setSessionId(s.session_id);
      setQueryResponse(null);
      setError(null);
      setQuery("");
    } catch (e) {
      toast.showToast(
        `新会话创建失败：${e instanceof ApiError ? e.message : String(e)}`,
        "error",
      );
    }
     
  }, []);

  const handleRebuildIndex = useCallback(async () => {
    try {
      toast.showToast("重建索引中…", "info");
      const info = await rebuildIndex();
      toast.showToast(`索引重建完成：${info.n_chunks} chunks`, "success");
      setConfig((c) =>
        c
          ? {
              ...c,
              n_chunks: info.n_chunks,
              index_signature: info.index_signature,
            }
          : c,
      );
    } catch (e) {
      toast.showToast(
        `重建失败：${e instanceof ApiError ? e.message : String(e)}`,
        "error",
      );
    }
     
  }, []);

  const handleModelChange = useCallback(async (model: string) => {
    if (!model) return;
    try {
      const updated = await patchConfig({ chat_model: model });
      setConfig(updated);
    } catch (e) {
      toast.showToast(
        `模型切换失败：${e instanceof ApiError ? e.message : String(e)}`,
        "error",
      );
    }
     
  }, []);

  const handlePickSample = useCallback(
    (q: string) => {
      setQuery(q);
      runQuery(q);
    },
    [runQuery],
  );

  return (
    <div className="flex gap-6 max-w-[1240px] mx-auto px-5 py-8">
      {config && (
        <Sidebar
          config={config}
          userId={userId}
          sessionId={sessionId || ""}
          onUserIdChange={setUserId}
          onNewSession={handleNewSession}
          onRebuildIndex={handleRebuildIndex}
          onPickSample={handlePickSample}
        />
      )}
      <main className="flex-1 min-w-0">
        {config && <Hero config={config} />}
        {config && (
          <AskBar
            config={config}
            initialQuery={query}
            onQueryChange={setQuery}
            onRun={runQuery}
            onModelChange={handleModelChange}
          />
        )}
        <div className="h-4" />
        {loading ? (
          <Card className="text-center py-10">
            <Spinner label="Agent 编排执行中：记忆召回 → 改写 → 检索 → 工具 → 生成 → 反思 → 记忆写入…" />
          </Card>
        ) : error ? (
          <Card className="text-bad border-bad/30">
            <div className="font-semibold mb-1">
              运行出错（多为模型接口超时/报错）
            </div>
            <div className="text-sm">
              {error.code}: {error.message}　可在上方换一个更稳的模型重试。
            </div>
          </Card>
        ) : queryResponse ? (
          <>
            <KpiRow
              verify={queryResponse.verify}
              iterations={queryResponse.iterations}
              evidenceCount={queryResponse.evidence.length}
            />
            <ChatHistory
              workingMemory={queryResponse.working_memory}
              sessionId={sessionId || ""}
            />
            <div className="grid grid-cols-[1.4fr_1fr] gap-6">
              <div>
                <AnswerCard
                  answer={queryResponse.answer}
                  verify={queryResponse.verify}
                />
                <CredibilityDerivation
                  verify={queryResponse.verify}
                  evidenceCount={queryResponse.evidence.length}
                  toolResults={queryResponse.tool_results}
                />
                <Citations citations={queryResponse.citations} />
                <ToolCalls toolResults={queryResponse.tool_results} />
                <MemoryPanel
                  recalledMemories={queryResponse.recalled_memories}
                  memoryWrites={queryResponse.memory_writes}
                />
                <EvidenceList evidence={queryResponse.evidence} />
              </div>
              <div>
                <ExecutionTrace trace={queryResponse.trace} />
                <MemoryEvolution
                  userId={userId}
                  refreshKey={memoryRefreshKey}
                />
                <RawState state={queryResponse} />
              </div>
            </div>
          </>
        ) : (
          <Card className="text-center py-10 border-dashed">
            <div className="text-[2rem]">🧠</div>
            <div className="font-bold text-[1.05rem] mt-2">
              输入问题，开始一次 Agent 编排
            </div>
            <div className="text-muted text-[0.86rem] mt-1.5">
              点上方示例问题，或直接提问 — 无需 API key
              也能体验完整链路（离线 fallback）。
            </div>
          </Card>
        )}
      </main>
    </div>
  );
}

export default function Page() {
  return (
    <ToastProvider>
      <PageInner />
    </ToastProvider>
  );
}
