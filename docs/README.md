# 合同风险扫描系统 — 文档中心

企业级「合同风险扫描」平台。当前阶段：**钉钉登录 + 超管配置中心**。

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [设计原则与约束](design/01-设计原则与约束.md) | 设计原则（P1~P10）、硬性约束、技术栈、ADR |
| [总体架构设计](design/02-总体架构设计.md) | 分层架构、模块划分、关键机制、前端架构、部署拓扑 |
| [数据模型设计](design/03-数据模型设计.md) | 表结构、Redis 键、种子数据、一致性 |
| [认证与授权设计](design/04-认证与授权设计.md) | 本地登录、钉钉登录流程、JWT、RBAC |
| [API 设计规范](design/05-API设计规范.md) | 响应包裹、错误码、端点清单 |
| [安全设计](design/06-安全设计.md) | 传输/密钥/OAuth/应用安全、限流、审计 |
| [工程规范与代码规范](design/07-工程规范与代码规范.md) | 仓库结构、Git 工作流、注释/分层/测试/日志规范 |
| [实施路线图](design/08-实施路线图.md) | 阶段划分与验收标准 |
| [非功能性需求与运维设计](design/09-非功能性需求与运维设计.md) | NFR、可观测性、备份恢复、发布运维 |

## 环境信息（仅本地参考）

数据库与 Redis 连接信息见仓库根目录 `环境信息.txt`；**接入代码时必须通过 `.env` 注入，禁止硬编码**。

## 快速开始（Phase 1 已实现）

### 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# 复制 .env.example 为 .env，填入数据库/Redis/初始超管配置
.\.venv\Scripts\alembic.exe upgrade head   # 初始化表结构
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- 初始超管由 `.env` 的 `ADMIN_USERNAME/ADMIN_PASSWORD` 首次启动自动创建，默认 `admin/123456`，**首次登录强制改密**（弱初始密码仅用于首登）。
- 测试：`.\.venv\Scripts\python.exe -m pytest -q`（测试使用独立 Redis db 与开发库隔离）。
  > **重要**：当前数据库账号无建库权限，pytest 会清空并重建 `contract_risk` 库的业务表；
  > **必须在显式设置 `ALLOW_DESTRUCTIVE_TEST_DB=1` 后运行**，否则 pytest 会拒绝启动；
  > **严禁在共享/生产库上运行 pytest**，应配置独立测试库后再运行。

```powershell
# 仅在明确同意清库时运行
$env:ALLOW_DESTRUCTIVE_TEST_DB='1'
.\.venv\Scripts\python.exe -m pytest -q
```

### 前端

```powershell
cd frontend
npm install
npm run dev   # http://localhost:5173，/api 代理到 http://127.0.0.1:8000
```

### 钉钉配置

1. 超管本地登录 → 修改初始密码 → 进入「钉钉配置」页；
2. 在[钉钉开发者后台](https://open-dev.dingtalk.com/)创建企业内部应用，从「基础信息 → 凭证与基础信息」获取 Client ID / Client Secret，并在后台首页/应用详情获取企业组织 ID（CorpId），按官方文档申请权限、配置「重定向URL（回调域名）」并发布应用；
3. 在配置页填入 Client ID / Client Secret / CorpId / 回调地址并保存（Client Secret 加密存储）；
4. 点击「连通性测试」验证配置；启用后员工即可通过钉钉扫码登录。

> **本地调试**：钉钉官方允许测试阶段将「重定向URL（回调域名）」配置为 `http://localhost:5173`，回调地址填 `http://localhost:5173/dingtalk/callback`；生产环境必须替换为公网 HTTPS 域名。若后台拒绝 `localhost`，可改用 `http://127.0.0.1:5173`。