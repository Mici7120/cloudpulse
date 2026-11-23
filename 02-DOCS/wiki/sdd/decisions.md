---
type: decisions
title: CloudPulse — Architectural & Process Decisions
description: Append-only log of significant architectural and process decisions for CloudPulse (Constitution Principle 18).
tags: [sdd, decisions]
timestamp: 2026-11-23T07:49:00Z
topic: sdd
status: active
---

# CloudPulse — Decisions Log

## 2026-11-23 — SSRF policy for monitor URLs (Milestone 1 vs Milestone 2)

- **Context:** During the Tier 2 security review of Milestone 1 (`01-auth-and-monitors`), the security refuter flagged that `MonitorCreate`/`MonitorUpdate` accept loopback, RFC1918, and link-local IP literals (`127.0.0.1`, `169.254.169.254`, `localhost`). Milestone 1 only stores monitor definitions and makes zero outbound HTTP requests.
- **Options considered:**
  1. Block private/loopback/metadata IP literals immediately at `POST/PATCH /monitors` ingestion in Milestone 1.
  2. Keep Milestone 1 ingestion open (while enforcing `http`/`https` schemes and rejecting ASCII control characters) and enforce post-DNS-resolution IP filtering in Milestone 2's ping worker with an explicit `ALLOW_PRIVATE_MONITOR_URLS=false` default flag.
- **Decision:** Adopt **Option 2**. Milestone 1 stays without private/loopback blocking at ingestion; Milestone 2's worker will enforce post-DNS IP range filtering with `ALLOW_PRIVATE_MONITOR_URLS=false` by default.
- **Rationale:** Real SSRF protection requires post-DNS-resolution IP validation anyway (to prevent DNS rebinding), and Milestone 1 has no outbound HTTP client. Deferring the restriction to Milestone 2 avoids breaking local development/test monitor URLs while guaranteeing secure-by-default enforcement before the first outbound request is ever made.
