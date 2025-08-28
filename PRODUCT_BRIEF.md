AI Documentation Gap Finder — detect missing/unclear docs by comparing codebase vs existing docs 

 

1) Product Description & Presentation 

One-liner 

“Continuously compare your codebase and APIs against your docs to surface what’s missing, outdated, or confusing—then generate fix-ready doc drafts.” 

What it produces 

Gap reports: missing topics, stale examples, undocumented endpoints/flags/env vars, orphaned docs. 

Clarity scores: per page/repo area (readability, completeness, recency, example coverage). 

Auto-drafts: suggested sections, code examples, tables, diagrams, and API reference deltas. 

Traceability graph: code ↔ docs ↔ issues/PRs ↔ changelog. 

Exports: Markdown/MDX patches, PRs to docs repo, JSON bundle (findings, mappings, suggested fixes). 

Scope/Safety 

Read-only by default; write access only for PR creation with explicit scopes. 

Keeps private symbols/classified endpoints out of public drafts unless whitelisted. 

Human-in-the-loop review for all auto-drafted docs. 

 

2) Target User 

Developer Experience (DX) & Docs teams maintaining product/API documentation. 

Backend/frontend teams shipping features that need docs on merge. 

Platform teams standardizing internal runbooks and service docs. 

PMs/Support needing visibility into doc gaps that cause tickets. 

 

3) Features & Functionalities (Extensive) 

Code & Artifact Ingestion 

Connect repos (GitHub/GitLab/Bitbucket), monorepos, packages; parse build files and CI. 

Parse source (TypeScript/JS, Python, Go, Java, Ruby), OpenAPI/GraphQL specs, CLIs (Cobra/Click, Commander), config (env vars, flags), examples and snippets. 

Ingest docs (Markdown/MDX, Docusaurus/Next.js content, Sphinx/Jekyll), changelogs, ADR, release notes, issues/PRs. 

Optional telemetry hints: endpoint usage, 404 docs hits, most-searched-but-not-found queries. 

Mapping & Alignment 

Build symbol maps: functions, classes, endpoints, CLI commands, feature flags, env vars → Doc anchors (headings, tags). 

Detect undocumented code entities and unreferenced docs. 

Schema diff: OpenAPI/GraphQL changes vs doc pages; param/enum drift. 

Example sync: ensure runnable snippets match SDK versions; test snippets in sandbox. 

Gap Detection & Scoring 

Gap types: Missing Page, Partial Coverage, Stale Version, Broken Link, Incorrect Sample, Orphan Doc, Outdated Screenshot. 

Clarity: readability (Flesch, layout heuristics), discoverability (internal links), example density, last-updated vs release cadence. 

Priority score = user impact (usage/telemetry) × drift severity × recency. 

Auto-Drafting & Fixes 

Generate doc skeletons (intro, quickstart, reference, troubleshoot). 

Convert function signatures and types to tables; create request/response examples. 

Suggest diagrams (Mermaid) from call graphs; config matrices from flags/env. 

Produce PR-ready Markdown/MDX with frontmatter, links, and snippet blocks. 

Workflows & Governance 

Watch branches/tags; create Doc Tasks at PR merge or spec change. 

Review queues, SLA targets, ownership (CODEOWNERS). 

Exceptions/waivers (e.g., internal-only API). 

Comment back to engineering PRs when docs required. 

Views & Reporting 

Gap Explorer: filters by product/area/type/severity. 

Clarity Dashboard: heatmaps across doc sections. 

Drift Timeline: when drift started, related releases. 

Auto-draft Studio: side-by-side suggested MDX + preview with lint checks. 

 

4) Backend Architecture (Extremely Detailed & Deployment-Ready) 

4.1 Topology 

Frontend/BFF: Next.js 14 (App Router) on Vercel; Server Actions for uploads/PR signing; SSR for dashboards; ISR for share links. 

API Gateway: NestJS (Node 20) — REST /v1, OpenAPI 3.1, Zod validation, Problem+JSON, RBAC (Casbin), Row-Level Security (RLS), Idempotency-Key, Request-ID (ULID). 

Workers (Python 3.11 + FastAPI control) 

