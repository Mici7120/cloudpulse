---
type: progress
title: CloudPulse — Progress & Decision Queue: 01-auth-and-monitors
description: Execution progress, verification evidence, 3-lens Tier 2 review outcomes, and Decision queue for Milestone 1.
tags: [sdd, progress, milestone-1]
timestamp: 2026-11-23T07:33:00Z
topic: sdd
status: in-review
spec: 02-DOCS/wiki/sdd/specs/01-auth-and-monitors.md
plan: 02-DOCS/wiki/sdd/plans/01-auth-and-monitors.md
branch: feat/01-auth-and-monitors
---

# Progress: 01-auth-and-monitors

## Task Checklist

- [x] **T1** — Initialize `backend/pyproject.toml`, `backend/uv.lock`, `backend/.env.example`, `backend/.gitignore`, and root `docker-compose.yml`.
- [x] **T2** — TDD Slice A: Config, DB session, structured error envelope (`detail`, `code`), and `GET /health` (`200 ok` + `503 DATABASE_UNAVAILABLE`).
- [x] **T3** — TDD Slice B: `User` model, Argon2 password hashing, HS256 JWT issue/decode, `POST /auth/register`, and `POST /auth/login`.
- [x] **T4** — TDD Slice C: `Monitor` model, `get_current_user` JWT dependency, CRUD `/monitors`, input validation, and strict per-user isolation (`404 MONITOR_NOT_FOUND`).
- [x] **T5** — Alembic setup and reversible migration `0001_create_users_and_monitors.py` (`upgrade -> downgrade -> upgrade` verified with column/index/FK inspection).
- [x] **T6** — Full quality gate: `ruff check`, `ruff format --check`, `mypy` (strict), and `pytest --cov` (>= 80% coverage).
- [x] **T7** — Tier 2 governance: `rsc risk --base origin/main`, 3-lens fresh-context review (`correctness`, `security`, `tests`), Round 1 fixes verified green, and panel recorded in review ledger (`01-auth-and-monitors/all`).

## Tier 2 Review Panel Summary (Round 1)

- **Reported:** 19 raw findings (18 unique after deduplicating explicit `null` in `PATCH` across `correctness` and `tests`):
  - `correctness`: 0 blockers, 1 warning, 3 nits
  - `security`: 1 blocker, 3 warnings, 2 nits
  - `tests`: 2 blockers, 4 warnings, 3 nits
- **Confirmed:** 18 unique findings.
- **Fixed in Round 1:** 17 unique findings (all 3 blockers, 6 warnings, and all 8 nits):
  - Removed default `JWT_SECRET_KEY`, switched to `SecretStr`, rejected `.env.example` placeholder, constrained `JWT_ALGORITHM` to `HS256|HS384|HS512`.
  - Equalized login timing on unknown email using precomputed `DUMMY_PASSWORD_HASH` (Argon2).
  - Rejected ASCII control characters (`\r`, `\n`, `\t`) in monitor URLs.
  - Rejected explicit `null` fields in `PATCH /monitors/{id}` (`422 VALIDATION_ERROR`) and avoided spurious `updated_at` bumps.
  - Preserved `exc.headers` in `StarletteHTTPException` handler; aligned `Monitor` `server_default` with Alembic migration; escaped `%` in `alembic/env.py`; bound PostgreSQL port to `127.0.0.1` in `docker-compose.yml`.
  - Expanded `pytest` suite: parametrized JWT auth across all 5 `/monitors` endpoints, orphan/wrong-secret JWT, full `PATCH` validation & bounds, invalid UUID, JWT claims verification, exact `{"detail", "code"}` 422 envelope, and Alembic column/index/FK inspection.
- **Deferred to Decision queue:** 1 security warning (`[review-after]` — private/loopback IP SSRF policy for Milestone 2 worker vs Milestone 1 ingestion).

## Decision queue

- **[resolved]** `SSRF policy for private/loopback/metadata monitor URLs` (`backend/app/schemas/monitor.py`) — Agreed 2026-11-23 (logged in `02-DOCS/wiki/sdd/decisions.md`): keep Milestone 1 ingestion without private/loopback blocking, and enforce post-DNS-resolution IP filtering in Milestone 2's ping worker with `ALLOW_PRIVATE_MONITOR_URLS=false` by default.

