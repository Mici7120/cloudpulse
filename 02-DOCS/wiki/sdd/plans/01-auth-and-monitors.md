---
type: plan
title: CloudPulse — Plan & Tasks: 01-auth-and-monitors
description: Technical architecture, data model, security design, and TDD task breakdown for Milestone 1.
tags: [sdd, plan, tasks, milestone-1, auth, monitors]
timestamp: 2026-11-23T07:23:00Z
topic: sdd
status: active
spec: 02-DOCS/wiki/sdd/specs/01-auth-and-monitors.md
branch: feat/01-auth-and-monitors
---

# Plan & Tasks: 01-auth-and-monitors

## 1. Architecture & Repository Layout

```text
docker-compose.yml                  # PostgreSQL 16 service with healthcheck
backend/
  pyproject.toml                    # Dependencies, Ruff, Mypy, Pytest config
  uv.lock                           # Committed lockfile (Constitution P5)
  .env.example                      # Required env vars without real secrets (P14)
  alembic.ini                       # Alembic CLI configuration
  alembic/
    env.py                          # Reads DATABASE_URL from app settings, targets Base.metadata
    script.py.mako
    versions/
      0001_create_users_and_monitors.py  # Reversible upgrade() and downgrade()
  app/
    __init__.py
    main.py                         # FastAPI app factory, error handlers, routers
    core/
      __init__.py
      config.py                     # pydantic-settings Settings (DATABASE_URL, JWT_SECRET_KEY, etc.)
      errors.py                     # AppError + structured {"detail", "code"} handlers
      security.py                   # Argon2 password hashing + HS256 JWT issue/verify
    db/
      __init__.py
      base.py                       # DeclarativeBase + Timestamp/UUID conventions
      session.py                    # Engine, SessionLocal, get_db dependency
    models/
      __init__.py
      user.py                       # User ORM model
      monitor.py                    # Monitor ORM model
    schemas/
      __init__.py
      common.py                     # ErrorResponse, HealthResponse
      auth.py                       # RegisterRequest, UserResponse, LoginRequest, TokenResponse
      monitor.py                    # MonitorCreate, MonitorUpdate, MonitorResponse, MonitorListResponse
    api/
      __init__.py
      deps.py                       # get_current_user (HTTPBearer -> JWT -> User lookup)
      routes/
        __init__.py
        health.py                   # GET /health
        auth.py                     # POST /auth/register, POST /auth/login
        monitors.py                 # CRUD /monitors
  tests/
    conftest.py                     # SQLite in-memory engine (StaticPool), TestClient, auth fixtures
    test_health.py
    test_auth.py
    test_monitors.py
    test_migrations.py              # Alembic upgrade -> downgrade -> upgrade test
```

## 2. Data Model

### `users`
- `id`: `Uuid` (PK, default `uuid.uuid4`) — dialect-portable across PostgreSQL (`UUID`) and SQLite (`CHAR(32)`).
- `email`: `String(320)`, `nullable=False`, `unique=True`, indexed (`ix_users_email`), normalized (`strip().lower()`).
- `password_hash`: `String(255)`, `nullable=False` (Argon2id hash via `argon2-cffi`).
- `created_at`: `DateTime(timezone=True)`, `nullable=False`, UTC server/default timestamp.

### `monitors`
- `id`: `Uuid` (PK, default `uuid.uuid4`).
- `owner_id`: `Uuid`, `ForeignKey("users.id", ondelete="CASCADE")`, `nullable=False`, indexed (`ix_monitors_owner_id`).
- `name`: `String(120)`, `nullable=False`.
- `url`: `String(2048)`, `nullable=False` (validated `http://` or `https://`).
- `interval_seconds`: `Integer`, `nullable=False`, default `60` (validated `30..86400`).
- `expected_status`: `Integer`, `nullable=False`, default `200` (validated `100..599`).
- `is_active`: `Boolean`, `nullable=False`, default `True`.
- `created_at`: `DateTime(timezone=True)`, `nullable=False`.
- `updated_at`: `DateTime(timezone=True)`, `nullable=False`.

## 3. Security & Error Contract Design

- **Password hashing:** `argon2.PasswordHasher()` (Argon2id with per-user random salt, constant-time verification).
- **JWT:** `PyJWT` (`HS256`) with claims `sub` (UUID string), `iat` (UTC epoch), `exp` (UTC epoch + `JWT_EXPIRE_MINUTES * 60`). `JWT_SECRET_KEY` loaded from env; minimum length enforced in production config, never hardcoded to a secret in git.
- **Auth dependency:** `HTTPBearer(auto_error=False)`. Missing header -> `401 UNAUTHORIZED`; malformed/expired/unknown-user token -> `401 INVALID_TOKEN`.
- **User isolation:** Every `/monitors` query filters strictly by `Monitor.owner_id == current_user.id`. Any missing or foreign `monitor_id` returns `404 MONITOR_NOT_FOUND`.
- **Error envelope:** Custom `AppError(status_code, detail, code)` + global handlers for `AppError`, `RequestValidationError` (`422 VALIDATION_ERROR`), and `StarletteHTTPException` so every error returns `{"detail": "...", "code": "..."}`.

## 4. Testing & Tooling Strategy

- **Test DB:** SQLite in-memory (`sqlite+pysqlite:///:memory:` with `StaticPool` and `PRAGMA foreign_keys=ON`) in `tests/conftest.py` so tests run cleanly and deterministically in sandbox and CI without external services, while `DATABASE_URL` in production/Docker targets PostgreSQL (`postgresql+psycopg://...`).
- **Alembic reversibility test:** Runs `alembic upgrade head`, verifies tables exist, runs `alembic downgrade base`, verifies tables are dropped, and runs `alembic upgrade head` again against a temporary SQLite file.
- **Static checks:** `ruff check .`, `ruff format --check .`, `mypy app tests`, `pytest --cov=app --cov-report=term-missing --cov-fail-under=80`.

## 5. TDD Task List

| ID | Task | Acceptance Criteria Covered | Done-check |
| --- | --- | --- | --- |
| T1 | Initialize `backend/pyproject.toml`, `uv.lock`, `backend/.env.example`, and root `docker-compose.yml` | Constitution P1, P4, P5, P9, P14 | `uv sync` succeeds and lockfile is generated |
| T2 | TDD Slice A: Config, DB session, structured error envelope, and `GET /health` (200 ok + 503 db unavailable) | AC #1 | `pytest tests/test_health.py` red -> green |
| T3 | TDD Slice B: `User` model, Argon2 security, JWT helper, `POST /auth/register` and `POST /auth/login` | AC #2, #3, #4 | `pytest tests/test_auth.py` red -> green |
| T4 | TDD Slice C: `Monitor` model, JWT `get_current_user` dependency, CRUD `/monitors`, input validation, and strict User A/B isolation | AC #5, #6, #7, #8 | `pytest tests/test_monitors.py` red -> green |
| T5 | Alembic setup and reversible migration `0001_create_users_and_monitors.py` + reversibility test | AC #9 | `pytest tests/test_migrations.py` red -> green |
| T6 | Full quality gate: `pytest --cov`, `ruff check`, `ruff format --check`, `mypy` | AC #9, Constitution P6, P7, P8 | All commands exit 0 with >= 80% coverage |
| T7 | Tier 2 governance: `rsc risk --base origin/main`, 3-lens review (`correctness`, `security`, `tests`), fix confirmed findings, record ledger panel, update progress & Decision queue | Constitution P16, `.rsc-risk.json` | Panel recorded, zero unresolved blockers |
