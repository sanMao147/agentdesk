// API client for AgentDesk backend.
// All requests go through the Next.js rewrite (/api/* -> backend), so the
// browser stays same-origin and we avoid CORS in dev.

const API_BASE = "/api";

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.message = message;
    this.status = status;
  }
}

// ---------- Types ----------

export interface IndexSignature {
  use_llm: boolean;
  model: string;
}

export interface Config {
  use_llm: boolean;
  vector_backend: string;
  top_k: number;
  max_iterations: number;
  chat_model: string;
  embedding_model: string;
  n_chunks: number;
  index_signature: IndexSignature | null;
}

export interface Session {
  session_id: string;
}

export interface IndexInfo {
  n_chunks: number;
  index_signature: IndexSignature | null;
  use_llm: boolean;
  embedding_model: string;
}

export interface MemoryRecord {
  mem_id: string;
  kind: string;
  text: string;
  version: number;
  use_count: number;
  updated_at: number;
  superseded_by: string | null;
}

export interface MemoryList {
  live: MemoryRecord[];
  dead: MemoryRecord[];
}

export interface Verify {
  score: number;
  faithful: boolean;
  method: string;
  detail: unknown;
  reason?: string;
}

export interface Evidence {
  chunk_id: string;
  doc_id: string;
  score: number;
  text: string;
}

export interface ToolResult {
  tool: string;
  out: {
    ok?: boolean;
    result?: string;
    error?: string;
    via?: string;
  };
}

export interface TraceStep {
  node: string;
  iter?: number;
  mode?: string;
  hits?: unknown[];
  called?: string[];
  queries?: string[];
  recalled?: unknown[];
  has_short?: boolean;
  wrote?: string[];
  summary_len?: number;
  citations?: string[];
  faithful?: boolean;
  score?: number;
}

export interface WorkingMemory {
  messages: { role: string; content: string }[];
  running_summary: string;
  round_count: number;
}

export interface QueryResponse {
  answer: string;
  citations: string[];
  evidence: Evidence[];
  tool_results: ToolResult[];
  verify: Verify;
  iterations: number;
  trace: TraceStep[];
  recalled_memories: { kind: string; text: string }[];
  memory_writes: { kind: string; text: string; version: number }[];
  working_memory: WorkingMemory;
}

// ---------- Internal request helper ----------

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let code = "http_error";
    let message = `Request failed with status ${res.status}`;
    try {
      const data = await res.json();
      if (data?.error?.code) code = data.error.code;
      if (data?.error?.message) message = data.error.message;
    } catch {
      // response had no JSON body; keep defaults
    }
    throw new ApiError(code, message, res.status);
  }

  return res.json() as Promise<T>;
}

// ---------- Public API ----------

export function getConfig(): Promise<Config> {
  return request<Config>("GET", "/config");
}

export function patchConfig(body: { chat_model?: string }): Promise<Config> {
  return request<Config>("PATCH", "/config", body);
}

export function createSession(): Promise<Session> {
  return request<Session>("POST", "/sessions");
}

export function listMemories(userId: string): Promise<MemoryList> {
  return request<MemoryList>("GET", `/users/${encodeURIComponent(userId)}/memories`);
}

export function getIndex(): Promise<IndexInfo> {
  return request<IndexInfo>("GET", "/index");
}

export function rebuildIndex(): Promise<IndexInfo> {
  return request<IndexInfo>("POST", "/index/rebuilds");
}

export function createQuery(body: {
  query: string;
  user_id: string;
  session_id: string | null;
}): Promise<QueryResponse> {
  return request<QueryResponse>("POST", "/queries", body);
}
