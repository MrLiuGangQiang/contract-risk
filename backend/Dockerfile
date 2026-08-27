# 后端镜像：FastAPI + Alembic（《09》第 8 节 / docs/ops/部署指南.md）
# 构建：docker build -f backend/Dockerfile -t <registry>/contract-risk:backend-<tag> backend
FROM python:3.12-slim

# 运行参数：不写字节码、日志不缓冲、pip 不缓存
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=prod

WORKDIR /app

# 先安装锁定依赖（利用 Docker 层缓存；requirements.lock.txt 为 pip freeze 全量锁定）
COPY requirements.lock.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

# 复制应用代码（.dockerignore 已排除 .env/.venv/__pycache__/tests 等）
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

# 非 root 运行（安全基线，uid 10001）
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 数据库迁移由 compose 的 migrate 服务单独执行；容器只负责启动 API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
