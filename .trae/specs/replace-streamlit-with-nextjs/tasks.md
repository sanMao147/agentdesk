# Tasks

## Phase 1 — Backend RESTful API 重构（前端无依赖，先做）

- [x] Task 1: 在 `app/config.py` 的 `Settings` 增加 `cors_origins: str = "http://localhost:3000"` 字段；新增 `set_chat_model(name: str) -> None` mutator（同步写 `self.chat_model` 与 `os.environ["CHAT_MODEL"]`）；新增 `index_signature` 只读 property（返回 `{"use_llm": bool, "model": embedding_model|offline-hash}`，照搬 `streamlit_app._emb_signature`）。
- [x] Task 2: 新建 `app/api/errors.py`：定义 `ApiError(code: str, message: str, status: int)` 异常类 + `register_exception_handlers(app)` 注册统一处理器，所有未捕获异常响应体为 `{"error": {"code", "message"}}`，status 与异常匹配（400/404/422/500）。
- [x] Task 3: 重写 `app/api/main.py`：创建 `FastAPI(title="AgentDesk API", version="0.5.0")`；注册 CORSMiddleware（`allow_origins=settings.cors_origins.split(",")`、`allow_methods=["GET","POST","PATCH","OPTIONS"]`、`allow_headers=["*"]`）；移除原 `home()` 与 `index.html` 引用；调用 `register_exception_handlers(app)`；通过 `app.include_router(...)` 挂载下列资源路由（统一 `/api` 前缀）。
- [x] Task 4: 新建 `app/api/routes/health.py`：`GET /api/health` 返回 `{"status": "ok"}`，200。
- [x] Task 5: 新建 `app/api/routes/config.py`：
  - `GET /api/config` —— 返回 `{use_llm, vector_backend, top_k, max_iterations, chat_model, embedding_model, n_chunks, index_signature}`（`n_chunks` 调 `app/api/routes/index.py` 的辅助函数读取）。
  - `PATCH /api/config` —— body `ConfigPatch {chat_model: str | None}`；若 `chat_model` 非空且 `settings.use_llm` 为真，调 `settings.set_chat_model(chat_model)`；返回 200 + 更新后的完整 config 资源；若 `use_llm=false` 且尝试改 chat_model，返回 400 `{error: {code: "offline_mode", message: "..."}}`。
- [x] Task 6: 新建 `app/api/routes/sessions.py`：`POST /api/sessions`（body 可空）→ 生成 `uuid4().hex` → 201 返回 `{session_id}`。
- [x] Task 7: 新建 `app/api/routes/index.py`：
  - 辅助函数 `get_index_info() -> dict`：读 `INDEX_PATH` 得 `n_chunks`，读 `index_meta.json` 得 `index_signature`，附加 `use_llm`、`embedding_model`。
  - 辅助函数 `rebuild_index() -> dict`：清 `app.rag.cache` 单例 + `app.graph.nodes._retriever` → `build_index()` → 写 `index_meta.json` → 返回 `{n_chunks, index_signature, use_llm, embedding_model}`。
  - `GET /api/index` → 200 返回 `get_index_info()`。
  - `POST /api/index/rebuilds` → 201 返回 `rebuild_index()` 结果。
- [x] Task 8: 新建 `app/api/routes/queries.py`：
  - `QueryCreate {query: str, user_id: str = "anonymous", session_id: str | None = None}` 请求模型。
  - `QueryResponse` 响应模型：在原 `ChatResponse` 字段基础上新增 `working_memory: dict`（含 `messages`、`running_summary`、`round_count`）。
  - `POST /api/queries` → 调 `run_query(...)` → 组装响应 → **201 Created** 返回；异常经 `ApiError` 包装为统一错误体。
- [x] Task 9: 新建 `app/api/routes/memories.py`：
  - `GET /api/users/{user_id}/memories` → 调 `app.memory.store.get_memory_store().list_by_user(user_id)` → 按 `superseded_by` 是否为空分桶为 `{live: [...], dead: [...]}`，每条字段含 `mem_id, kind, text, version, use_count, updated_at, superseded_by` → 200 返回。
- [x] Task 10: 把 `app/api/routes/__init__.py` 与 `app/api/deps.py`（共享 dependency，如 `get_settings()`）建好；确保 `python -m uvicorn app.api.main:app --reload` 启动后 `/api/health`、`/api/config`、`/api/sessions`、`/api/queries`、`/api/users/alice/memories`、`/api/index`、`/api/index/rebuilds` 全部可达，OpenAPI 文档 `/docs` 显示完整 schema。

