# AI Documentation Gap Finder — PLAN.md

## One-liner
Continuously compare your codebase and APIs against your docs to surface what’s missing, outdated, or confusing—then generate fix-ready doc drafts.

## Goals (v1)
- **Detect gaps** between code & docs: missing/partial/stale/incorrect samples, undocumented endpoints/flags/env vars, orphaned docs.
- **Score clarity** (readability, completeness, freshness, example density) and prioritize by user impact.
- **Auto-draft** MD/MDX patches with provenance and runnable examples.
- **Traceability graph**: code ↔ docs ↔ issues/PRs ↔ changelog.
- **Exports**: PRs to docs repo + JSON bundle; guardrails (lint, link checker, owner approval).

## Non‑Goals (v1)
- Public docs publishing & site theming.
- Auto-merge without human review.
- Live, destructive edits in source repos outside PRs.

## Key Users & Jobs
- **DX/Docs teams**: keep docs accurate & clear; accept auto-drafts quickly.
- **Backend/Frontend teams**: ship features with docs tasks on merge.
- **Platform/Infra**: maintain internal runbooks & service docs.
- **PM/Support**: see gaps that generate tickets.

## Success Metrics (align to brief)
- Doc coverage +30 pp in 60 days.
- Mean doc freshness −40% vs release cadence.
- Support tickets tied to docs −25%.
- Auto-draft PR acceptance ≥ 70%.
- Pipeline success ≥ 99% (excl. repo outages); draft lint/test pass ≥ 95%; mapping P@1 ≥ 0.9.

## 12‑Week Delivery Plan
**Phase 0 · Week 1–2 · Foundations**
- Repo connectors (GitHub/GitLab) read-only.
- Postgres + pgvector schema; NATS, Redis, S3.
- Next.js shell, auth, RBAC (org/workspace/member).
- OpenTelemetry + Grafana/Prom + Sentry.
**Exit**: create project, connect repos, run a no-op scan.

**Phase 1 · Week 3–4 · Scanners**
- Code scanners: TS/JS, Python; OpenAPI & GraphQL parsers; CLI detectors (Cobra/Click).
- Docs scanner: MD/MDX parse (headings/anchors/link graph).
- Artifact store, basic embeddings; hnsw index.
**Exit**: entity/doc indices visible; raw mappings preview.

**Phase 2 · Week 5–6 · Alignment & Drift**
- Embedding+heuristic mapper; traceability edges.
- Schema diff (OpenAPI/GraphQL), broken link checker.
- Snippet runner (containerized) for MDX code blocks.
**Exit**: gaps computed; DriftDiff UI.

**Phase 3 · Week 7–8 · Scoring & Prioritization**
- Clarity metrics: readability, completeness, freshness, example density.
- Priority = usage × drift severity × recency (optional telemetry input).
- Gap Explorer & Clarity Heatmap.
**Exit**: ranked backlog with owners (CODEOWNERS integration).

**Phase 4 · Week 9–10 · Drafting & Studio**
- Draft generator: MDX skeletons, tables, request/response examples, Mermaid diagrams.
- Draft Studio: preview, lint (remark/ESLint), snippet tests, link checker.
**Exit**: reviewers can approve drafts that pass checks.

**Phase 5 · Week 11–12 · PR Export & Hardening**
- PR export to docs repo; JSON/PDF bundle.
- SLA queues, rate limits; DLQ, retries; multi-tenant RLS reviews.
- Security pass (token scopes, private symbol rules), e2e & load tests.
**Exit**: Beta readiness; SLOs: scan p95, delta p95, draft p95, PR p95 as in brief.

## Deliverables
- Running SaaS (dev/stage/prod), Terraform/IaC, CI/CD.
- API v1 (Projects, Scans, Gaps, Drafts, Exports, Search).
- Frontend app with Gap Explorer, DriftDiff, Draft Studio, Graph, Exports.
- Playbook: onboarding, connectors, troubleshooting.

## Risks & Mitigations
- **Mapping precision**: combine embeddings with heuristics (name/path/sig) + threshold & human override.
- **Snippet execution safety**: sandbox containers, no external network by default, time/mem limits.
- **Private symbol leakage**: visibility flags, default-private; PR guardrails.
- **Monorepo scale**: sparse clone, parallel scanners, per-project queues.
- **Flaky link checks**: backoff/retry, cache, mark external 404s as warnings.

## Security & Compliance
- SSO (SAML/OIDC), least-privilege tokens, KMS-wrapped secrets.
- RLS per project; immutable audit; retention & DSR tooling.
- Private-by-default drafting; owner approval required to export.

## Launch Plan
- **Alpha**: 3–5 internal repos; weekly office hours.
- **Closed Beta**: 10 design partners; SLA + support.
- **Public Beta**: gated self-serve; usage-based limits.

## Pricing/Packaging (placeholder)
- Team (up to N repos), Pro (monorepo + telemetry), Enterprise (SSO, on-prem runner, private VPC).
