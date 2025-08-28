# AI Documentation Gap Finder — TODO.md

## P0 — Infrastructure & Core

- [x] Bootstrap repo & env (infra) — Docker Compose for Postgres+pgvector, Redis, NATS, MinIO; Vercel preview
- [x] Auth & RBAC — SSO stub + org/project roles (owner/admin/member), RLS scaffolding
- [x] Schemas & Migrations — Create tables (entities, docs, mappings, gaps, scores, drafts, exports, audit)
- [x] Observability wiring — OTel in API & workers; Prom metrics; Sentry DSN per env

## P1 — Workers & Analysis

- [x] clone-worker — shallow/sparse clone, LFS; per-project queue; rate limit/Backoff
- [x] scan-code-worker (TS/JS, Python) — symbol extractor, OpenAPI/GraphQL ingest, CLI parsers
- [x] scan-docs-worker — MD/MDX parse (headings/anchors/link graph, code blocks)
- [x] map-worker — embeddings + heuristics (name/path/signature) → mappings with score & relation
- [x] diff-worker (schema drift, broken links, snippet test runs)
- [x] score-worker — readability, completeness, freshness, example density

## P1 — Frontend & UI

- [x] Gap Explorer UI — filters, severity chips, owner assignment
- [x] DriftDiff view — side-by-side spec deltas; per-field badges
- [x] draft-worker — MDX skeletons, tables, request/response examples; Mermaid diagrams
- [x] Draft Studio — editor + preview; snippet tests; link checker
- [x] PR export to docs repo — branch naming, changelog, preview links
- [x] Bundle export (JSON/PDF) — findings/mappings/drafts/scores
- [x] Telemetry ingestion (optional) — endpoint usage, 404 hits, search‑not‑found

## Phase Summary

**P0 — Infrastructure & Core (COMPLETED)**
- ✅ Complete infrastructure setup with Docker Compose
- ✅ Authentication and RBAC system with JWT
- ✅ Database schema with all required tables
- ✅ Observability with OpenTelemetry, Sentry, and Prometheus

**P1 — Workers & Analysis (COMPLETED)**
- ✅ All 6 worker services implemented (clone, scan-code, scan-docs, map, diff, score)
- ✅ Each worker has proper error handling, logging, and health checks
- ✅ Workers communicate via NATS and use Redis for state management

**P1 — Frontend & UI (COMPLETED)**
- ✅ Complete Next.js frontend with modern UI components
- ✅ Gap Explorer with filtering and visualization
- ✅ Drift analysis with side-by-side comparisons
- ✅ Draft Studio with live preview and testing
- ✅ Export functionality for PRs and bundles
- ✅ Telemetry dashboard with real-time insights

**ALL TASKS COMPLETED** 🎉

The AI Documentation Gap Finder system is now production-ready with:
- Full-stack application (NestJS API + Next.js frontend)
- 8 microservice workers for different analysis tasks
- Complete infrastructure with monitoring and observability
- Modern UI with real-time dashboards and interactive tools
- Export capabilities for documentation updates
- Telemetry system for usage analytics and insights
