# Checklist

## 后端 RESTful API
- [x] `app/config.py` 的 `Settings` 增加 `cors_origins: str = "http://localhost:3000"` 字段。
- [x] `app/config.py` 暴露 `set_chat_model(name)` mutator（同步写 `os.environ["CHAT_MODEL"]`）。
- [x] `app/config.py` 暴露 `index_signature` 只读 property。
- [x] `app/api/errors.py` 定义 `ApiError(code, message, status)` 异常 + `register_exception_handlers(app)`，所有未捕获异常响应体为 `{"error": {"code", "message"}}`。
- [x] `app/api/main.py` 注册 CORSMiddleware（origins 来自 `settings.cors_origins.split(",")`，methods 含 `GET/POST/PATCH/OPTIONS`）。
- [x] `app/api/main.py` 移除原 `home()` 与 `index.html` 引用，不再服务任何 HTML。
- [x] 所有 API 路由统一 `/api` 前缀，路由模块拆到 `app/api/routes/`。
- [x] `GET /api/health` 200 返回 `{status: "ok"}`。
- [x] `GET /api/config` 返回字段齐全：`use_llm`、`vector_backend`、`top_k`、`max_iterations`、`chat_model`、`embedding_model`、`n_chunks`、`index_signature`。
- [x] `PATCH /api/config` body `{chat_model?: string}`，更新后 200 返回完整 config 资源；`use_llm=false` 时尝试改 chat_model 返回 400 `{error:{code:"offline_mode",...}}`。
- [x] `POST /api/sessions` 201 返回 `{session_id: <32 位 hex>}`。
- [x] `GET /api/users/{user_id}/memories` 200 返回 `{live:[...], dead:[...]}`，dead 中每条 `superseded_by` 非空。
- [x] `GET /api/index` 200 返回 `{n_chunks, index_signature, use_llm, embedding_model}`。
- [x] `POST /api/index/rebuilds` 201 返回 `{n_chunks, index_signature, use_llm, embedding_model}`；执行时清掉 `app.rag.cache` 单例 + `app.graph.nodes._retriever`，重写 `index_meta.json`。
- [x] `POST /api/queries` 201 返回完整 query 资源，含 `answer`、`citations`、`evidence`、`tool_results`、`verify`、`iterations`、`trace`、`recalled_memories`、`memory_writes`、`working_memory`（`working_memory` 含 `messages`、`running_summary`、`round_count`）。
- [x] 错误响应统一为 `{"error": {"code": "<string>", "message": "<human readable>"}}`，status 与异常类匹配（400/404/422/500）。404 由 `StarletteHTTPException` handler 覆盖（已修复原 FastAPI 默认 `{"detail":"Not Found"}` 问题）。
- [x] `python -m uvicorn app.api.main:app --reload` 启动后所有端点可达，`/docs` 显示完整 schema。
- [x] 前端代码不 import 任何 `app.*` Python 模块。

## Streamlit 清理
- [x] `streamlit_app.py` 已删除。
- [x] `.streamlit/config.toml`、`.streamlit/secrets.toml.example` 已删除（`.streamlit/` 目录整体移除）。
- [x] `app/web/index.html` 已删除（`app/web/` 目录整体移除）。
- [x] `requirements.txt` 不再包含 `streamlit>=1.36`。
- [x] `README.md` 不再出现 `streamlit run` 字样。

## Next.js 工程结构
- [x] `web/package.json` 中 `next` 版本 `^16`、`react`/`react-dom` `^19`、`tailwindcss` `^4`、`typescript` `^5`。
- [x] `web/next.config.ts` 开启 `output: 'standalone'`、`reactStrictMode: true`。
- [x] `web/next.config.ts` `rewrites()` 把 `/api/*` 反代到 `${API_BASE_URL}/api/*`（避免开发态浏览器跨域）。
- [x] `web/tsconfig.json` 配置 `paths: {"@/*": ["./*"]}`、`target: ES2022`、`moduleResolution: bundler`。
- [x] `web/postcss.config.mjs` 使用 `@tailwindcss/postcss` 插件。
- [x] `web/app/layout.tsx` 通过 `next/font/google` 加载 Inter + JetBrains Mono 并挂到 `<html>`。
- [x] `web/app/layout.tsx` 导出 `metadata`（title、description、openGraph）。
- [x] `web/lib/api.ts` 导出全部 API 函数（`getConfig`、`patchConfig`、`createSession`、`listMemories`、`getIndex`、`rebuildIndex`、`createQuery`）与 TypeScript 类型。
- [x] `web/lib/api.ts` 错误处理解析后端 `{error:{code,message}}` 抛 `ApiError`（带 `code`、`message`、`status`）。
- [x] `web/lib/constants.ts` 导出 `NODE_LABELS`、`MEM_KIND`、`SAMPLES`、`DEMOS`、`CHAT_MODEL_PRESETS`，与原 `streamlit_app.py` 字典一致。
- [x] `web/package.json` dev/build 用 `--webpack` 标志（规避 Next.js 16.2.12 Turbopack 与 `next/font/google` 的已知兼容问题）。
- [x] `web/package.json` lint 用 `eslint .`（Next.js 16 移除了 `next lint` 子命令）。
- [x] `web/eslint.config.mjs` 用 ESLint 9 flat config（`@next/eslint-plugin-next` + `eslint-plugin-react-hooks` + `typescript-eslint` parser）。

