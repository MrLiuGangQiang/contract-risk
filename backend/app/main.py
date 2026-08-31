"""FastAPI 应用入口：中间件、全局异常处理、路由挂载、启动引导（《02-总体架构设计》第 4 节）。"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.admin.router import router as admin_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.contracts import router as contracts_router
from app.api.v1.health import router as health_router
from app.api.v1.risk_rules import router as risk_rules_router
from app.core.config import get_settings
from app.core.database import SessionFactory
from app.core.exceptions import BizException
from app.core.logging import request_id_middleware, setup_logging
from app.core.response import ApiResponse
from app.integrations import redis_client
from app.services.bootstrap import bootstrap
from app.services.contract_scan_job_service import ContractScanJobService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化日志并执行幂等引导（种子数据/初始超管）。"""
    settings = get_settings()
    setup_logging(settings.debug)
    async with SessionFactory() as session:
        await bootstrap(session)
    # 恢复应用重启前中断的后台扫描任务
    await ContractScanJobService().resume_orphaned()
    yield
    await redis_client.close_redis()


def create_app() -> FastAPI:
    """构建 FastAPI 应用（工厂函数，便于测试）。"""
    settings = get_settings()
    app = FastAPI(
        title="合同风险扫描系统 API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.debug else None,
    )

    # CORS：白名单 + 允许携带 Cookie（refresh token）
    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )
    app.middleware("http")(request_id_middleware)

    # ==================== 全局异常处理 ====================
    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException) -> JSONResponse:
        """业务异常 → 统一响应包裹（保留业务错误码）。"""
        return JSONResponse(
            status_code=exc.http_status,
            content=ApiResponse.error(request, exc.code, exc.message, data=exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """参数校验失败 → code 20000。"""
        return JSONResponse(
            status_code=422,
            content=ApiResponse.error(
                request,
                20000,
                "参数校验失败",
                data={"errors": jsonable_encoder(exc.errors())},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """框架级 HTTP 异常（404/405 等）→ 统一响应包裹。"""
        code = 10001 if exc.status_code == 404 else 10000
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse.error(request, code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """未预期异常：记录 ERROR 日志，对外只返回模糊信息（《06-安全设计》）。"""
        logger.error("unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=ApiResponse.error(request, 50000, "系统内部错误"),
        )

    # ==================== 路由 ====================
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(risk_rules_router, prefix="/api/v1")
    app.include_router(contracts_router, prefix="/api/v1")
    return app


app = create_app()