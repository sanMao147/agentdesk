# Replace Streamlit with Next.js V16 + Tailwind Frontend Spec

## Why
当前 UI 由 `streamlit_app.py` 单文件 + 大段 `unsafe_allow_html` CSS/HTML 字符串构成：状态、样式、交互、渲染强耦合，组件复用难、SSR/SEO 缺失、性能受 Streamlit 全量 rerun 模型限制。改用 Next.js 16 (App Router) + Tailwind CSS v4 可以拆分组件、走 RSC/CSR 分层、按需流式渲染，同时保留原"深空玻璃拟态"视觉语言。

后端 FastAPI 严格遵循 RESTful 规范（资源导向 URL + 正确 HTTP 方法 + 标准 status code + JSON 媒体类型），仅负责数据/业务；Next.js 仅负责 UI 渲染与交互。两侧通过 `/api/*` 契约解耦。

## What Changes
- **BREAKING** 删除 `streamlit_app.py`、`.streamlit/`、`app/web/index.html`，移除 `requirements.txt` 中的 `streamlit` 依赖；FastAPI `/` 不再返回静态 HTML。
- 新增 Next.js 16 前端工程：`web/` 目录（App Router + Tailwind v4 + TypeScript + `next/font` Inter/JetBrains Mono），仅做 UI 渲染与交互，不持有业务状态。
- 后端 FastAPI 重构为 RESTful 资源 API（统一 `/api` 前缀、资源命名复数、HTTP 方法语义化、status code 规范）：
  - `GET    /api/config` —— 取运行时配置资源（singleton）。
  - `PATCH  /api/config` —— 部分更新配置（body `{chat_model?: string}`）；切换 chat 模型同步写 `settings.chat_model` 与 `os.environ["CHAT_MODEL"]`。
  - `POST   /api/sessions` —— 创建会话资源，201 返回 `{session_id}`。
  - `GET    /api/users/{user_id}/memories` —— 列出用户长期记忆（含 `superseded_by` 审计链），200 返回 `{live: [...], dead: [...]}`。
  - `GET    /api/index` —— 取索引资源（`n_chunks`、`index_signature`、`use_llm`、`embedding_model`）。
  - `POST   /api/index/rebuilds` —— 创建一次重建任务（同步执行），201 返回 `{n_chunks, index_signature}`；资源命名遵循 "动作名词化"。
  - `POST   /api/queries` —— 创建一次提问（替代旧 `/chat`），201 返回完整 query 资源（含 `answer`、`citations`、`evidence`、`tool_results`、`verify`、`iterations`、`trace`、`recalled_memories`、`memory_writes`、`working_memory`）。
  - `GET    /api/health` —— 健康检查，200 返回 `{status: "ok"}`。
  - 全部 API 启用 CORS（开发态允许 `http://localhost:3000`，可通过 `CORS_ORIGINS` 环境变量配置）；统一返回 `application/json`，错误体为 `{error: {code, message}}`。
- 前端实现原 Streamlit 全部面板，组件化拆分（详见 tasks.md）：
  - Hero、Sidebar（运行状态 / 配置 KPI / 记忆身份 / 示例问题 / 架构）、提问区（含 chat 模型选择 + 示例 chip）、KPI 行、对话历史（短期记忆）、Answer 卡 + Faithfulness 环形仪表、可信度推导（含标尺）、Citations、Tool calls、Memory（召回/写入）、Retrieved evidence、Execution trace 时间线、Memory evolution 审计、原始 state 折叠面板。
- 视觉系统迁移：原 CSS 变量（`--bg`/`--brand`/`--grad` 等）落到 `web/app/globals.css` 的 `:root`，Tailwind v4 `@theme` 映射为 `bg-brand`/`text-ink`/`bg-grad` 等 token；玻璃拟态卡片、KPI、环形仪表、时间线节点全部用 React 组件 + Tailwind 重写。
- Docker 化：`Dockerfile` 多阶段构建（前端 `next build` → `.next/standalone`，后端 Python 镜像拷贝 `web/.next/standalone` + `web/public`），FastAPI 不再服务前端；`docker-compose.yml` 增加 `web` 服务（Node 20 alpine + `next start`），`api` 仅暴露 `/api/*`。
- 文档同步：`README.md` 删除 Streamlit 段、新增 `web/` 启动与构建说明、更新目录树。

