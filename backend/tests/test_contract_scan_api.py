"""合同后台扫描集成测试（《11-合同风险识别核心功能设计》第 5/7 节）。

后台扫描语义：
- 上传后合同立即入库（扫描中/已完成），返回 job_id + contract_id；
- 扫描在后台任务执行，/contracts/jobs/{job_id} 与 /contracts/{id}/job 可查进度；
- 重扫为异步任务；非法文件拒绝。
"""
import asyncio

from httpx import AsyncClient

SAMPLE_TEXT = (
    "项目合作协议\n"
    "第一条 甲方逾期付款应承担违约责任。\n"
    "第二条 项目范围、需求变更与验收标准以双方书面确认为准。\n"
    "第三条 知识产权归甲方所有。\n"
    "第四条 因不可抗力导致的延期双方互不承担责任。\n"
    "第五条 如发生争议，提交甲方所在地法院管辖。\n"
)


async def _wait_job_done(client: AsyncClient, headers: dict, job_id: str) -> dict:
    """轮询任务直到终态（测试环境 AI 关闭，扫描为纯规则匹配，秒级完成）。"""
    for _ in range(50):
        resp = await client.get(f"/api/v1/contracts/jobs/{job_id}", headers=headers)
        assert resp.status_code == 200, resp.text
        job = resp.json()["data"]
        if job["status"] in ("done", "failed"):
            return job
        await asyncio.sleep(0.2)
    raise AssertionError("scan job did not finish in time")


async def test_upload_returns_job_and_contract_immediately(
    client: AsyncClient, admin_token: str
) -> None:
    """上传立即返回 job_id + contract_id，合同出现在列表中。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    files = {"file": ("demo.txt", SAMPLE_TEXT.encode("utf-8"), "text/plain")}
    resp = await client.post("/api/v1/contracts/upload", headers=headers, files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["job_id"]
    contract_id = body["data"]["contract_id"]

    list_resp = await client.get("/api/v1/contracts", headers=headers)
    rows = [c for c in list_resp.json()["data"]["items"] if c["id"] == contract_id]
    assert rows, "合同上传后应立即出现在列表"
    # 扫描很快，状态为扫描中(3)或已完成(1)均合法
    assert rows[0]["status"] in (1, 3)

    job = await _wait_job_done(client, headers, body["data"]["job_id"])
    assert job["status"] == "done"
    assert job["contract_id"] == contract_id
    assert (job["risk_count"] or 0) > 0


async def test_upload_invalid_extension_rejected(
    client: AsyncClient, admin_token: str
) -> None:
    """非支持格式直接拒绝（20002），不创建任务。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    files = {"file": ("photo.jpg", b"binary", "image/jpeg")}
    resp = await client.post("/api/v1/contracts/upload", headers=headers, files=files)
    assert resp.json()["code"] == 20002


async def test_contract_job_endpoint_tracks_progress(
    client: AsyncClient, admin_token: str
) -> None:
    """按合同查询后台扫描进度：与 job_id 查询一致；完成后合同状态为已完成。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    files = {"file": ("track.txt", SAMPLE_TEXT.encode("utf-8"), "text/plain")}
    resp = await client.post("/api/v1/contracts/upload", headers=headers, files=files)
    data = resp.json()["data"]
    contract_id = data["contract_id"]

    # 按合同查进度（可能在任务过期前任意状态，这里等待终态）
    job = await _wait_job_done(client, headers, data["job_id"])
    assert job["status"] == "done"

    by_contract = await client.get(f"/api/v1/contracts/{contract_id}/job", headers=headers)
    assert by_contract.status_code == 200
    assert by_contract.json()["data"]["status"] == "done"

    detail = await client.get(f"/api/v1/contracts/{contract_id}", headers=headers)
    assert detail.json()["data"]["contract"]["status"] == 1
    assert len(detail.json()["data"]["risks"]) > 0


async def test_rescan_runs_in_background(
    client: AsyncClient, admin_token: str
) -> None:
    """重新扫描：返回 job_id，后台完成后风险统计刷新。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    files = {"file": ("rescan.txt", SAMPLE_TEXT.encode("utf-8"), "text/plain")}
    resp = await client.post("/api/v1/contracts/upload", headers=headers, files=files)
    data = resp.json()["data"]
    contract_id = data["contract_id"]
    first = await _wait_job_done(client, headers, data["job_id"])
    assert first["status"] == "done"

    resp = await client.post(f"/api/v1/contracts/{contract_id}/rescan", headers=headers)
    assert resp.json()["code"] == 0
    second = await _wait_job_done(client, headers, resp.json()["data"]["job_id"])
    assert second["status"] == "done"
    assert second["risk_count"] == first["risk_count"]
