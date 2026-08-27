"""合同扫描后台任务服务（《11》第 5/7 节）。

上传/重扫先返回 job_id，后台异步执行并在 Redis 内更新进度：
读取文件 → 提取文本 → 规则匹配 → AI 分析 → 生成结果。
前端轮询 /contracts/jobs/{id} 展示进度。
"""
import asyncio
import logging
import uuid
from typing import Any

from app.core.database import SessionFactory
from app.core.exceptions import BizException
from app.domain.constants import CONTRACT_ALLOWED_EXTENSIONS, CONTRACT_MAX_SIZE
from app.integrations import job_store
from app.services.contract_risk_service import ContractRiskService

logger = logging.getLogger(__name__)

# 防止后台任务被 GC（持有引用）
_TASKS: set[asyncio.Task] = set()


class ContractScanJobService:
    """合同扫描任务管理（无状态服务）。"""

    async def start_upload(
        self, *, user_id: int, file_name: str, content: bytes
    ) -> str:
        """校验后创建异步上传扫描任务，立即返回 job_id。"""
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if ext not in CONTRACT_ALLOWED_EXTENSIONS:
            raise BizException(20002, "仅支持 txt/pdf/docx 文件")
        if not content:
            raise BizException(20002, "文件内容为空")
        if len(content) > CONTRACT_MAX_SIZE:
            raise BizException(20002, "文件不能超过 20MB")

        job_id = uuid.uuid4().hex
        await job_store.create_job(
            job_id, {"user_id": user_id, "stage_message": "任务已创建", "progress": 0}
        )
        self._spawn(self._run_upload(job_id, user_id, file_name, content))
        return job_id

    async def start_rescan(self, *, user_id: int, contract_id: int) -> str:
        """创建重新扫描任务，立即返回 job_id。"""
        job_id = uuid.uuid4().hex
        await job_store.create_job(
            job_id, {"user_id": user_id, "contract_id": contract_id, "stage_message": "任务已创建", "progress": 0}
        )
        self._spawn(self._run_rescan(job_id, user_id, contract_id))
        return job_id

    async def get_status(self, job_id: str) -> dict[str, Any]:
        """读取任务状态（不存在返回 404 语义）。"""
        data = await job_store.get_job(job_id)
        if data is None:
            raise BizException(10001, "Not Found", http_status=404)
        return data

    # ==================== 私有 ====================

    def _spawn(self, coro: Any) -> None:
        """启动后台任务并防 GC。"""
        task = asyncio.create_task(coro)
        _TASKS.add(task)
        task.add_done_callback(_TASKS.discard)

    async def _run_upload(self, job_id: str, user_id: int, file_name: str, content: bytes) -> None:
        """后台执行上传扫描。"""
        async with SessionFactory() as session:
            svc = ContractRiskService(session)

            last_stage = {"value": ""}

            async def progress(percent: int, stage: str) -> None:
                await job_store.update_job(
                    job_id, progress=percent, stage=stage, stage_message=stage
                )
                if stage != last_stage["value"]:
                    await job_store.append_event(job_id, stage)
                    last_stage["value"] = stage

            try:
                await job_store.append_event(job_id, "任务已创建")
                await job_store.append_event(job_id, f"正在上传文件：{file_name}")
                await job_store.update_job(job_id, progress=10, stage="reading", stage_message="正在读取合同文件")
                result = await svc.upload(
                    user_id=user_id,
                    file_name=file_name,
                    content=content,
                    request_meta={"ip": "job", "user_agent": "background", "duration_ms": 0, "trace_id": job_id},
                    progress_cb=progress,
                )
                await job_store.update_job(
                    job_id,
                    status="done",
                    progress=100,
                    stage="done",
                    stage_message="扫描完成",
                    contract_id=result.contract.id,
                    risk_count=result.contract.risk_count,
                )
                await job_store.append_event(job_id, f"扫描完成：共 {result.contract.risk_count} 项风险")
                logger.info("contract scan job done", extra={"job_id": job_id, "contract_id": result.contract.id})
            except Exception as exc:
                await job_store.update_job(job_id, status="failed", stage="failed", stage_message=str(exc))
                await job_store.append_event(job_id, f"扫描失败：{exc}", level="error")
                logger.warning("contract scan job failed", extra={"job_id": job_id, "error": str(exc)})

    async def _run_rescan(self, job_id: str, user_id: int, contract_id: int) -> None:
        """后台执行重新扫描。"""
        async with SessionFactory() as session:
            svc = ContractRiskService(session)

            last_stage = {"value": ""}

            async def progress(percent: int, stage: str) -> None:
                await job_store.update_job(
                    job_id, progress=percent, stage=stage, stage_message=stage
                )
                if stage != last_stage["value"]:
                    await job_store.append_event(job_id, stage)
                    last_stage["value"] = stage

            try:
                await job_store.append_event(job_id, "开始重新扫描")
                result = await svc.rescan(
                    user_id=user_id,
                    contract_id=contract_id,
                    request_meta={"ip": "job", "user_agent": "background", "duration_ms": 0, "trace_id": job_id},
                    progress_cb=progress,
                )
                await job_store.update_job(
                    job_id,
                    status="done",
                    progress=100,
                    stage="done",
                    stage_message="扫描完成",
                    contract_id=result.contract.id,
                    risk_count=result.contract.risk_count,
                )
                await job_store.append_event(job_id, f"重新扫描完成：共 {result.contract.risk_count} 项风险")
                logger.info("contract rescan job done", extra={"job_id": job_id, "contract_id": result.contract.id})
            except Exception as exc:
                await job_store.update_job(job_id, status="failed", stage="failed", stage_message=str(exc))
                await job_store.append_event(job_id, f"扫描失败：{exc}", level="error")
                logger.warning("contract rescan job failed", extra={"job_id": job_id, "error": str(exc)})