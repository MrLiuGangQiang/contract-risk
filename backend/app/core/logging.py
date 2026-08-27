"""结构化日志（JSON）与 request_id 全链路（《07-工程规范》第 7 节）。

- 输出 JSON 行：time/level/logger/message/request_id/user_id/path/duration_ms/extra
- 敏感字段（password/token/secret）在日志中统一脱敏。
"""
import json
import logging
import sys
import time
from typing import Any

from fastapi import Request

SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "cookie", "app_secret", "client_secret"}


def _mask(value: Any, key: str = "") -> Any:
    """对敏感键值做掩码处理（仅首尾保留，中间打码）。"""
    if not isinstance(value, str):
        return value
    if key.lower() in SENSITIVE_KEYS:
        if len(value) <= 8:
            return "***"
        return f"{value[:2]}***{value[-2:]}"
    return value


class JsonFormatter(logging.Formatter):
    """将日志记录格式化为单行 JSON。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "user_id", "path", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload["extra"] = {k: _mask(v, k) for k, v in extra.items()}
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(debug: bool) -> None:
    """初始化根日志配置：JSON 输出到 stdout；debug 开启时级别为 DEBUG。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    # 降低第三方库噪音
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def request_id_middleware(request: Request, call_next: Any) -> Any:
    """为每个请求生成 request_id（兼容外部传入的 X-Request-Id）。"""
    import uuid

    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    request.state.request_id = request_id
    request.state.start_time = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response