## Impact
- Affected specs: 无既有 spec（项目首次引入 spec-driven 流程）。
- Affected code:
  - 删除：`streamlit_app.py`、`.streamlit/config.toml`、`.streamlit/secrets.toml.example`、`app/web/index.html`。
  - 修改：`app/api/main.py`（拆为 `app/api/main.py` + 资源路由模块 + CORS + RESTful 重构 + 扩展 `QueryResponse`）、`app/config.py`（暴露运行时 mutator + `cors_origins` 字段）、`requirements.txt`（去 streamlit）、`Dockerfile`（多阶段）、`docker-compose.yml`（加 web 服务）、`README.md`、`.gitignore`（加 `web/.next/`、`web/node_modules/`）。
  - 新增：`web/` 整个 Next.js 工程（`package.json`、`next.config.ts`、`tsconfig.json`、`postcss.config.mjs`、`app/`、`components/`、`lib/`、`public/`）。
  - 新增后端模块：`app/api/routes/config.py`、`app/api/routes/sessions.py`、`app/api/routes/users.py`、`app/api/routes/memories.py`、`app/api/routes/index.py`、`app/api/routes/queries.py`、`app/api/routes/health.py`、`app/api/deps.py`、`app/api/errors.py`（统一异常→JSON 错误体）。

## ADDED Requirements

### Requirement: Frontend/Backend Responsibility Split
The system SHALL strictly separate responsibilities: FastAPI backend owns data + business logic (RAG orchestration, memory, index, config); Next.js frontend owns UI rendering + interaction. They communicate only via the documented `/api/*` RESTful contract; the frontend never imports Python modules or calls internal helpers.

#### Scenario: Frontend never reaches into Python
- **WHEN** any frontend code needs runtime config, memory list, or runs a query
- **THEN** it issues an HTTP request to the corresponding `/api/*` endpoint
- **AND** never imports from `app.*` or relies on in-process state

#### Scenario: Backend never renders HTML
- **WHEN** FastAPI receives any request to `/api/*`
- **THEN** it returns `application/json` (or standard error JSON)
- **AND** does not serve `text/html` for any route (static HTML serving removed)

### Requirement: RESTful Backend API
The FastAPI backend SHALL expose a RESTful API: resource-oriented plural-noun URLs under `/api`, correct HTTP methods (GET for read, POST for create, PATCH for partial update), standard status codes (200 OK, 201 Created, 4xx/5xx), and a unified JSON error envelope `{error: {code, message}}`.

#### Scenario: Resource URL naming
- **WHEN** listing user memories
- **THEN** the endpoint is `GET /api/users/{user_id}/memories` (nested resource, plural nouns)
- **AND** NOT `GET /api/memory/{user_id}` or `GET /api/getMemories`

#### Scenario: Create a query (replaces /chat)
- **WHEN** frontend POSTs to `/api/queries` with body `{query, user_id, session_id}`
- **THEN** backend returns **201 Created** with the full query resource in body
- **AND** the resource includes `answer`, `citations`, `evidence`, `tool_results`, `verify`, `iterations`, `trace`, `recalled_memories`, `memory_writes`, `working_memory`

#### Scenario: Patch config (replaces /config/chat_model)
- **WHEN** frontend PATCHes `/api/config` with body `{chat_model: "Qwen/Qwen2.5-32B-Instruct"}`
- **THEN** backend updates `settings.chat_model` and `os.environ["CHAT_MODEL"]`
- **AND** returns **200 OK** with the updated full config resource

#### Scenario: Create session
- **WHEN** frontend POSTs to `/api/sessions` (empty body)
- **THEN** backend returns **201 Created** with `{session_id: <uuid4 hex>}`

#### Scenario: Create index rebuild task
- **WHEN** frontend POSTs to `/api/index/rebuilds` (empty body)
- **THEN** backend synchronously rebuilds the index
- **AND** returns **201 Created** with `{n_chunks, index_signature}`

#### Scenario: Unified error envelope
- **WHEN** any endpoint raises (e.g., 422 validation, 500 server error)
- **THEN** response body is `{"error": {"code": "<string>", "message": "<human readable>"}}`
- **AND** status code matches the error class (400/404/422/500)

#### Scenario: CORS for local dev
- **WHEN** browser at `http://localhost:3000` calls any `/api/*` endpoint
- **THEN** response includes `Access-Control-Allow-Origin: http://localhost:3000` (configurable via `CORS_ORIGINS` env)
- **AND** preflight `OPTIONS` requests are handled by CORSMiddleware

### Requirement: Next.js 16 Frontend Application
The system SHALL provide a Next.js 16 (App Router) + Tailwind CSS v4 + TypeScript frontend at `web/`, replacing the Streamlit UI, preserving all existing panels and the dark glass-morphism visual language.

#### Scenario: User opens the console
- **WHEN** user navigates to `http://localhost:3000/`
- **THEN** page renders Hero, sidebar, ask bar, demo chips, and an empty-state placeholder card
- **AND** sidebar shows live runtime status (real LLM vs offline fallback), vector backend, top_k, max_iterations, KB chunks fetched from `GET /api/config`

