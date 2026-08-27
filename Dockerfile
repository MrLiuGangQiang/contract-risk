# 一体化镜像：Vue3 前端（Nginx）+ FastAPI 后端（Uvicorn），单镜像部署（《09》第 8 节）
# 构建：docker build -t <registry>/contract-risk:<tag> .
# 说明：Nginx 托管前端静态资源，并将 /api 反向代理到同容器内 127.0.0.1:8000 的 Uvicorn。

# ---------- 阶段一：构建前端静态资源 ----------
FROM node:22-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- 阶段二：运行时（Python 后端 + Nginx） ----------
FROM python:3.12-slim

# 安装 Nginx（Debian 官方包），托管前端并反向代理 /api
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=prod

WORKDIR /app

# 安装后端锁定依赖（requirements.lock.txt 为 pip freeze 全量锁定）
COPY backend/requirements.lock.txt backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

# 复制后端代码与迁移脚本
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./

# 复制前端构建产物、Nginx 配置与启动入口
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 80

# 数据库迁移由 compose 的 migrate 服务单独执行；容器启动 = Uvicorn + Nginx
CMD ["/usr/local/bin/entrypoint.sh"]
