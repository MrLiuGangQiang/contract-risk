"""合同扫描后台任务服务（《11》第 5/7 节）。

后台扫描模式：
- 上传：校验 + 文本解析 + 合同以「扫描中」状态入库（立即可见），随后返回 job_id；
- 扫描（规则匹配 + AI 分析）在后台任务中执行，进度写入 Redis，前端轮询或从列表查看；
- 关闭进度弹窗 / 刷新页面不影响扫描继续；
- 应用重启后自动恢复「扫描中」的孤儿任务（重新启动扫描）。
"""
import asyncio
import logging
import uuid
from typing import Any

from app.core.database import SessionFactory
from app.core.exceptions import BizException
from app.domain.constants import (
    CONTRACT_ALLOWED_EXTENSIONS,
    CONTRACT_MAX_SIZE,
    CONTRACT_STATUS_SCANNING,
    RISK_CATEGORY_LABELS,
)
from app.integrations import job_store
from app.services.contract_risk_service import ContractRiskService

logger = logging.getLogger(__name__)

# 防止后台任务被 GC（持有引用）
_TASKS: set[asyncio.Task] = set()

# 任务状态读改写锁：Redis 读-改-写非原子，并发回调（维度任务/进度/AI）需串行化，防止相互覆盖
_JOB_LOCK = asyncio.Lock()


