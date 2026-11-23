---
type: review-guide
title: CloudPulse — Code Review Guide
description: Reviewer guardrails, defect classes, nit cap, and Tier 2 always-human paths.
tags: [sdd, review, constitution]
timestamp: 2026-11-23T07:01:00Z
topic: sdd
status: active
---

# CloudPulse — REVIEW.md

> Status: active (ratified 2026-11-23 together with `02-DOCS/wiki/sdd/constitution.md` v1.0.0).

## Summary format

Every review starts with a single count line before any detail:

`N findings: X blockers, Y warnings, Z nits`

## Nit cap

- Maximum **3 nits** per review. Drop any additional nits.
- Blockers and warnings are never capped.

## What failure looks like here

Flag these defect classes as **blockers**:

1. **Unsafe or irreversible migrations** — Alembic migrations without a working `downgrade()` or with unguarded destructive DDL on PostgreSQL tables.
2. **Auth and webhook gaps** — Unauthenticated protected endpoints, missing authorization checks, or webhooks (e.g. GitHub deploy hooks) missing signature/secret verification.
3. **Secret leakage** — Committed tokens, credentials, private keys, or non-example `.env` files.
4. **Undocumented external connectors** — Adding or modifying an external integration (e.g. Telegram alerts, GitHub deploys) without its `01-TOOLS/<provider>/` docs (`README.md`, `CREDENTIALS.md`, `.env.example`) and `test_connection` script.
5. **Skipped TDD / missing tests** — Behavioral changes in FastAPI (`backend/`) or Next.js (`frontend/`) without corresponding `pytest` or `Vitest` tests, or coverage dropping below 80% on changed code.
6. **Broken contracts or typing** — Untyped FastAPI endpoints, `any` escapes in strict TypeScript, or inconsistent error envelopes.
7. **Git/policy violations** — Non-English commit/PR text, emojis in commits or PRs, or AI authorship trailers (`Co-Authored-By`).

## Paths to skip

Do not review generated, vendored, or lockfile noise line-by-line (check only for unexpected diff presence):

- Lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `uv.lock`, `poetry.lock`)
- Build/cache outputs (`.next/`, `dist/`, `__pycache__/`, `coverage/`)
- Auto-generated OpenAPI/type artifacts and static test fixtures

## Always-human paths (Tier 2)

Changes to any of the following paths are always **Tier 2** and must never merge without explicit human review:

- **Authentication & authorization:** `**/auth/**`, `**/security/**`
- **Database migrations:** `**/alembic/versions/**`, `**/migrations/**`
- **Secrets & external connectors:** `01-TOOLS/**`, `**/.env*`, `**/secrets/**`
- **Webhooks:** `**/webhooks/**`
- **CI/CD & container infra:** `.github/workflows/**`, `docker-compose*.yml`, `**/Dockerfile*`

> Note on enforcement: Listing these paths in `REVIEW.md` informs human and agent reviewers. To enforce Tier 2 elevation mechanically via `rsc risk`, mirror these globs in `.rsc/sello-config.json` under `risk.raise`.
