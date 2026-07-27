# AgentDesk FastAPI 后端镜像（/api/* RESTful API）
FROM python:3.11-slim

# 系统依赖（uvicorn standard 需要的编译/网络栈最小集合）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用 Docker 层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝后端源码（不拷 web/、docs/、.git 等）
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY eval/ ./eval/
COPY data/ ./data/

EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
