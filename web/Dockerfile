# AgentDesk Next.js 前端镜像（生产 standalone 模式）
FROM node:20-alpine AS builder

WORKDIR /app

# 先拷依赖清单利用层缓存
COPY package.json package-lock.json* ./
RUN npm ci

# 拷源码并构建（output: 'standalone' 会输出到 .next/standalone）
COPY . .
RUN npm run build

# ---- 运行阶段 ----
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

# 拷贝 standalone 产物 + 静态资源 + public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
