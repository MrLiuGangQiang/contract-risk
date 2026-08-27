"""统一响应包裹（《05-API设计规范》第 1.1 节）。

所有接口返回：{code, message, data, request_id, timestamp}
"""
import time
from typing import Any

from fastapi import Request


class ApiResponse:
    """统一响应构建器（无 pydantic 泛型，保持简单可靠）。"""

    @staticmethod
    def ok(request: Request, data: Any = None, message: str = "ok") -> dict[str, Any]:
        """构造成功响应。"""
        return {
            "code": 0,
            "message": message,
            "data": data,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": int(time.time() * 1000),
        }

    @staticmethod
    def error(
        request: Request,
        code: int,
        message: str,
        *,
        data: Any = None,
        http_status: int = 400,
    ) -> dict[str, Any]:
        """构造失败响应（供异常处理器使用）。"""
        return {
            "code": code,
            "message": message,
            "data": data,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": int(time.time() * 1000),
        }