# AI Documentation Gap Finder — ARCH.md

## 1) System Overview
A multi-tenant service that continuously scans code + docs, aligns entities ↔ anchors, detects drift/gaps, scores clarity, auto-drafts MDX, and opens PRs. Core building blocks:
- **Frontend/BFF**: Next.js 14 (App Router) on Vercel.
- **API Gateway**: NestJS (Node 20) — REST /v1, Zod validation, RBAC (Casbin), RLS, Problem+JSON, Idempotency-Key, Request-ID (ULID).
- **Workers** (Python 3.11 + FastAPI controllers): clone, scan-code, scan-docs, map, diff, score, draft, export.
- **Event bus**: NATS (topic per stage) + Redis Streams (progress/checkpoints).
- **Data**: Postgres 16 + pgvector; S3 for artifacts; Redis cache; optional OpenSearch (full-text) & Neo4j (traceability graph).
- **Observability**: OpenTelemetry traces/metrics/logs → Prometheus/Grafana; Sentry for errors.
- **Security**: SSO (SAML/OIDC), KMS-wrapped secrets, signed PR keys, least-privilege repo tokens.

## 2) High‑Level Data Flow
```mermaid
flowchart LR
  A[Connect repos] --> B[clone-worker]
  B --> C[scan-code-worker]
  B --> D[scan-docs-worker]
  C --> E[map-worker]
  D --> E
  E --> F[diff-worker (drift, broken links, snippet exec)]
  F --> G[score-worker (clarity & priority)]
  G --> H[draft-worker (MDX auto-drafts)]
  H --> I[export-worker (PR/JSON/PDF)]
  subgraph Stores
    P[(Postgres+pgvector)]
    S[(S3 Artifacts)]
    R[(Redis)]
  end
  C --> P
  D --> P
  E --> P
  F --> P
  G --> P
  H --> S
  I --> S
```

## 3) Key Pipelines
- **Clone & Scan**
  - Sparse clone with depth=1 by default; LFS support for images/screens.
  - Code scanning: parsers per language (TS/JS via TS compiler API, Python via `libcst`/`ast`, Go via `go/parser`, Java via JavaParser), OpenAPI/GraphQL spec ingestion, CLI parsers (Cobra/Click/Commander).
  - Docs scanning: MD/MDX → remark/rehype AST; capture headings/anchors/link graph; extract code blocks for snippet runner.
- **Alignment**
  - Hybrid matching: pgvector embeddings + heuristics (names, paths, signatures, tags).
  - Build **mappings** (entity_id ↔ doc_id@anchor) with confidence; store relation type (describes/references/mentions).
- **Drift & Gap Detection**
  - OpenAPI/GraphQL diff by version; param/enum/schema drift flagged.
  - Broken link checker with throttling/cache.
  - Snippet runner executes examples in sandbox (language toolchain images), compares outputs to expected (or compiles for type-check).
- **Scoring**
  - Clarity metrics (Flesch, layout heuristics), completeness (entities mapped), freshness (last_updated vs release cadence), example density.
  - Priority = (usage/telemetry) × severity × recency.
- **Drafting**
  - MDX skeletons (frontmatter, intro, quickstart, reference, troubleshoot).
  - Auto tables for signatures, params, flags/env vars.
  - Request/response examples from OpenAPI/GraphQL; language tabs.
  - Mermaid diagrams from call graphs; config matrices from flags/env.
  - Lints (remark, ESLint), snippet tests, link checker.
- **Export**
  - PR to docs repo; commits grouped per area; JSON/PDF bundle with findings, mappings, drafts.

## 4) Storage Schema (condensed)
- **entities**(… embedding VECTOR(1536)) — functions/classes/endpoints/cli/flags/env/types.
- **docs**(… embedding VECTOR(1536)) — page path/title/headings/links/timestamps.
- **mappings** — entity↔doc@anchor with score & relation.
- **gaps** — type/severity/priority/reason/status.
- **scores** — clarity/completeness/freshness/example_density.
- **drafts** — mdx + rationale + provenance; status (pending/approved).
- **exports** — bundles & PR URLs.
- All tables scoped by **project_id** with **RLS** enabled.

## 5) API Surface (v1)
- `POST /projects {name, code_repo, docs_repo, default_branch}`
- `POST /projects/:id/scan {mode: full|delta, since?}`
- `GET /gaps?project_id=&type=&severity=&status=`
- `POST /drafts/generate {project_id, entity_id?, doc_id?, type}`
- `POST /drafts/:id/approve`
- `POST /exports/pr {project_id, branch, title}`
- `POST /exports/bundle {project_id, format}`
- `GET /search?project_id=&q=` — hybrid RAG (entities + docs w/ anchors).

## 6) Runtime & Scaling
- **Workers** autoscale by NATS queue depth; each stage idempotent with task ack/retry & DLQ.
- **Parallelism**: per-project queues to avoid head-of-line blocking; shard by repo path for monorepos.
- **Caching**: Redis for hot embeddings & link-check results; S3 for rendered previews.
- **SLO Targets** (p95): full scan 10m (250k LoC + 1k MDX), delta 90s, draft 8s, PR 30s.

## 7) Security & Compliance
- OAuth app with minimal scopes (repo:read, PR:write on docs repo only).
- KMS-wrapped secrets; short-lived tokens; no plaintext storage.
- Private symbols default; publishing whitelist required.
- Immutable audit trail; retention controls; DSR endpoints.
- Network egress deny by default for snippet runner; allowlist when needed.

## 8) Observability
- **OTel** spans across: repo.clone, code.scan, docs.scan, align.map, delta.diff, score.rank, draft.make, export.make.
- Metrics: scan latency, mapper precision@1 (sampled), draft lint/test pass rate, PR success rate.
- Sentry errors mapped to task + project, with replay breadcrumbs.

## 9) Frontend Composition
- Next.js server components for heavy views (DriftDiff render, Graph), client components for interactive editors.
- State: TanStack Query + Zod schemas; optimistic UI for draft edits.
- Components: GapTable, DriftDiff, DraftStudio (MDX editor & preview), TraceGraph (Cytoscape), ExportWizard.

## 10) Threat Model Notes
- **Repo token misuse**: scoped tokens; project-level vault; per-request Request-ID; anomaly alerts.
- **Private data leak**: classification on entities; draft validator blocks external PR unless visibility=public.
- **RCE via snippets**: sandboxed containers, resource limits, no host mounts, no default outbound net.

## 11) Local Dev
- `docker compose up db redis nats minio`
- `pnpm dev` (web), `pnpm start:api` (NestJS), `make worker` (uvicorn workers)
- Seed script creates demo project, synthetic repo & docs, and sample gaps.