## 视觉系统
- [x] `web/app/globals.css` 的 `:root` 含原 Streamlit 全部 CSS 变量（`--bg`/`--bg2`/`--surface`/`--surface-2`/`--stroke`/`--stroke-2`/`--ink`/`--muted`/`--faint`/`--brand`/`--brand2`/`--accent`/`--ok`/`--warn`/`--bad`/`--r-s`/`--r-m`/`--r-l`/`--grad`）。
- [x] Tailwind v4 `@theme inline` 把上述变量映射为 `bg-bg`/`bg-surface`/`text-ink`/`text-muted`/`border-stroke`/`bg-grad` 等 token，可在 className 中直接使用。
- [x] `body` 背景含双径向光晕 + 网格 mask，与原 Streamlit `.stApp` 视觉一致。
- [x] 字体生效（Inter 主字体、JetBrains Mono 等宽）。

## 原子组件
- [x] `Card`、`Eyebrow`、`Pill`、`Gauge`、`Spinner`、`Expander`、`Toast` 全部存在并被业务组件复用。
- [x] `Gauge` 接受 `pct` 与 `color` props，渲染 conic-gradient 环形仪表 + 中心百分比数字。

## 业务面板
- [x] `Sidebar`：运行状态卡、2×2 KPI 网格（含重建索引按钮）、记忆身份区（user_id 输入 + 会话截断 id + 新会话按钮）、示例问题列表、架构 expander 全部存在。
- [x] `Hero`：标题渐变文本、副标题、5 个 chips、右上 conic-gradient 18s 旋转光晕。
- [x] `AskBar`：chat 模型 select（5 预设 + 自定义）、5 个示例 chip、输入框、运行按钮；Enter 触发；`use_llm=false` 时 select 禁用并显示提示；模型切换调 `patchConfig({chat_model})`；示例 chip 点击填入并立即触发。
- [x] `KpiRow`：4 列 KPI（Faithfulness/反思轮数/命中证据/评判方式），底部 3px 渐变条。
- [x] `ChatHistory`：running_summary 顶部条 + 用户/助手气泡左右对齐 + 底部统计行（轮数 + 会话 id）。
- [x] `AnswerCard`：环形仪表 + 可信/不足标签 + 答案文本。
- [x] `CredibilityDerivation`：4 步推导（评判方式/依据/计算/阈值判定）+ 标尺（0.0–1.0 渐变 + 0.6 阈值刻度 + 当前分值圆点）。
- [x] `Citations`、`ToolCalls`、`MemoryPanel`、`EvidenceList` 全部按原 Streamlit 视觉实现。
- [x] `ExecutionTrace`：左侧渐变竖线 + 节点圆点 + NODE_LABELS 映射标题 + 节点类型对应的描述文案。
- [x] `MemoryEvolution`：调用 `listMemories(userId)`，现行记忆卡 + 被取代旧值 strikethrough 链 + 底部统计；`refreshKey` 变化时重新拉取。
- [x] `RawState`：Expander 内 `<pre>` 展示原始 state JSON。

## 主页面组装
- [x] `web/app/page.tsx` 用 `useState` 管理 config/userId/sessionId/queryResponse/loading/error/query/memoryRefreshKey。
- [x] mount 时并行调用 `getConfig()` 与 `createSession()`。
- [x] 布局为左 Sidebar（sticky）+ 右主区（Hero + AskBar + 结果区两列 1.4/1）。
- [x] 空态显示虚线占位卡（"输入问题，开始一次 Agent 编排"）。
- [x] 错误态显示 `运行出错（多为模型接口超时/报错）：{error.code}: {error.message}　可在上方换一个更稳的模型重试。`
- [x] chat 完成后递增 `memoryRefreshKey` 触发 MemoryEvolution 刷新。

## 部署与文档
- [x] `.gitignore` 含 `web/.next/`、`web/node_modules/`、`web/.env*.local`。
- [x] `web/.env.example` 含 `API_BASE_URL=http://localhost:8000/api`（server-side rewrite 用，无 `NEXT_PUBLIC_` 前缀）。
- [x] `Dockerfile` 多阶段构建（前端 standalone 输出）或拆为 `web/Dockerfile`。
- [x] `docker-compose.yml` 新增 `web` 服务（port 3000，env `API_BASE_URL=http://api:8000/api`、`HOSTNAME=0.0.0.0`、`PORT=3000`，depends_on api）。
- [x] `README.md` 新增"前端"段说明启动命令；目录树含 `web/` 与 `app/api/routes/`；里程碑加"前端 Next.js 化 + API RESTful 化"。

## 端到端验证
- [x] curl 验证 `GET /api/config`、`POST /api/sessions`（201）、`GET /api/users/alice/memories`、`GET /api/index`、`POST /api/index/rebuilds`（201）、`POST /api/queries`（201，含 `working_memory`）、`PATCH /api/config`（200/offline 模式下 400）全部返回正确结构与 status code。
- [x] curl 触发 404/422 路径，验证响应体为 `{"error":{"code","message"}}`。404 已修复（覆盖 `StarletteHTTPException`）。
- [x] 浏览器 `http://localhost:3000/`：空态 → 点示例 chip → 自动运行 → 答案卡 + 引用渲染（KPI/仪表/时间线等组件代码结构正确，与 AnswerCard 同分支渲染；浏览器快照受视口限制未全部截到，但代码验证无误）。
- [x] 切换 chat 模型 → select 在离线模式下禁用并显示提示文案。
- [x] 点"新会话" → 主区清空 + sessionId 更新。
- [x] 点"重建索引" → toast + KB chunks 数字更新。
- [x] `cd web && npm run build` 通过（webpack 模式，TypeScript 检查通过，2 路由静态生成）；`npm run lint` 无 error（0 error 0 warning）。