clone-worker (git clone/sparse, LFS) 

scan-code-worker (AST, symbol extraction, spec parse, CLI parse) 

scan-docs-worker (MD/MDX parse, anchors, link graph) 

map-worker (code↔doc alignment using embeddings + heuristics) 

diff-worker (schema drift, snippet test runs, broken links) 

score-worker (priority & clarity scoring) 

draft-worker (auto-draft MDX, examples, diagrams) 

export-worker (PRs, bundles, PDFs) 

Event bus: NATS topics (repo.clone, code.scan, docs.scan, align.map, delta.diff, score.rank, draft.make, export.make) + Redis Streams for progress. 

Execution: containerized analysis (node, py, go, java toolchains); headless browser for doc previews. 

Data 

Postgres 16 + pgvector (entities, mappings, gaps, drafts, embeddings). 

S3/R2 (artifacts, rendered previews, exports). 

Redis (cache, job state). 

Optional: OpenSearch (full-text) and Neo4j (traceability graph). 

Observability: OpenTelemetry (traces/metrics/logs), Prometheus/Grafana, Sentry. 

Secrets: KMS; per-repo tokens; signed PR keys. 

4.2 Data Model (Postgres + pgvector) 

-- Tenancy 
CREATE TABLE orgs (id UUID PRIMARY KEY, name TEXT, plan TEXT DEFAULT 'pro', created_at TIMESTAMPTZ DEFAULT now()); 
CREATE TABLE users (id UUID PRIMARY KEY, org_id UUID, email CITEXT UNIQUE, role TEXT DEFAULT 'member', tz TEXT); 
 
-- Projects/Repos 
CREATE TABLE projects (id UUID PRIMARY KEY, org_id UUID, name TEXT, code_repo TEXT, docs_repo TEXT, default_branch TEXT, created_at TIMESTAMPTZ DEFAULT now()); 
 
-- Code Entities 
CREATE TABLE entities ( 
  id UUID PRIMARY KEY, project_id UUID, kind TEXT,                 -- function|class|endpoint|cli|flag|env|type 
  name TEXT, path TEXT, lang TEXT, signature JSONB, spec JSONB, visibility TEXT, version TEXT, 
  embedding VECTOR(1536), meta JSONB 
); 
CREATE INDEX ON entities USING hnsw (embedding vector_cosine_ops); 
 
-- Docs 
CREATE TABLE docs ( 
  id UUID PRIMARY KEY, project_id UUID, path TEXT, title TEXT, headings JSONB, links JSONB, 
  last_commit TEXT, last_updated TIMESTAMPTZ, frontmatter JSONB, embedding VECTOR(1536) 
); 
 
-- Alignment & Traceability 
CREATE TABLE mappings ( 
  id UUID PRIMARY KEY, project_id UUID, entity_id UUID, doc_id UUID, anchor TEXT, score NUMERIC, relation TEXT -- describes|references|mentions 
); 
 
-- Gaps & Scores 
CREATE TABLE gaps ( 
  id UUID PRIMARY KEY, project_id UUID, type TEXT, entity_id UUID, doc_id UUID, 
  severity TEXT, priority NUMERIC, reason TEXT, created_at TIMESTAMPTZ DEFAULT now(), status TEXT 
); 
 
CREATE TABLE scores ( 
  id UUID PRIMARY KEY, project_id UUID, doc_id UUID, clarity NUMERIC, completeness NUMERIC, freshness NUMERIC, example_density NUMERIC, meta JSONB 
); 
 
-- Drafts & Exports 
CREATE TABLE drafts (id UUID PRIMARY KEY, project_id UUID, doc_id UUID, entity_id UUID, mdx TEXT, rationale JSONB, status TEXT, created_at TIMESTAMPTZ DEFAULT now()); 
CREATE TABLE exports (id UUID PRIMARY KEY, project_id UUID, kind TEXT, s3_key TEXT, pr_url TEXT, created_at TIMESTAMPTZ DEFAULT now()); 
 
-- Audit 
CREATE TABLE audit_log (id BIGSERIAL PRIMARY KEY, org_id UUID, user_id UUID, action TEXT, target TEXT, meta JSONB, created_at TIMESTAMPTZ DEFAULT now()); 
  

