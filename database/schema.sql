-- Research Commons PostgreSQL Schema (with pgvector support)
-- Chanakya University Mini-Project: Data Mining and Warehousing
-- Module: Database & Backend (Mokshith)

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 1. USERS & SOCIAL GRAPH
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(150) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255),
    role            VARCHAR(32) NOT NULL DEFAULT 'student'
                    CHECK (role IN ('student', 'faculty', 'researcher', 'admin')),
    department      VARCHAR(120) NOT NULL,
    bio             TEXT DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_department ON users (department);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

CREATE TABLE IF NOT EXISTS user_interests (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tag             VARCHAR(100) NOT NULL,
    UNIQUE (user_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_user_interests_user_id ON user_interests (user_id);
CREATE INDEX IF NOT EXISTS idx_user_interests_tag ON user_interests (tag);

CREATE TABLE IF NOT EXISTS follows (
    id              SERIAL PRIMARY KEY,
    follower_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (follower_id, following_id),
    CHECK (follower_id <> following_id)
);

CREATE INDEX IF NOT EXISTS idx_follows_follower_id ON follows (follower_id);
CREATE INDEX IF NOT EXISTS idx_follows_following_id ON follows (following_id);

-- ============================================================
-- 2. ACADEMIC PAPERS & CITATION GRAPH
-- ============================================================

CREATE TABLE IF NOT EXISTS papers (
    id                  VARCHAR(128) PRIMARY KEY,
    title               TEXT NOT NULL,
    abstract            TEXT DEFAULT '',
    authors             JSONB NOT NULL DEFAULT '[]'::jsonb,
    doi                 VARCHAR(255),
    arxiv_id            VARCHAR(128),
    source              VARCHAR(64) NOT NULL DEFAULT 'openalex',
    publication_year    INTEGER,
    citation_count      INTEGER NOT NULL DEFAULT 0,
    concepts            JSONB NOT NULL DEFAULT '[]'::jsonb,
    embedding           VECTOR(384),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers (doi) WHERE doi IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_papers_arxiv_id ON papers (arxiv_id) WHERE arxiv_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_papers_pub_year ON papers (publication_year);
CREATE INDEX IF NOT EXISTS idx_papers_citation_count ON papers (citation_count DESC);
CREATE INDEX IF NOT EXISTS idx_papers_authors_gin ON papers USING GIN (authors);
CREATE INDEX IF NOT EXISTS idx_papers_concepts_gin ON papers USING GIN (concepts);
CREATE INDEX IF NOT EXISTS idx_papers_embedding_hnsw
    ON papers USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS paper_citations (
    id              SERIAL PRIMARY KEY,
    paper_id        VARCHAR(128) NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    cited_paper_id  VARCHAR(128) NOT NULL,
    UNIQUE (paper_id, cited_paper_id)
);

CREATE INDEX IF NOT EXISTS idx_paper_citations_paper_id ON paper_citations (paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_citations_cited_paper_id ON paper_citations (cited_paper_id);

-- ============================================================
-- 3. PERSONAL RESEARCH LIBRARY / BOOKMARKS
-- ============================================================

CREATE TABLE IF NOT EXISTS library (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paper_id        VARCHAR(128) NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    notes           TEXT DEFAULT '',
    collection_name VARCHAR(120) NOT NULL DEFAULT 'General',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, paper_id, collection_name)
);

CREATE INDEX IF NOT EXISTS idx_library_user_id ON library (user_id);
CREATE INDEX IF NOT EXISTS idx_library_paper_id ON library (paper_id);
CREATE INDEX IF NOT EXISTS idx_library_collection ON library (collection_name);

-- ============================================================
-- 4. COMMUNITY POSTS & DISCUSSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS posts (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title               VARCHAR(300) NOT NULL,
    content             TEXT NOT NULL,
    tags                JSONB NOT NULL DEFAULT '[]'::jsonb,
    attached_paper_id   VARCHAR(128) REFERENCES papers(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts (user_id);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_attached_paper ON posts (attached_paper_id);
CREATE INDEX IF NOT EXISTS idx_posts_tags_gin ON posts USING GIN (tags);

CREATE TABLE IF NOT EXISTS comments (
    id              SERIAL PRIMARY KEY,
    post_id         INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments (post_id);
CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments (user_id);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments (created_at);

-- ============================================================
-- 5. ACTIVITY EVENTS (TRENDS, SPAM DETECTION & OLAP ANALYTICS)
-- ============================================================

CREATE TABLE IF NOT EXISTS activity_events (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type      VARCHAR(32) NOT NULL
                    CHECK (event_type IN ('view', 'save', 'search')),
    target_id       VARCHAR(128),
    query_text      TEXT,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_user_id ON activity_events (user_id);
CREATE INDEX IF NOT EXISTS idx_activity_event_type ON activity_events (event_type);
CREATE INDEX IF NOT EXISTS idx_activity_target_id ON activity_events (target_id);
CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_events (timestamp DESC);