## Phase 2 — Next.js 工程初始化

- [x] Task 11: 在仓库根目录 `web/` 下用 `npx create-next-app@latest web --typescript --tailwind --app --no-src-dir --import-alias "@/*"` 初始化 Next.js 16 工程；调整 `package.json` 确保 `next@^16`、`react@^19`、`react-dom@^19`、`tailwindcss@^4`、`typescript@^5`。
  - [x] SubTask 11.1: 配置 `next.config.ts`：`output: 'standalone'`、`reactStrictMode: true`；`rewrites()` 把 `/api/*` 反代到 `${API_BASE_URL || http://localhost:8000}/api/*`（开发态浏览器同源请求避免 CORS）。
  - [x] SubTask 11.2: 配置 `tsconfig.json`：`paths: {"@/*": ["./*"]}`、`target: ES2022`、`moduleResolution: bundler`。
  - [x] SubTask 11.3: 配置 `postcss.config.mjs` 用 `@tailwindcss/postcss`；`app/globals.css` 顶部 `@import "tailwindcss";`。
- [x] Task 12: 在 `web/app/globals.css` 落 `:root` CSS 变量（照搬 `streamlit_app.py` 中的 token：`--bg`/`--bg2`/`--surface`/`--surface-2`/`--stroke`/`--stroke-2`/`--ink`/`--muted`/`--faint`/`--brand`/`--brand2`/`--accent`/`--ok`/`--warn`/`--bad`/`--r-s`/`--r-m`/`--r-l`/`--grad`），并通过 Tailwind v4 `@theme inline` 映射为 `bg-bg`/`bg-surface`/`text-ink`/`text-muted`/`border-stroke`/`bg-grad` 等 token；写入背景渐变、网格、字体（Inter / JetBrains Mono）。
- [x] Task 13: 在 `web/app/layout.tsx` 用 `next/font/google` 加载 `Inter` 与 `JetBrains_Mono`，挂到 `<html>` 的 `className`；写入 `metadata`（title `AgentDesk · Agentic RAG 控制台`、description、OpenGraph）。
- [x] Task 14: 在 `web/lib/api.ts` 封装 fetch 客户端：
  - `const API_BASE = '/api'`（由 Next.js rewrite 转发到后端，避免浏览器跨域）。
  - 导出：`getConfig()`、`patchConfig({chat_model?})`、`createSession()`、`listMemories(userId)`、`getIndex()`、`rebuildIndex()`、`createQuery({query, user_id, session_id})`。
  - 错误处理：解析 `{error: {code, message}}` 抛 `ApiError` 类（带 `code`、`message`、`status`）。
  - 导出 TypeScript 类型：`Config`、`QueryResponse`、`MemoryList`、`MemoryRecord`、`IndexInfo`、`Session`、`TraceStep`、`Evidence`、`Verify`、`ToolResult`、`WorkingMemory`（字段对照后端 schema）。
- [x] Task 15: 新建 `web/lib/constants.ts`：导出 `NODE_LABELS`（与 `streamlit_app.py` 中字典一致）、`MEM_KIND`（kind→[icon,label,color]）、`SAMPLES`、`DEMOS`（5 个示例 chip）、`CHAT_MODEL_PRESETS`（5 个预设 + "自定义…"）。

## Phase 3 — 共享 UI 原子组件

- [x] Task 16: 在 `web/components/ui/Card.tsx` 实现玻璃拟态卡片（默认 `bg-surface border border-stroke rounded-r-m backdrop-blur-md`，hover `translateY(-2px) border-stroke-2` 过渡）；导出 `Card`、`CardHeader`、`CardBody`。
- [x] Task 17: 在 `web/components/ui/Eyebrow.tsx` 实现区段标题（左侧 18×2 渐变短杠 + 0.74rem 字重 700 大写字间距 0.16em）。
- [x] Task 18: 在 `web/components/ui/Pill.tsx` 实现 pill 标签，支持变体 `default`/`tool`/`bad`/自定义颜色（`background: {col}22; color: {col}`）。
- [x] Task 19: 在 `web/components/ui/Gauge.tsx` 实现 Faithfulness 环形仪表（conic-gradient + 中心镂空 + 大数字百分比，props: `pct: number`、`color: string`）。
- [x] Task 20: 在 `web/components/ui/Spinner.tsx` 实现加载态（渐变圆环旋转 + 文案 props.label）。
- [x] Task 21: 在 `web/components/ui/Expander.tsx` 实现折叠面板（`<details>` 风格，但样式覆写为玻璃卡，含 summary 文本与展开图标）。
- [x] Task 22: 在 `web/components/ui/Toast.tsx` 实现简易 toast（context + portal），用于重建索引反馈。