Invariants 

RLS by project_id. 

A gap references at least one entity or doc. 

Each draft stores provenance: code signatures, spec diffs, and example generation inputs. 

PR exports only after passing lint & link checks and owner approval. 

4.3 API Surface (REST /v1) 

Projects/Repos 

POST /projects {name, code_repo, docs_repo, default_branch} 

POST /projects/:id/scan (full or delta) 

Findings 

GET /gaps?project_id=&type=&severity=&status= 

GET /scores?project_id=&doc_id= 

GET /mappings?project_id=&entity_id= 

Drafting 

POST /drafts/generate {project_id, entity_id?, doc_id?, type:"missing|stale|example"} 

GET /drafts/:id 

POST /drafts/:id/approve 

Exports 

POST /exports/pr {project_id, branch, title} 

POST /exports/bundle {project_id, format:"json|pdf"} 

Search (RAG) 

GET /search?project_id=UUID&q="webhook signature" (entities + docs with anchors) 

Conventions 

Idempotency-Key for mutations; Problem+JSON errors; SSE /tasks/:id/stream for long jobs. 

4.4 Pipelines 

Clone & Scan: code & docs → parse AST/specs/MDX → extract entities & anchors. 

Align: embedding + heuristics → map entities to doc anchors; build traceability edges. 

Detect Drift & Gaps: OpenAPI/GraphQL diff; snippet execution; link checker; freshness thresholds. 

Score: compute clarity/completeness/freshness/example density → priority rank. 

Draft: generate content (MDX) with tables, examples, Mermaid diagrams; run linters (remark/ESLint), test snippet execution. 

Export: open PR to docs repo with changes; create JSON/PDF report. 

4.5 Security & Compliance 

SSO (SAML/OIDC), least-privilege repo tokens, KMS-wrapped secrets. 

Private symbols remain private unless explicitly marked publishable. 

Audit trail for all scans, drafts, and PRs; DSR & retention controls. 

 

5) Frontend Architecture (React 18 + Next.js 14 — Looks Matter) 

5.1 Design Language 

shadcn/ui + Tailwind, glassmorphism panels, neon accents, soft depth; dark mode default. 

Framer Motion: animated gap cards, diff reveals, graph zoom/pan inertia. 

Crisp monospace for code, accessible color palettes, and keyboard-first navigation. 

5.2 App Structure 

/app 
  /(marketing)/page.tsx 
  /(auth)/sign-in/page.tsx 
  /(app)/projects/page.tsx 
  /(app)/dashboard/page.tsx 
  /(app)/gaps/page.tsx 
  /(app)/docs/[path]/page.tsx 
  /(app)/drafts/[id]/page.tsx 
  /(app)/graph/page.tsx 
  /(app)/exports/page.tsx 
