-- AI Documentation Gap Finder Database Initialization
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Tenancy tables
CREATE TABLE orgs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    plan TEXT DEFAULT 'pro',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES orgs(id) ON DELETE CASCADE,
    email CITEXT UNIQUE NOT NULL,
    role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    tz TEXT DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Projects/Repos
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES orgs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    code_repo TEXT,
    docs_repo TEXT,
    default_branch TEXT DEFAULT 'main',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Code Entities
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('function', 'class', 'endpoint', 'cli', 'flag', 'env', 'type')),
    name TEXT NOT NULL,
    path TEXT,
    lang TEXT,
    signature JSONB,
    spec JSONB,
    visibility TEXT DEFAULT 'private' CHECK (visibility IN ('public', 'private', 'internal')),
    version TEXT,
    embedding VECTOR(1536),
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create HNSW index for vector similarity search
CREATE INDEX ON entities USING hnsw (embedding vector_cosine_ops);

-- Docs
CREATE TABLE docs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    title TEXT,
    headings JSONB DEFAULT '[]',
    links JSONB DEFAULT '[]',
    last_commit TEXT,
    last_updated TIMESTAMPTZ DEFAULT now(),
    frontmatter JSONB DEFAULT '{}',
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Alignment & Traceability
CREATE TABLE mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    doc_id UUID REFERENCES docs(id) ON DELETE CASCADE,
    anchor TEXT,
    score NUMERIC CHECK (score >= 0 AND score <= 1),
    relation TEXT CHECK (relation IN ('describes', 'references', 'mentions')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Gaps & Scores
CREATE TABLE gaps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('missing', 'partial', 'stale', 'broken_link', 'incorrect_sample', 'orphan_doc', 'outdated_screenshot')),
    entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
    doc_id UUID REFERENCES docs(id) ON DELETE SET NULL,
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    priority NUMERIC DEFAULT 0,
    reason TEXT,
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'investigating', 'resolved', 'wont_fix')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    doc_id UUID REFERENCES docs(id) ON DELETE CASCADE,
    clarity NUMERIC CHECK (clarity >= 0 AND clarity <= 1),
    completeness NUMERIC CHECK (completeness >= 0 AND completeness <= 1),
    freshness NUMERIC CHECK (freshness >= 0 AND freshness <= 1),
    example_density NUMERIC CHECK (example_density >= 0 AND example_density <= 1),
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Drafts & Exports
CREATE TABLE drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    doc_id UUID REFERENCES docs(id) ON DELETE SET NULL,
    entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
    mdx TEXT,
    rationale JSONB DEFAULT '{}',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'merged')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('pr', 'bundle')),
    s3_key TEXT,
    pr_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Audit
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    org_id UUID REFERENCES orgs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    target TEXT,
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable Row Level Security (RLS)
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE docs ENABLE ROW LEVEL SECURITY;
ALTER TABLE mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE gaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Create indexes for performance
CREATE INDEX idx_entities_project_kind ON entities(project_id, kind);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_docs_project_path ON docs(project_id, path);
CREATE INDEX idx_mappings_project ON mappings(project_id);
CREATE INDEX idx_mappings_entity ON mappings(entity_id);
CREATE INDEX idx_mappings_doc ON mappings(doc_id);
CREATE INDEX idx_gaps_project_status ON gaps(project_id, status);
CREATE INDEX idx_drafts_project_status ON drafts(project_id, status);
CREATE INDEX idx_audit_org_created ON audit_log(org_id, created_at DESC);

-- Insert demo data for development
INSERT INTO orgs (id, name) VALUES ('550e8400-e29b-41d4-a716-446655440000', 'Demo Organization');

INSERT INTO users (id, org_id, email, role) VALUES
('550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 'admin@demo.com', 'admin'),
('550e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'user@demo.com', 'member');

INSERT INTO projects (id, org_id, name, code_repo, docs_repo) VALUES
('550e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440000', 'Demo Project', 'https://github.com/demo/repo', 'https://github.com/demo/docs');