## Phase 4 — 业务面板组件

- [x] Task 23: `web/components/Sidebar.tsx`（client）—— 渲染：① 运行状态卡（绿/黄 dot + 真实大模型/离线 Fallback）；② 2×2 KPI 网格（vector_backend / top_k / max_iterations / KB chunks + 重建索引按钮）；③ 记忆身份区（user_id 输入 + 会话 id 截断显示 + 新会话按钮）；④ 试一试示例问题列表；⑤ 架构/流程 expander。Props: `config`、`userId`、`sessionId`、`onNewSession`、`onRebuildIndex`、`onPickSample`。
- [x] Task 24: `web/components/Hero.tsx`（server）—— 渲染 Hero 卡（标题渐变文本、副标题、chips：模型状态 / 混合检索 / MCP 工具层 / Critic 反思 / KB chunks），右上 conic-gradient 18s 旋转光晕。Props: `config`。
- [x] Task 25: `web/components/AskBar.tsx`（client）—— 含 chat 模型 select（Qwen 系列预设 + 自定义输入）+ 示例 chip 行（5 个）+ 输入框 + 运行按钮；Enter 触发；模型切换时调 `patchConfig({chat_model})`；示例 chip 点击填入并立即触发。Props: `config`、`onRun`、`onModelChange`、`initialQuery`。
- [x] Task 26: `web/components/KpiRow.tsx`（server）—— 4 列网格：Faithfulness（数值+达标/未达标）、反思轮数、命中证据数、评判方式；底部 3px 渐变条。Props: `verify`、`iterations`、`evidenceCount`。
- [x] Task 27: `web/components/ChatHistory.tsx`（server）—— 渲染短期记忆气泡：running_summary 顶部条 + 用户/助手气泡（左右对齐 + 不同背景）+ 底部统计行。Props: `workingMemory`、`sessionId`。
- [x] Task 28: `web/components/AnswerCard.tsx`（server）—— Faithfulness 仪表 + 可信/不足标签 + 答案文本（white-space: pre-wrap）。Props: `answer`、`verify`。
- [x] Task 29: `web/components/CredibilityDerivation.tsx`（server）—— 4 步推导（评判方式 / 依据 / 计算 / 阈值判定）+ 标尺（0.0–1.0 渐变条 + 0.6 阈值刻度 + 当前分值圆点）。Props: `verify`、`evidenceCount`、`toolResults`。
- [x] Task 30: `web/components/Citations.tsx`（server）—— 引用 pill 列表。Props: `citations: string[]`。
- [x] Task 31: `web/components/ToolCalls.tsx`（server）—— 工具调用卡片列表（pill 显示 ✓/✕ + 工具名 + via + 等宽输出）。Props: `toolResults`。
- [x] Task 32: `web/components/MemoryPanel.tsx`（server）—— 召回记忆卡片（kind pill + 召回说明 + 文本）+ 本轮写入/更新 pill 行。Props: `recalledMemories`、`memoryWrites`。
- [x] Task 33: `web/components/EvidenceList.tsx`（server）—— 证据卡列表（排名徽章 + chunk_id + doc_id·score + 进度条 + 截断文本）。Props: `evidence`。
- [x] Task 34: `web/components/ExecutionTrace.tsx`（server）—— 时间线（左侧渐变竖线 + 节点圆点 + 标题 + 描述），按 `NODE_LABELS` 映射；不同 node 类型计算不同描述（memory_retrieve/planner/retrieval/tool/writer/critic/memory_write/summarize）。Props: `trace`。
- [x] Task 35: `web/components/MemoryEvolution.tsx`（client）—— 调 `listMemories(userId)` 拉取，渲染现行记忆卡（kind pill + 命中次数 + 文本 + 被取代旧值链 strikethrough）+ 底部统计。Props: `userId`、`refreshKey`（每次 chat 完成后递增触发刷新）。
- [x] Task 36: `web/components/RawState.tsx`（server）—— Expander 包裹的 JSON 调试视图（用 `<pre>` + 等宽字体 + 滚动）。Props: `state`。

## Phase 5 — 主页面组装与状态管理