#### Scenario: User submits a query
- **WHEN** user types a question and clicks 运行 (or presses Enter)
- **THEN** frontend POSTs to `/api/queries` with `{query, user_id, session_id}`
- **AND** shows a spinner with text "Agent 编排执行中：记忆召回 → 改写 → 检索 → 工具 → 生成 → 反思 → 记忆写入…"
- **AND** on success (201) renders KPI row, chat history, answer card with faithfulness gauge, credibility derivation, citations, tool calls, memory cards, evidence list, execution trace timeline, and memory evolution audit

#### Scenario: Demo question one-click
- **WHEN** user clicks a demo chip (e.g. "📊 多公司营收")
- **THEN** the chip's query fills the input box and immediately triggers a `POST /api/queries`

#### Scenario: Chat model switch
- **WHEN** user picks a model from the chat 模型 select (or types a custom name)
- **THEN** frontend PATCHes `/api/config` with `{chat_model: <name>}`
- **AND** sidebar reflects the new model on next `/api/config` poll
- **AND** when `use_llm` is false, the select is disabled with a hint "离线 fallback 不调用大模型，切换无效（需在 .env 配 key）"

#### Scenario: New session
- **WHEN** user clicks "新会话" in the sidebar
- **THEN** frontend POSTs `/api/sessions`, receives a fresh `session_id` (201), stores it client-side, and clears the main panel back to the empty state

#### Scenario: Index rebuild
- **WHEN** user clicks "重建索引" (placed under sidebar KB chunks KPI)
- **THEN** frontend POSTs `/api/index/rebuilds` and shows a toast/spinner until the 201 response returns the new chunk count

#### Scenario: Error during run
- **WHEN** `/api/queries` returns 5xx or network fails
- **THEN** an error card appears with `运行出错（多为模型接口超时/报错）：{code}: {message}　可在上方换一个更稳的模型重试。` (using the unified error envelope fields)

### Requirement: Visual Design Token Migration
The frontend SHALL migrate the existing CSS design tokens (deep-space dark theme, glass-morphism cards, brand gradient) to Tailwind v4 `@theme`, preserving visual fidelity with the Streamlit version.

#### Scenario: Token mapping
- **WHEN** developer writes `className="bg-surface text-ink border-stroke"`
- **THEN** the rendered styles use the corresponding `:root` CSS variables (`--surface`, `--ink`, `--stroke`)

#### Scenario: Brand gradient
- **WHEN** any element uses `bg-grad` (Hero after-glow, KPI bottom bar, evidence bar, gauge, etc.)
- **THEN** it renders `linear-gradient(120deg,#7c5cff 0%,#5b8cff 45%,#22d3ee 100%)`

## MODIFIED Requirements

### Requirement: Project Layout & Deployment
The project SHALL ship as a two-service stack: FastAPI (Python, `/api/*` RESTful backend) and Next.js (Node, `/` UI). `docker-compose up` runs both.

#### Scenario: Local development
- **WHEN** developer runs `uvicorn app.api.main:app --reload` and `cd web && npm run dev`
- **THEN** API is reachable at `http://localhost:8000/api/*` and UI at `http://localhost:3000/`
- **AND** Next.js dev server proxies `/api/*` to the FastAPI backend (no browser CORS in dev either)

#### Scenario: Docker compose full stack
- **WHEN** user runs `docker compose up --build`
- **THEN** `web` service starts `next start` on port 3000, `api` service starts uvicorn on port 8000, `qdrant` and `redis` start as before
- **AND** `web` reaches `api` via internal network (`API_BASE_URL=http://api:8000/api` server-side, `NEXT_PUBLIC_API_BASE_URL=/api` client-side via rewrite)

## REMOVED Requirements

### Requirement: Streamlit Console
**Reason**: Replaced by the Next.js frontend for componentization, performance, and modern tooling.
**Migration**:
- Delete `streamlit_app.py`, `.streamlit/` directory.
- Remove `streamlit>=1.36` from `requirements.txt`.
- Remove `streamlit run streamlit_app.py` instructions from `README.md`.
- All panels (Hero, sidebar, KPI, gauge, trace timeline, memory audit, etc.) are reimplemented as React components under `web/components/`.

### Requirement: Legacy Non-RESTful API Endpoints
**Reason**: Old endpoints (`POST /chat`, `GET /`) do not follow RESTful conventions and mix UI serving with business API.
**Migration**:
- `POST /chat` → `POST /api/queries` (resource creation, 201 response).
- `GET /` (FileResponse HTML) → removed; UI served by Next.js at `/`.
- `GET /health` → `GET /api/health`.
- Any RPC-style verbs in URL paths (`rebuild`, `chat_model`) replaced with resource nouns (`/api/index/rebuilds`, `PATCH /api/config`).
