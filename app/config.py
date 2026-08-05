"""全局配置模块。

设计目标：**最大兼容性 + 最小依赖**。

配置加载策略：
1. 优先使用 pydantic-settings（类型安全、支持 .env 文件）
2. 若未安装 pydantic-settings，自动退化为环境变量 + .env 文件解析

所有配置项均可通过环境变量或 .env 文件覆盖，
无需修改代码即可适应不同部署环境。

配置项分类：
- LLM 配置：API Key、模型名、Base URL
- RAG 配置：向量后端、Top-K、分块参数
- 记忆配置：短期记忆窗口、长期记忆召回参数
- 工具配置：MCP 开关
- 服务配置：CORS 源、Trace 日志
"""
from __future__ import annotations

import os


def _load_env_file(path: str = ".env") -> None:
    """手动解析 .env 文件。

    当 pydantic-settings 不可用时，此函数提供基本的 .env 文件解析能力。
    逐行读取，跳过注释和空行，解析 KEY=VALUE 格式。

    Args:
        path: .env 文件路径
    """
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


# ── 尝试加载 pydantic-settings ──
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        """应用全局配置（pydantic-settings 版本）。

        支持从 .env 文件和环境变量自动加载配置。
        字段名即环境变量名（不区分大小写）。
        """
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

        # ── LLM 配置 ──
        openai_api_key: str = ""                    # API Key，为空时系统进入离线模式
        openai_base_url: str = "https://api.openai.com/v1"  # API Base URL
        chat_model: str = "gpt-4o-mini"             # 对话模型
        embedding_model: str = "text-embedding-3-small"  # Embedding 模型

        # ── RAG 配置 ──
        top_k: int = 5                              # 最终返回的证据数量
        chunk_size: int = 512                       # 文档分块大小（字符）
        chunk_overlap: int = 64                     # 分块重叠大小（防止语义断裂）
        max_iterations: int = 3                     # Agent 最大迭代次数（防死循环）

        # ── 工具配置 ──
        use_mcp: bool = False                       # 是否启用 MCP 协议调用工具

        # ── 向量存储配置 ──
        vector_backend: str = "memory"              # 向量后端：memory / qdrant
        qdrant_url: str = "http://localhost:6333"   # Qdrant 服务地址
        qdrant_collection: str = "agentdesk"          # Qdrant 集合名

        # ── 缓存配置 ──
        redis_url: str = ""                         # Redis 地址（为空则用内存缓存）

        # ── 记忆系统配置 ──
        mem_enabled: bool = True                    # 是否启用记忆系统
        mem_collection: str = "agentdesk_memory"     # 长期记忆集合名
        mem_short_window_k: int = 2                 # 短期记忆窗口（保留最近 k 轮对话）
        mem_summarize_every_n: int = 3              # 每 n 轮对话生成一次摘要
        mem_long_top_k: int = 3                     # 长期记忆召回数量
        mem_dedup_threshold: float = 0.92           # 去重阈值（相似度 >= 此值视为重复）
        mem_conflict_threshold: float = 0.80        # 冲突阈值（相似度 >= 此值视为冲突）
        mem_event_ttl_days: int = 30                # 事件类型记忆 TTL（天）
        mem_max_per_user: int = 500                 # 每用户最大记忆条数（LRU 淘汰）

        # ── 服务配置 ──
        trace_log: bool = True                      # 是否记录 Trace 日志
        cors_origins: str = "http://localhost:3000"  # CORS 允许的源

        @property
        def use_llm(self) -> bool:
            """判断是否使用真实 LLM。

            规则：openai_api_key 非空即视为在线模式。
            空字符串或全空格 → 离线模式（使用哈希向量 + 模板拼接）。
            """
            return bool(self.openai_api_key.strip())

        def set_chat_model(self, name: str) -> None:
            """切换 chat 模型。

            同步更新实例属性和环境变量，确保 llm.py 下次调用时读取到新值。
            这使得前端可以动态切换模型而无需重启服务。

            Args:
                name: 模型名称
            """
            self.chat_model = name
            os.environ["CHAT_MODEL"] = name

        @property
        def index_signature(self) -> dict:
            """索引指纹。

            用于判断现有向量索引是否仍然有效。
            当 use_llm 切换（哈希 ↔ 真实 embedding）或模型名变更时，
            指纹变化 → 触发索引重建。

            Returns:
                {"use_llm": bool, "model": str}
            """
            return {
                "use_llm": bool(self.use_llm),
                "model": self.embedding_model if self.use_llm else "offline-hash",
            }

    settings = Settings()

except ImportError:
    # ── 回退：纯环境变量解析 ──
    _load_env_file()

    class _FallbackSettings:
        """回退配置类（不依赖 pydantic-settings）。

        直接从环境变量读取，提供类型转换和默认值。
        接口与 Settings 保持一致，上层代码无需修改。
        """

        # ── LLM 配置 ──
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        openai_base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        chat_model = os.environ.get("CHAT_MODEL", "gpt-4o-mini")
        embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

        # ── RAG 配置 ──
        top_k = int(os.environ.get("TOP_K", "5"))
        chunk_size = int(os.environ.get("CHUNK_SIZE", "512"))
        chunk_overlap = int(os.environ.get("CHUNK_OVERLAP", "64"))
        max_iterations = int(os.environ.get("MAX_ITERATIONS", "3"))

        # ── 工具配置 ──
        use_mcp = os.environ.get("USE_MCP", "").strip() in ("1", "true", "True")

        # ── 向量存储配置 ──
        vector_backend = os.environ.get("VECTOR_BACKEND", "memory")
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        qdrant_collection = os.environ.get("QDRANT_COLLECTION", "agentdesk")

        # ── 缓存配置 ──
        redis_url = os.environ.get("REDIS_URL", "")

        # ── 记忆系统配置 ──
        mem_enabled = os.environ.get("MEM_ENABLED", "1").strip() not in ("0", "false", "False")
        mem_collection = os.environ.get("MEM_COLLECTION", "agentdesk_memory")
        mem_short_window_k = int(os.environ.get("MEM_SHORT_WINDOW_K", "2"))
        mem_summarize_every_n = int(os.environ.get("MEM_SUMMARIZE_EVERY_N", "3"))
        mem_long_top_k = int(os.environ.get("MEM_LONG_TOP_K", "3"))
        mem_dedup_threshold = float(os.environ.get("MEM_DEDUP_THRESHOLD", "0.92"))
        mem_conflict_threshold = float(os.environ.get("MEM_CONFLICT_THRESHOLD", "0.80"))
        mem_event_ttl_days = int(os.environ.get("MEM_EVENT_TTL_DAYS", "30"))
        mem_max_per_user = int(os.environ.get("MEM_MAX_PER_USER", "500"))

        # ── 服务配置 ──
        trace_log = os.environ.get("TRACE_LOG", "1").strip() not in ("0", "false", "False")
        cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")

        @property
        def use_llm(self) -> bool:
            """判断是否使用真实 LLM（回退版本）。"""
            return bool(self.openai_api_key.strip())

        def set_chat_model(self, name: str) -> None:
            """切换 chat 模型（回退版本）。"""
            self.chat_model = name
            os.environ["CHAT_MODEL"] = name

        @property
        def index_signature(self) -> dict:
            """索引指纹（回退版本）。"""
            return {
                "use_llm": bool(self.use_llm),
                "model": self.embedding_model if self.use_llm else "offline-hash",
            }

    settings = _FallbackSettings()
