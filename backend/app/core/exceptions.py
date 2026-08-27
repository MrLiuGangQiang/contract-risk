"""统一异常体系：业务异常与系统异常分离。

- BizException：可预期业务异常，携带错误码，由全局处理器转换为统一响应。
- 系统异常：不直接抛出到前端，由全局处理器记录日志并返回模糊信息。
遵循《07-工程规范与代码规范》第 3.4 节。
"""
from typing import Any


class AppError(Exception):
    """应用异常基类。"""

    def __init__(
        self,
        code: int,
        message: str,
        *,
        data: Any = None,
        http_status: int = 400,
    ) -> None:
        self.code = code
        self.message = message
        self.data = data
        self.http_status = http_status
        super().__init__(message)


class BizException(AppError):
    """可预期业务异常（对应统一错误码，如 30010 账密错误）。"""