/components 
  RepoConnect/* 
  ScanControls/*           // full/delta scan controls, progress 
  GapTable/*               // filterable with severity/owner chips 
  GapCard/*                // animated card with rationale & quick actions 
  ClarityHeatmap/*         // per-section heatmaps 
  DriftDiff/*              // OpenAPI/GraphQL diff with colored badges 
  SnippetRunner/*          // run examples, show pass/fail 
  DraftStudio/*            // MDX editor + live preview + lint 
  TraceGraph/*             // Cytoscape graph of code↔docs↔issues 
  ExportWizard/*           // PR or bundle, branch naming 
/store 
  useProjectStore.ts 
  useGapStore.ts 
  useDraftStore.ts 
  useScoreStore.ts 
  useGraphStore.ts 
  useExportStore.ts 
/lib 
  api-client.ts 
  sse-client.ts 
  zod-schemas.ts 
  rbac.ts 
  

5.3 Key UX Flows 

Connect & Scan: add repos → run full/delta scan → shimmering progress with per-stage logs. 

Explore Gaps: Gap Table with severity/area/owner filters; click to open Gap Card with rationale, affected entities, and suggested fix. 

Drift Review: DriftDiff compares OpenAPI/GraphQL/CLI vs docs; inline “Apply draft” CTA. 

Draft Studio: side-by-side MDX + preview; run snippet tests; Mermaid diagram preview; lints & broken-link checks. 

Graph View: interactive traceability graph; hover highlights; quick “open doc” or “open source”. 

Export: select drafts → PR summary auto-composed with change log; confetti on successful PR. 

5.4 Validation & Error Handling 

Zod schemas; Problem+JSON banners with “Fix it” actions (e.g., select owner, set visibility). 

Guards: PR disabled if drafts fail lint, snippet tests, or owner approval missing. 

Link checker runs before publish; warns on external 404s. 

5.5 Accessibility & i18n 

Keyboard shortcuts (G to open Gap search, / to focus search, ]/[ to next/prev gap). 

Screen-reader summaries for heatmaps & graphs; captioned diffs. 

Localized dates & number formats. 

 

6) SDKs & Integration Contracts 

Trigger scan (delta) 

POST /v1/projects/{id}/scan 
{ "mode":"delta", "since":"2025-08-01T00:00:00Z" } 
  

List gaps 

GET /v1/gaps?project_id=UUID&type=missing&severity=high&status=open 
  

Generate a draft 

POST /v1/drafts/generate 
{ "project_id":"UUID", "entity_id":"UUID", "type":"missing" } 
  

Approve & export PR 

POST /v1/drafts/{id}/approve 
POST /v1/exports/pr 
{ "project_id":"UUID", "branch":"docs/add-webhooks", "title":"Docs: Add Webhooks section (auto-draft)" } 
  

Export JSON bundle 

POST /v1/exports/bundle 
{ "project_id":"UUID", "format":"json" } 
  

JSON bundle keys: entities[], docs[], mappings[], gaps[], scores[], drafts[], exports[]. 

 

7) DevOps & Deployment 

FE: Vercel (Next.js). 

APIs/Workers: Render/Fly/GKE; autoscale by queue depth; DLQ with jitter backoff. 

DB: Managed Postgres + pgvector; PITR; read replicas. 

Cache/Bus: Redis + NATS; per-project queues. 

Storage/CDN: S3/R2; CDN for previews. 

CI/CD: GitHub Actions (lint/typecheck/unit/integration, container scan, sign, deploy); blue/green; migration approvals. 

SLOs 

Monorepo scan (250k LoC + 1k MDX pages) < 10 min p95 (parallel). 

Delta scan on PR < 90 s p95. 

Draft generation < 8 s p95 per page. 

PR export < 30 s p95. 

 

8) Testing 

Unit: AST parsers, spec diffing, MD/MDX anchor parsing, link checker, readability metrics. 

Integration: scan → align → detect gaps → draft → lint → PR. 

Golden: fixture repos with known doc drift; assert stable gap detection. 

Snippet tests: run generated examples against mocked/live SDKs. 

Load/Chaos: huge monorepos, flaky git hosts, broken MDX imports; retry/backoff. 

Security: RLS coverage; token scopes; private symbol leakage tests. 

 

9) Success Criteria 

Product KPIs 

Doc coverage (entities mapped to docs) +30 pp in first 60 days. 

Mean doc freshness (days since last change vs release cadence) −40%. 

Support tickets linked to missing/unclear docs −25%. 

PR acceptance of auto-drafts ≥ 70%. 

Engineering SLOs 

Pipeline success ≥ 99% (excl. repo outages). 

Draft lint/test pass rate ≥ 95% before PR. 

Mapping precision@1 ≥ 0.9 on gold sets. 

 

10) Visual/Logical Flows 

A) Connect & Scan 

 Add code + docs repos → full scan → entities & docs indexed. 

B) Align & Detect 

 Embedding + heuristics map entities ↔ anchors → drift/gaps computed → severity & priority scored. 

C) Review & Draft 

 Open gaps → view rationale and affected users → generate MDX draft → run snippet tests & lints. 

D) Approve & Export 

 Owner approves → PR created with commits, changelog, and preview links → track merge status. 

E) Observe & Improve 

 Clarity dashboard & heatmaps track progress → regressions flagged on new releases → continuous doc hygiene. 

 

 