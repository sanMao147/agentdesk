# AgentDesk Next.js 前端镜像（生产 standalone 模式）
FROM node:20-alpine AS builder

WORKDIR /app

# 先拷依赖清单利用层缓存
COPY package.json package-lock.json* ./
RUN npm ci

# 拷源码并构建（output: 'standalone' 会输出到 .next/standalone）
COPY . .
# 确保 public 目录存在（项目可能未提供该目录）
RUN mkdir -p public

# Next.js rewrites 在 build 阶段把 process.env.API_BASE_URL 内联为字面量，
# 运行时注入的环境变量不会生效，因此需要在构建时设置默认值。
# docker-compose 运行时可覆盖以适配不同部署目标。
ARG API_BASE_URL=http://api:8000
ENV API_BASE_URL=${API_BASE_URL}
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
