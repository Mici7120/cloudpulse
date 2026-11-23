---
type: analysis
title: CloudPulse — Consistency Analysis: 01-auth-and-monitors
description: Cross-artifact verification between spec, plan, constitution, REVIEW.md, and .rsc-risk.json.
tags: [sdd, analyze, milestone-1]
timestamp: 2026-11-23T07:23:00Z
topic: sdd
status: pass
spec: 02-DOCS/wiki/sdd/specs/01-auth-and-monitors.md
plan: 02-DOCS/wiki/sdd/plans/01-auth-and-monitors.md
branch: feat/01-auth-and-monitors
---

# Analysis: 01-auth-and-monitors

## Verdict

**PASS** — Zero contradictions between spec, plan, constitution (`v1.0.0`), `REVIEW.md`, and `.rsc-risk.json`. Ready for Etapa 4 (`implement`).

## 1. Acceptance Criteria Traceability Matrix

| Spec AC | Plan Tasks | Planned Verification |
| --- | --- | --- |
| AC #1: `GET /health` (200 ok + 503 db error) | T2 | `tests/test_health.py` |
| AC #2: `POST /auth/register` (201, hashed password, no secret leak) | T3 | `tests/test_auth.py` |
| AC #3: Duplicate email (case-insensitive) -> `409 EMAIL_ALREADY_EXISTS` | T3 | `tests/test_auth.py` |
| AC #4: `POST /auth/login` (200 JWT / 401 `INVALID_CREDENTIALS`) | T3 | `tests/test_auth.py` |
| AC #5: JWT protection on all `/monitors*` routes (missing/invalid/expired -> 401) | T4 | `tests/test_monitors.py` |
| AC #6: Full `/monitors` CRUD (`201`, `200`, `200`, `200`, `204`) + persistence | T4 | `tests/test_monitors.py` |
| AC #7: Strict User A vs User B isolation (`GET/PATCH/DELETE` -> `404`) | T4 | `tests/test_monitors.py` |
| AC #8: Field validation (`http/https` URL, `interval_seconds` 30..86400, `expected_status` 100..599 -> `422`) | T4 | `tests/test_monitors.py` |
| AC #9: Reversible Alembic migration + `ruff` + `mypy` + `pytest --cov >= 80%` | T5, T6 | `tests/test_migrations.py` + CLI gates |

## 2. Constitution & Policy Alignment

- **Stack canon (P1, P2, P4, P5):** Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL via `docker-compose.yml`, `uv.lock` committed. Aligned.
- **Quality & Typing (P6, P7, P8):** Ruff, mypy, strict TDD with `pytest` and >= 80% coverage. Aligned.
- **Boundaries & Error Envelope (P9, P10):** Only `backend/` and `docker-compose.yml` touched for code; all errors return `{"detail", "code"}` and are exposed in OpenAPI. Aligned.
- **Secrets & Tier 2 Risk (P14, P16, `.rsc-risk.json`):** No `.env` committed (only `.env.example`), Argon2 password hashing, JWT secret from env. Paths `backend/app/api/routes/auth.py`, `backend/app/core/security.py`, and `backend/alembic/` trigger Tier 2 -> 3-lens panel required before PR. Aligned.
- **Out-of-scope guard:** No ping worker, no `01-TOOLS/` connectors, no `frontend/`, no refresh tokens or admin roles in plan tasks. Aligned.

## 3. Identified Risks to Watch During Implementation

1. **UUID portability between PostgreSQL and SQLite:** Use SQLAlchemy 2.x generic `Uuid` type (`sqlalchemy.Uuid`) rather than `postgresql.UUID` so models and Alembic migrations work cleanly on both PostgreSQL and SQLite tests.
2. **Invalid UUID path parameters:** FastAPI parses `monitor_id: UUID`; malformed UUIDs will hit `RequestValidationError` (`422 VALIDATION_ERROR`) consistently through the global error handler.
3. **Alembic `env.py` URL override:** Allow tests to inject a temporary `DATABASE_URL` into Alembic config without mutating production config.
4. **Timezone-aware timestamps:** Store UTC timestamps consistently (`datetime.now(timezone.utc)`) so `exp` in JWT and `created_at`/`updated_at` comparisons never fail on naive vs aware datetimes.
