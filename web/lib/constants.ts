// UI constants mirrored from streamlit_app.py to keep label/i18n parity.

export const NODE_LABELS: Record<string, [string, string]> = {
  memory_retrieve: ["Memory · Retrieve", "加载短期上下文 + 召回长期记忆"],
  planner: ["Planner", "查询改写 · multi-query"],
  retrieval: ["Retrieval", "向量 + BM25 → RRF → Rerank"],
  tool: ["Tool", "MCP 工具路由"],
  writer: ["Writer", "带证据生成 · 标注引用"],
  critic: ["Critic", "faithfulness 反思判定"],
  memory_write: ["Memory · Write", "抽取演化写入 + 追加短期记忆"],
  summarize: ["Memory · Summarize", "滚动摘要压缩旧轮次"],
};

export const MEM_KIND: Record<string, [string, string, string]> = {
  preference: ["⭐", "偏好", "#10b981"],
  fact: ["📌", "事实", "#3aa6ff"],
  event: ["🕒", "事件", "#f59e0b"],
};

export const SAMPLES: string[] = [
  "公司A和公司B 2025年营收分别是多少？",
  "知识库里有多少个文档？",
  "(210-205)/205*100",
  "AC-104 这个需求计划讲了什么？",
  "公司的报销政策是怎样的？",
];

export const DEMOS: [string, string][] = [
  ["📊 多公司营收", "公司A和公司B 2025年营收分别是多少？"],
  ["🔢 计算器工具", "(210-205)/205*100"],
  ["🗂️ 知识库统计", "知识库里有多少个文档？"],
  ["📄 套餐 SLA", "AC-110 套餐的 SLA 可用性是多少？"],
  ["📑 报销政策", "公司的报销政策是怎样的？"],
];

export const CHAT_MODEL_PRESETS: string[] = [
  "Qwen/Qwen2.5-7B-Instruct",
  "Qwen/Qwen2.5-14B-Instruct",
  "Qwen/Qwen2.5-32B-Instruct",
  "Qwen/Qwen2.5-72B-Instruct",
  "deepseek-ai/DeepSeek-V3",
  "自定义…",
];
