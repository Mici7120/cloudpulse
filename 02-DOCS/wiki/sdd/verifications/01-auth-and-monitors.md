---
type: verification
title: CloudPulse — Closing Verification: 01-auth-and-monitors
description: Closing verification evidence against origin/main including pytest, coverage, ruff, mypy, and Alembic rollback proof.
tags: [sdd, verify, milestone-1]
timestamp: 2026-11-23T07:50:00Z
topic: sdd
status: pass
spec: 02-DOCS/wiki/sdd/specs/01-auth-and-monitors.md
plan: 02-DOCS/wiki/sdd/plans/01-auth-and-monitors.md
branch: feat/01-auth-and-monitors
---

# Verification: 01-auth-and-monitors (Closing Mode vs `origin/main`)

## Verdict

**PASS** — All 9 acceptance criteria verified with observed command output, >= 80% coverage exceeded (`94.03%`), static checks clean, and Alembic migration rollback proven.

## 1. Automated Verification Matrix

| Check | Command | Observed Result |
| --- | --- | --- |
| Lint | `uv run ruff check .` | Exit `0` — `All checks passed!` |
| Format | `uv run ruff format --check .` | Exit `0` — `29 files already formatted` |
| Static typing | `uv run mypy app tests` | Exit `0` — `Success: no issues found in 27 source files` |
| Tests & coverage | `uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=80` | Exit `0` — `18 passed in 6.22s`, **94.03%** coverage (`385` stmts, `23` miss) |
| Alembic rollback (pytest) | `tests/test_migrations.py` | Exit `0` — verified `users`/`monitors` tables, columns, nullability, `ix_users_email` (unique), `ix_monitors_owner_id`, FK `CASCADE`, `downgrade base`, and re-`upgrade head` |
| Alembic rollback (CLI) | `uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head` | Exit `0` — `ALEMBIC_ROLLBACK_OK` (`-> 0001_initial -> base -> 0001_initial`) |
| Spec gate | `rsc spec gate 02-DOCS/wiki/sdd/specs/01-auth-and-monitors.md` | Exit `0` — `PASS  01-auth-and-monitors.md — 7 open point(s), 7 typed` |

## 2. Acceptance Criteria Proof

- **AC #1 (`GET /health`):** `tests/test_health.py` (`2 passed` — `200 ok` + `503 DATABASE_UNAVAILABLE`).
- **AC #2 & #3 (`POST /auth/register`):** `tests/test_auth.py` — UUID creation, email normalization, Argon2id hash stored in DB, no secret in response, case-insensitive duplicate -> `409 EMAIL_ALREADY_EXISTS`.
- **AC #4 (`POST /auth/login`):** `tests/test_auth.py` — valid HS256 JWT with verified `sub`, `iat`, `exp` claims; wrong password and unknown email both return identical `401 INVALID_CREDENTIALS` with constant-time Argon2 verification.
- **AC #5 (JWT protection on `/monitors*`):** `tests/test_monitors.py` — parametrized across all 5 endpoints (`POST`, `GET`, `GET/{id}`, `PATCH/{id}`, `DELETE/{id}`) for missing header, non-Bearer header, malformed JWT, expired JWT, orphan-user JWT, and wrong-secret JWT.
- **AC #6 (`/monitors` CRUD):** `tests/test_monitors.py` — defaults (`60`, `200`, `true`), list, get, partial update with `updated_at` refresh, empty `{}` no-op, physical `DELETE` (`204`), and `404` afterwards.
- **AC #7 (Strict user isolation):** `tests/test_monitors.py` — User B cannot list, read, patch, or delete User A's monitor (`404 MONITOR_NOT_FOUND` on all item operations; User A's data untouched).
- **AC #8 (Input validation):** `tests/test_monitors.py` — `POST` and `PATCH` reject non-`http/https` URLs, CRLF/control chars, out-of-range `interval_seconds`/`expected_status`, blank `name`, explicit `null` in `PATCH`, and invalid UUID path params with exact `{"detail", "code"}` `422 VALIDATION_ERROR`.
- **AC #9 (Migration reversibility & quality):** Proven via `tests/test_migrations.py`, standalone Alembic CLI run, `ruff`, `mypy`, and `pytest --cov` (`94.03%`).

## 3. Rollback Plan

If Milestone 1 needs to be reverted after deployment:

1. **Database rollback:** Run `cd backend && uv run alembic downgrade base` (verified to cleanly drop `ix_monitors_owner_id`, `monitors`, `ix_users_email`, and `users` in reverse dependency order).
2. **Code rollback:** Revert the Milestone 1 merge commit on `main` via `git revert -m 1 <merge-sha>`.
3. **CI rollback:** Removing the `backend-tests` job in `.github/workflows/ci-spec-gate.yml` restores the pre-Milestone 1 workflow cleanly.
