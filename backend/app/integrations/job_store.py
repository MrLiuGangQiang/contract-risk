"""合同扫描任务存储（Redis，临时状态，用于前端进度展示）。

任务生命周期短（默认 10 分钟），数据可重建，不作为业务唯一数据源。
"""
import json
from typing import Any

from app.domain.constants import REDIS_CONTRACT_JOB_PREFIX
from app.integrations import redis_client

JOB_TTL_SECONDS = 600


def _job_key(job_id: str) -> str:
    """构造任务 Redis 键。"""
    return f"{REDIS_CONTRACT_JOB_PREFIX}{job_id}"


async def create_job(job_id: str, data: dict[str, Any]) -> None:
    """创建任务初始状态。"""
    data = {"status": "running", "progress": 0, "stage": "created", "stage_message": "任务已创建", **data}
    await redis_client.get_redis().set(_job_key(job_id), json.dumps(data, ensure_ascii=False), ex=JOB_TTL_SECONDS)


async def update_job(job_id: str, **fields: Any) -> None:
    """更新任务状态字段（不覆盖其它字段）。"""
    raw = await redis_client.get_redis().get(_job_key(job_id))
    if raw is None:
        return
    data = json.loads(raw)
    data.update(fields)
    await redis_client.get_redis().set(_job_key(job_id), json.dumps(data, ensure_ascii=False), ex=JOB_TTL_SECONDS)


async def get_job(job_id: str) -> dict[str, Any] | None:
    """读取任务状态。"""
    raw = await redis_client.get_redis().get(_job_key(job_id))
    if raw is None:
        return None
    return json.loads(raw)