- [x] Task 37: `web/app/page.tsx`（client component，因需交互状态）—— 用 `useState` 管理 `config`、`userId`（默认 `alice`）、`sessionId`（mount 时调 `createSession()`）、`queryResponse`、`loading`、`error`、`query`、`memoryRefreshKey`；`useEffect` 拉 `getConfig`；组装布局：左侧 Sidebar（sticky）、右侧主区（Hero + AskBar + 结果区）。
  - [x] SubTask 37.1: 实现 `runQuery(q)`：setLoading → `createQuery()` → setQueryResponse / setError → 递增 `memoryRefreshKey`；空态显示虚线占位卡。
  - [x] SubTask 37.2: 结果区分两列（main 1.4 / side 1）：main 含 KPI、ChatHistory、AnswerCard、CredibilityDerivation、Citations、ToolCalls、MemoryPanel、EvidenceList；side 含 ExecutionTrace、MemoryEvolution、RawState。
  - [x] SubTask 37.3: 错误态显示红色卡片 `运行出错（多为模型接口超时/报错）：{error.code}: {error.message}　可在上方换一个更稳的模型重试。`（用 `ApiError` 的字段）。

## Phase 6 — 清理与部署

- [x] Task 38: 删除 `streamlit_app.py`、`.streamlit/config.toml`、`.streamlit/secrets.toml.example`、`app/web/index.html`（注意 `app/web/` 目录可整删）；从 `requirements.txt` 移除 `streamlit>=1.36`。
- [x] Task 39: 更新 `.gitignore` 增加 `web/.next/`、`web/node_modules/`、`web/.env*.local`；新增 `web/.env.example` 含 `API_BASE_URL=http://localhost:8000/api`（server-side rewrite 用，不放 `NEXT_PUBLIC_` 前缀避免暴露）。
- [x] Task 40: 重写 `Dockerfile` 为多阶段：stage1 `node:20-alpine` 拷 `web/` 跑 `npm ci && npm run build` 产出 `web/.next/standalone`；stage2 `python:3.11-slim` 装后端依赖 + 拷 `app/` + `scripts/` + `data/` + `eval/`，作为 `api` 服务镜像；新增 `web/Dockerfile`（`node:20-alpine` + `npm ci --omit=dev` + `cp -r .next/standalone /app` + `CMD node server.js`）。
- [x] Task 41: 更新 `docker-compose.yml`：新增 `web` 服务（build `./web`，port 3000，env `API_BASE_URL=http://api:8000/api`、`HOSTNAME=0.0.0.0`、`PORT=3000`，depends_on api）；`api` 服务 command 不变；保留 qdrant/redis。
- [x] Task 42: 更新 `README.md`：删除 "可视化仪表盘（推荐演示）：streamlit run streamlit_app.py" 行；新增 "## 🖥️ 前端" 段说明 `cd web && npm install && npm run dev`（3000） + 后端 `uvicorn app.api.main:app --reload`（8000）；更新目录树加 `web/` 与 `app/api/routes/`；更新里程碑加 "前端 Next.js 化 + API RESTful 化"。

## Phase 7 — 验证

- [x] Task 43: 启动后端 `uvicorn app.api.main:app --reload`，用 curl 验证：`GET /api/config`、`POST /api/sessions`（201）、`GET /api/users/alice/memories`、`GET /api/index`、`POST /api/index/rebuilds`（201）、`POST /api/queries`（201，含 `working_memory`）、`PATCH /api/config`（200）。验证错误路径返回 `{error: {code, message}}`。
- [x] Task 44: 启动前端 `cd web && npm run dev`，浏览器手测：空态 → 点示例 chip → 自动运行 → KPI/答案/仪表/时间线/记忆审计全部渲染；切换 chat 模型 → sidebar 反映；新会话按钮 → 主区清空；重建索引 → toast + KB chunks 更新；断开后端模拟错误 → 错误卡片显示 code+message。
- [x] Task 45: `cd web && npm run build` 通过；`npm run lint` 无 error。

# Task Dependencies
- Phase 2 依赖 Phase 1（前端要调真实端点）；Phase 3 可与 Phase 1/2 并行。
- Phase 4 依赖 Phase 2（组件用 `lib/api.ts` 类型）+ Phase 3（用原子组件）。
- Phase 5 依赖 Phase 4。
- Phase 6 依赖 Phase 5（功能验证后再删 Streamlit）；Task 38 必须在 Task 43/44 验证通过后执行。
- Phase 7 依赖 Phase 6。
- 可并行：Task 4–9（不同资源路由，但建议 Task 2/3 先做以定基线）、Task 16–22（不同原子组件）、Task 23–36（不同业务组件，但建议按依赖顺序：Sidebar/Hero/AskBar 先做，其它再并行）。
