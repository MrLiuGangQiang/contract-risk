# Repository Guidelines

These guidelines apply to all contributors, including AI agents (e.g., Codex). **Design documents in `docs/design/` are the single source of truth and MUST be followed — do not improvise beyond them.**

## Project Structure & Module Organization

- `docs/` — design docs: principles (01), architecture (02), data model (03), auth/DingTalk (04), API spec (05), security (06), engineering standards (07), roadmap (08), NFR/ops (09).
- `backend/` — FastAPI app (Phase 1):
  - `app/api/` routes, `app/services/` business logic, `app/repositories/` data access, `app/models/` ORM, `app/schemas/` Pydantic DTOs
  - `app/core/` config/security/logging, `app/integrations/` Redis/DingTalk clients, `app/domain/` enums/rules
  - `migrations/` Alembic, `tests/` pytest
- `frontend/` — Vue 3 + TS SPA: `src/api`, `src/views`, `src/components`, `src/stores`, `src/router`.

Layering is strict and one-directional: `api → services → repositories → domain`. No cross-layer imports, no SQL in services, no business rules in repositories.

## Build, Test, and Development Commands

Run from `backend/` (Python 3.12+, venv + pip):

- `python -m venv .venv` + `pip install -r requirements.txt` — install deps (pinned in `requirements.lock.txt`).
- `.\.venv\Scripts\alembic.exe upgrade head` — apply DB migrations (`.env` holds DB/Redis credentials; never commit it).
- `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload` — dev server.
- `.\.venv\Scripts\python.exe -m pytest -q` — tests (use a Redis db isolated from dev, see `tests/conftest.py`).
- Frontend (`frontend/`): `npm install`, `npm run dev`, `npm run build`.

## Coding Style & Naming Conventions

- Python 3.12+: `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants, full type hints (mypy strict), Google-style docstrings for public APIs, black + ruff formatting.
- Frontend: TypeScript `strict`, ESLint + Prettier, `PascalCase` component files.
- Database: snake_case tables (`sys_` prefix) and columns; schema changes only via Alembic migrations (upgrade + downgrade).

## Testing Guidelines

- pytest + httpx `AsyncClient` for integration tests through the real API layer.
- Test isolation: separate test DB/Redis; never touch dev/prod data.
- Naming: `test_<scenario>_<expected>` (e.g., `test_login_wrong_password_fails`).
- Core paths (login, DingTalk callback, config CRUD, RBAC) must be covered; target ≥ 80% coverage.
- Tests follow `docs/design/07-工程规范与代码规范.md` §6; every change ships with tests.

### ⛔ 数据库保护铁律（不可违反，违反即事故）

> 背景：2026-08-29 曾因集成测试清空共享开发库，导致超管、配置、合同数据全部丢失。
> 以下规则为硬性约束，任何情况下不得违反，不存在豁免途径：

1. **共享数据库（`DATABASE_URL` 指向的库）只读对待**：任何脚本、测试、一次性命令都不得对其执行
   `TRUNCATE / DELETE / UPDATE / DROP`，也不得直接修改 `sys_user / sys_config` 等业务表（包括"重置密码"之类的"修复"脚本）。
2. **集成测试必须使用独立测试库**：运行任何需要数据库的测试前，必须设置 `TEST_DATABASE_URL`
   指向专用测试库（与开发库不同库名）；`tests/conftest.py` 已写死校验——缺少该变量或指向开发库时直接拒绝运行。
   若测试库不存在，**正确做法是停止并告知用户创建**，而不是动用共享库。
3. **已删除 `ALLOW_DESTRUCTIVE_TEST_DB` 逃生门**：不得重新引入任何"显式允许清库"的开关。
4. **纯函数单测**（如 `test_contract_scan.py`、`test_risk_rule_markdown.py`）不需要数据库，可安全运行。
5. 需要修改数据库数据的操作（如重置密码），**一律先征得用户同意**，并明确说明影响范围。

## Commit & Pull Request Guidelines

- Conventional Commits: `feat(auth): ...`, `fix(config): ...`, `docs: ...`, `refactor: ...`, `test: ...`.
- Work on `feature/*` branches; `main` is protected — merge via PR after review.
- PR must pass CI (lint, type check, tests, dependency scan), include a clear description, and update docs/design specs when interfaces or behavior change.

## Security & Configuration Tips

- Never commit `.env`, real credentials, or logs. `.env.example` is the only committed template.
- DB/Redis/DingTalk credentials come from environment variables only; DingTalk `client_secret` is encrypted at rest and masked in responses/logs.
- No patch-style fixes: changes follow 「problem → design → review → implementation → test」, per docs/design/01.

## Agent-Specific Instructions

AI agents must follow the design documents — they are the contract, not a suggestion:

1. **Read first**: before writing or changing code, tests, migrations, or APIs, read the relevant docs in `docs/design/` (07 工程规范 lists the review checklist).
2. **No free improvisation**: do not invent tech stack choices, DB tables/columns, endpoints, error codes, schemas, or naming conventions. Anything outside the design docs must first be added there through the documented change flow; otherwise stop and flag it.
3. **Do exactly what is specified**: implement only what the docs and task require; no unrequested features, "improvements", or refactors.
4. **No silent deviation**: if a doc conflicts with reality or has a gap, stop, report the issue, and wait for a decision — never patch around it.
5. **Keep docs in sync**: any design/interface change must update `docs/design/` before or with the code.
6. **数据库铁律（最高优先级）**：共享数据库只读——禁止运行任何会写/清空 `DATABASE_URL` 指向数据库的测试或脚本；集成测试必须配置独立的 `TEST_DATABASE_URL`，否则停止测试并告知用户；禁止绕过 `tests/conftest.py` 的隔离校验；修改库内数据前必须征得用户同意。详见「Testing Guidelines → 数据库保护铁律」。