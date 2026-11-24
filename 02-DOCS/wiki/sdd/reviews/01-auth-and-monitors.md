---
type: review
title: CloudPulse — Closing Review: 01-auth-and-monitors
description: Tier 2 3-lens closing review (correctness, security, tests) for Milestone 1.
tags: [sdd, review, milestone-1, tier-2]
timestamp: 2026-11-23T07:50:00Z
topic: sdd
status: pass
spec: 02-DOCS/wiki/sdd/specs/01-auth-and-monitors.md
branch: feat/01-auth-and-monitors
---

# Closing Review: 01-auth-and-monitors

0 findings: 0 blockers, 0 warnings, 0 nits (post-Round 1 remediation)

## Tier 2 Panel History (Round 1 -> Closing)

| Lens | Reported (Round 1) | Confirmed | Fixed | Deferred / Decided |
| --- | --- | --- | --- | --- |
| `correctness` | 0 blockers, 1 warning, 3 nits | 4 | 4 | 0 |
| `security` | 1 blocker, 3 warnings, 2 nits | 6 | 5 | 1 (`SSRF` -> logged in `decisions.md` for Milestone 2) |
| `tests` | 2 blockers, 4 warnings, 3 nits | 8 unique (1 dup with correctness) | 8 | 0 |
| **Total (unique)** | **18** | **18** | **17** | **1 (agreed by owner)** |

## Key Remediations Verified

1. **JWT secret & algorithm hardening (`security` blocker + nit):** Removed default `JWT_SECRET_KEY`, switched to `SecretStr`, rejected `.env.example` placeholder, constrained `JWT_ALGORITHM` to `HS256|HS384|HS512`.
2. **Constant-time login (`security` warning):** Equalized unknown-email login latency via precomputed `DUMMY_PASSWORD_HASH` (Argon2).
3. **URL control character rejection (`security` warning):** Rejected ASCII control characters (`\r`, `\n`, `\t`) in `MonitorCreate`/`MonitorUpdate`.
4. **Explicit `null` rejection in `PATCH` (`correctness` + `tests` warning):** Added `@model_validator(mode="before")` on `MonitorUpdate` so explicit `null` returns `422 VALIDATION_ERROR` without bumping `updated_at`.
5. **Infrastructure & schema hygiene (`correctness` + `security` nits):** Preserved `exc.headers` in `StarletteHTTPException` handler; aligned `Monitor` `server_default` with Alembic migration; escaped `%` in `alembic/env.py`; bound PostgreSQL port to `127.0.0.1` in `docker-compose.yml`.
6. **Full AC test coverage (`tests` blockers + warnings + nits):** Parametrized JWT protection across all 5 `/monitors` endpoints, tested orphan/wrong-secret JWTs, added full `PATCH` validation and bounds tests, verified JWT claims and exact `{"detail", "code"}` 422 envelope, and inspected Alembic columns/indexes/FK `CASCADE`.

## Constitution & REVIEW.md Gate Check

- [x] Reversible Alembic migration (`upgrade` + `downgrade` verified).
- [x] Protected endpoints enforce JWT and strict per-user isolation (`404 MONITOR_NOT_FOUND`).
- [x] Zero secrets committed (`.env` gitignored, `.env.example` placeholder only).
- [x] Strict TDD with `pytest` (18/18 pass, 94.03% coverage >= 80%).
- [x] Zero errors/warnings in `ruff check`, `ruff format --check`, and `mypy` (strict).
- [x] English no-emoji Conventional Commits and human git authorship.
- [x] Decision logged in `02-DOCS/wiki/sdd/decisions.md` and Decision queue closed.
- [x] Tier 2 human approval required on GitHub PR #4 (no auto-merge).
