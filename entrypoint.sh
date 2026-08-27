#!/bin/sh
# 单容器启动入口：先启动后端 Uvicorn（127.0.0.1:8000），再以前台方式启动 Nginx。
# 数据库迁移由 compose 的 migrate 服务执行，不在本入口执行。
set -e

UVICORN_WORKERS="${UVICORN_WORKERS:-2}"

echo "[entrypoint] starting uvicorn on 127.0.0.1:8000 (workers=${UVICORN_WORKERS})"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers "${UVICORN_WORKERS}" &

# 等待后端就绪（最多 30 秒），避免 Nginx 提前启动导致 502
i=0
until python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=1)" 2>/dev/null || [ "$i" -ge 30 ]; do
  i=$((i + 1))
  sleep 1
done

echo "[entrypoint] starting nginx"
exec nginx -g 'daemon off;'
