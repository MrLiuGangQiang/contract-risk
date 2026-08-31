"""合同扫描任务存储（Redis，临时状态，用于前端进度展示）。

任务生命周期短（默认 10 分钟），数据可重建，不作为业务唯一数据源。
"""
import json
from datetime import datetime
from typing import Any

from app.domain.constants import REDIS_CONTRACT_JOB_PREFIX
from app.integrations import redis_client

JOB_TTL_SECONDS = 600


def _job_key(job_id: str) -> str:
    """构造任务 Redis 键。"""
    return f"{REDIS_CONTRACT_JOB_PREFIX}{job_id}"


def _contract_job_key(contract_id: int) -> str:
    """构造合同 -> 任务关联键（用于从合同恢复进度查看）。"""
    return f"{REDIS_CONTRACT_JOB_PREFIX}contract:{contract_id}"


async def link_contract(job_id: str, contract_id: int) -> None:
    """建立合同与任务的关联（进度查询入口）。"""
    await redis_client.get_redis().set(_contract_job_key(contract_id), job_id, ex=JOB_TTL_SECONDS)


async def get_job_by_contract(contract_id: int) -> dict[str, Any] | None:
    """按合同查询关联任务状态。"""
    job_id = await redis_client.get_redis().get(_contract_job_key(contract_id))
    if job_id is None:
        return None
    return await get_job(job_id if isinstance(job_id, str) else job_id.decode())


async def create_job(job_id: str, data: dict[str, Any]) -> None:
    """创建任务初始状态（job_id 一并存储，便于按合同恢复进度时继续轮询）。"""
    data = {
        "job_id": job_id,
        "status": "running",
        "progress": 0,
        "stage": "created",
        "stage_message": "任务已创建",
        **data,
    }
    await redis_client.get_redis().set(_job_key(job_id), json.dumps(data, ensure_ascii=False), ex=JOB_TTL_SECONDS)


async def update_job(job_id: str, **fields: Any) -> None:
    """更新任务状态字段（不覆盖其它字段）。"""
    raw = await redis_client.get_redis().get(_job_key(job_id))
    if raw is None:
        return
    data = json.loads(raw)
    data.update(fields)
    await redis_client.get_redis().set(_job_key(job_id), json.dumps(data, ensure_ascii=False), ex=JOB_TTL_SECONDS)


async def append_event(job_id: str, message: str, level: str = "info") -> None:
    """追加任务日志事件（前端终端式滚动展示）。"""
    raw = await redis_client.get_redis().get(_job_key(job_id))
    if raw is None:
        return
    data = json.loads(raw)
    events = data.get("events") or []
    events.append({"time": datetime.now().strftime("%H:%M:%S"), "level": level, "message": message})
    data["events"] = events[-100:]
    await redis_client.get_redis().set(_job_key(job_id), json.dumps(data, ensure_ascii=False), ex=JOB_TTL_SECONDS)


async def get_job(job_id: str) -> dict[str, Any] | None:
    """读取任务状态。"""
    raw = await redis_client.get_redis().get(_job_key(job_id))
    if raw is None:
        return None
    return json.loads(raw)


async def get_job_id_by_contract(contract_id: int) -> str | None:
    """返回合同关联的任务 ID（可能已过期）。"""
    value = await redis_client.get_redis().get(_contract_job_key(contract_id))
    if value is None:
        return None
    return value if isinstance(value, str) else value.decode()


def _ai_stream_key(job_id: str) -> str:
    """AI 流式输出存储键（完整累积文本，前端按 offset 增量拉取）。"""
    return f"{REDIS_CONTRACT_JOB_PREFIX}stream:{job_id}"


async def append_ai_stream(job_id: str, chunk: str) -> None:
    """追加 AI 流式输出片段。"""
    await redis_client.get_redis().append(_ai_stream_key(job_id), chunk)
    await redis_client.get_redis().expire(_ai_stream_key(job_id), JOB_TTL_SECONDS)


async def get_ai_stream(job_id: str) -> str:
    """读取 AI 流式输出全文（追加式，前端轮询实现打字机效果）。"""
    value = await redis_client.get_redis().get(_ai_stream_key(job_id))
    if value is None:
        return ""
    return value if isinstance(value, str) else value.decode(errors="replace")