class ContractScanJobService:
    """合同扫描任务管理（无状态服务）。"""

    async def start_upload(
        self, *, user_id: int, file_name: str, content: bytes
    ) -> tuple[str, int]:
        """校验并登记合同（同步），然后启动后台扫描任务。

        返回 (job_id, contract_id)：合同立即出现在列表中（扫描中）。
        """
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if ext not in CONTRACT_ALLOWED_EXTENSIONS:
            raise BizException(20002, "仅支持 txt/pdf/docx 文件")
        if not content:
            raise BizException(20002, "文件内容为空")
        if len(content) > CONTRACT_MAX_SIZE:
            raise BizException(20002, "文件不能超过 20MB")

        # 合同登记入库（扫描中），扫描失败不影响合同存在
        async with SessionFactory() as session:
            contract = await ContractRiskService(session).register_upload(
                user_id=user_id,
                file_name=file_name,
                content=content,
                request_meta={"ip": "upload", "user_agent": "upload", "duration_ms": 0, "trace_id": ""},
            )

        job_id = uuid.uuid4().hex
        await job_store.create_job(
            job_id,
            {
                "user_id": user_id,
                "contract_id": contract.id,
                "file_name": file_name,
                "stage_message": "任务已创建",
                "progress": 0,
            },
        )
        await job_store.append_event(job_id, "任务已创建")
        await job_store.append_event(job_id, f"文件已上传：{file_name}（{contract.total_chars} 字符）")
        await job_store.append_event(job_id, "已加入后台扫描队列")
        await job_store.link_contract(job_id, contract.id)
        self._spawn(self._run_scan(job_id, user_id, contract.id, label="上传扫描"))
        return job_id, contract.id

    async def start_rescan(self, *, user_id: int, contract_id: int) -> str:
        """登记重新扫描并启动后台任务，立即返回 job_id。"""
        async with SessionFactory() as session:
            await ContractRiskService(session).register_rescan(
                user_id=user_id,
                contract_id=contract_id,
                request_meta={"ip": "rescan", "user_agent": "rescan", "duration_ms": 0, "trace_id": ""},
            )

        job_id = uuid.uuid4().hex
        await job_store.create_job(
            job_id,
            {"user_id": user_id, "contract_id": contract_id, "stage_message": "任务已创建", "progress": 0},
        )
        await job_store.append_event(job_id, "开始重新扫描（使用最新生效规则）")
        await job_store.link_contract(job_id, contract_id)
        self._spawn(self._run_scan(job_id, user_id, contract_id, label="重新扫描"))
        return job_id

    async def get_status(self, job_id: str) -> dict[str, Any]:
        """读取任务状态（不存在返回 404 语义）。"""
        data = await job_store.get_job(job_id)
        if data is None:
            raise BizException(10001, "Not Found", http_status=404)
        return data

    async def get_status_by_contract(self, contract_id: int) -> dict[str, Any]:
        """按合同读取关联任务状态（不存在返回 404 语义）。"""
        job_id = await job_store.get_job_id_by_contract(contract_id)
        if job_id is None:
            raise BizException(10001, "Not Found", http_status=404)
        data = await job_store.get_job(job_id)
        if data is None:
            raise BizException(10001, "Not Found", http_status=404)
        return data

    async def resume_orphaned(self) -> int:
        """应用启动时恢复「扫描中」的孤儿合同（重启前的后台任务已丢失）。"""
        from sqlalchemy import select

        from app.models.contract import Contract

        async with SessionFactory() as session:
            result = await session.execute(
                select(Contract.id, Contract.user_id, Contract.file_name).where(
                    Contract.status == CONTRACT_STATUS_SCANNING,
                    Contract.deleted_at.is_(None),
                )
            )
            orphans = result.all()
        for contract_id, user_id, file_name in orphans:
            job_id = uuid.uuid4().hex
            await job_store.create_job(
                job_id,
                {
                    "user_id": user_id,
                    "contract_id": contract_id,
                    "file_name": file_name,
                    "stage_message": "服务重启，恢复扫描",
                    "progress": 0,
                },
            )
            await job_store.append_event(job_id, f"服务重启，恢复后台扫描：{file_name}")
            await job_store.link_contract(job_id, contract_id)
            self._spawn(self._run_scan(job_id, user_id, contract_id, label="恢复扫描"))
        if orphans:
            logger.info("resumed orphaned contract scans: %d", len(orphans))
        return len(orphans)

    # ==================== 私有 ====================

    def _spawn(self, coro: Any) -> None:
        """启动后台任务并防 GC。"""
        task = asyncio.create_task(coro)
        _TASKS.add(task)
        task.add_done_callback(_TASKS.discard)

    async def _run_scan(self, job_id: str, user_id: int, contract_id: int, *, label: str) -> None:
        """后台执行扫描：四维度并发 + AI 流式，状态实时写入 Redis。"""
        async with SessionFactory() as session:
            svc = ContractRiskService(session)

            last_stage = {"value": ""}

            async def progress(percent: int, stage: str) -> None:
                async with _JOB_LOCK:
                    await job_store.update_job(
                        job_id, progress=percent, stage=stage, stage_message=stage
                    )
                if stage != last_stage["value"]:
                    await job_store.append_event(job_id, stage)
                    last_stage["value"] = stage

            async def init_tasks(counts: dict[str, int]) -> None:
                """初始化维度并发任务清单（维度开放格式，前端任务卡片渲染）。"""
                tasks = {
                    category: {
                        "label": RISK_CATEGORY_LABELS.get(category, category),
                        "status": "pending",
                        "rule_count": rule_count,
                        "hits": 0,
                    }
                    for category, rule_count in counts.items()
                }
                await job_store.update_job(job_id, tasks=tasks)
                await job_store.append_event(
                    job_id,
                    "已创建 " + "、".join(
                        f"{RISK_CATEGORY_LABELS.get(c, c)}({n})" for c, n in counts.items() if n
                    ) + " 并发任务",
                )

            async def task_update(category: str, status: str, hits: int) -> None:
                """更新单个维度任务状态（锁内读改写，防止并发覆盖）。"""
                async with _JOB_LOCK:
                    raw = await job_store.get_job(job_id)
                    if raw is None:
                        return
                    tasks = raw.get("tasks") or {}
                    if category not in tasks:
                        tasks[category] = {
                            "label": RISK_CATEGORY_LABELS.get(category, category),
                            "rule_count": 0,
                        }
                    tasks[category].update({"status": status, "hits": hits})
                    await job_store.update_job(job_id, tasks=tasks)
                if status == "done":
                    await job_store.append_event(
                        job_id,
                        f"{RISK_CATEGORY_LABELS.get(category, category)}扫描完成：命中 {hits} 项",
                    )

            async def ai_status(status: str, findings: int) -> None:
                """更新 AI 分析状态（running 在流开始时已由首个 chunk 隐含）。"""
                messages = {
                    "running": "AI 已开始逐条理解规则并并发校验合同",
                    "skipped": "AI 未启用/未配置，使用关键词规则匹配",
                    "done": f"AI 逐条校验完成：命中 {findings} 项风险",
                    "failed": "AI 逐条校验失败，已自动降级为关键词匹配",
                }
                async with _JOB_LOCK:
                    await job_store.update_job(job_id, ai={"status": status, "findings": findings})
                await job_store.append_event(job_id, messages.get(status, status))

            async def rule_status(code: str, status: str, detail: str) -> None:
                """逐条规则校验状态（理解规则 → 并发校验 → 命中/无风险）。"""
                async with _JOB_LOCK:
                    raw = await job_store.get_job(job_id)
                    if raw is None:
                        return
                    checks = raw.get("rule_checks") or {}
                    checks[code] = {"code": code, "status": status, "detail": detail}
                    await job_store.update_job(job_id, rule_checks=checks)
                if status == "matched":
                    await job_store.append_event(job_id, f"规则 {code} 命中风险")

            ai_started = {"chunk_count": 0}

            async def ai_chunk(chunk: str) -> None:
                """AI 流式片段写入 Redis（前端增量拉取展示打字机效果）。"""
                await job_store.append_ai_stream(job_id, chunk)
                ai_started["chunk_count"] += 1
                if ai_started["chunk_count"] == 1:
                    async with _JOB_LOCK:
                        await job_store.update_job(job_id, ai={"status": "running", "findings": 0})
                    await job_store.append_event(job_id, "AI 流式分析已启动，输出实时可见")

            try:
                result = await svc.run_scan(
                    user_id=user_id,
                    contract_id=contract_id,
                    request_meta={"ip": "job", "user_agent": "background", "duration_ms": 0, "trace_id": job_id},
                    progress_cb=progress,
                    init_cb=init_tasks,
                    task_cb=task_update,
                    ai_chunk_cb=ai_chunk,
                    ai_status_cb=ai_status,
                    rule_status_cb=rule_status,
                    action=f"contract.{label}",
                    audit_path=f"/api/v1/contracts/{contract_id}/scan",
                )
                async with _JOB_LOCK:
                    await job_store.update_job(
                        job_id,
                        status="done",
                        progress=100,
                        stage="done",
                        stage_message="扫描完成，报告已生成",
                        contract_id=result.contract.id,
                        risk_count=result.contract.risk_count,
                    )
                await job_store.append_event(job_id, f"扫描完成：共 {result.contract.risk_count} 项风险")
                logger.info("contract scan job done", extra={"job_id": job_id, "contract_id": contract_id})
            except Exception as exc:
                async with _JOB_LOCK:
                    await job_store.update_job(job_id, status="failed", stage="failed", stage_message=str(exc))
                await job_store.append_event(job_id, f"扫描失败：{exc}", level="error")
                logger.warning("contract scan job failed", extra={"job_id": job_id, "error": str(exc)})
                try:
                    async with SessionFactory() as err_session:
                        await ContractRiskService(err_session).mark_failed(
                            user_id=user_id, contract_id=contract_id, error=str(exc)
                        )
                except Exception:
                    logger.exception("failed to mark contract as failed")
