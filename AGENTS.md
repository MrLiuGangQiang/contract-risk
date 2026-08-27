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
- Test isolation: separate test DB/Redis; never touch dev/prod data. Tests that truncate a shared DB require explicit `ALLOW_DESTRUCTIVE_TEST_DB=1`.
- Naming: `test_<scenario>_<expected>` (e.g., `test_login_wrong_password_fails`).
- Core paths (login, DingTalk callback, config CRUD, RBAC) must be covered; target ≥ 80% coverage.
- Tests follow `docs/design/07-工程规范与代码规范.md` §6; every change ships with tests.

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