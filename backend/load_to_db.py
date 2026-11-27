"""
Load harvested OpenAlex papers, citation links, and synthetic community data
into PostgreSQL (with pgvector schema).

Usage:
    python backend/load_to_db.py
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
PAPERS_PATH = BASE_DIR / "data" / "processed" / "papers.json"
SYNTHETIC_PATH = BASE_DIR / "data" / "synthetic" / "synthetic_data.json"


def _load_env() -> None:
    env_path = BACKEND_DIR / ".env"
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_path)
    except ImportError:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


_load_env()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/research_commons",
)

SERIAL_TABLES = [
    "users",
    "user_interests",
    "follows",
    "paper_citations",
    "library",
    "posts",
    "comments",
    "activity_events",
]


def ensure_schema(cur: Any) -> None:
    """Execute database/schema.sql if core tables do not yet exist."""
    cur.execute(
        "SELECT to_regclass('public.users') IS NOT NULL "
        "AND to_regclass('public.papers') IS NOT NULL "
        "AND to_regclass('public.activity_events') IS NOT NULL;"
    )
    exists = cur.fetchone()[0]
    if not exists:
        if not SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        cur.execute(schema_sql)
        print(f"Applied schema from {SCHEMA_PATH}")
    else:
        print("Database schema already exists; skipping DDL.")


def load_papers(cur: Any) -> int:
    if not PAPERS_PATH.exists():
        raise FileNotFoundError(f"{PAPERS_PATH} not found. Run backend/fetch_papers.py first.")

    raw_papers = json.loads(PAPERS_PATH.read_text(encoding="utf-8"))
    papers = raw_papers if isinstance(raw_papers, list) else raw_papers.get("papers", [])

    paper_rows = [
        (
            str(p["id"]),
            p.get("title", ""),
            p.get("abstract", ""),
            json.dumps(p.get("authors") or []),
            p.get("doi"),
            p.get("arxiv_id"),
            p.get("source", "openalex"),
            p.get("publication_year"),
            int(p.get("citation_count") or 0),
            json.dumps(p.get("concepts") or []),
            p.get("created_at"),
        )
        for p in papers
    ]

    execute_values(
        cur,
        """
        INSERT INTO papers (
            id, title, abstract, authors, doi, arxiv_id, source,
            publication_year, citation_count, concepts, created_at
        )
        VALUES %s
        ON CONFLICT (id) DO NOTHING
        """,
        paper_rows,
        template="(%s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s::jsonb, COALESCE(%s::timestamptz, NOW()))",
        page_size=500,
    )

    citation_pairs: set[tuple[str, str]] = set()
    for p in papers:
        pid = str(p["id"])
        for ref in p.get("referenced_works") or []:
            ref_id = str(ref).strip()
            if ref_id and ref_id != pid:
                citation_pairs.add((pid, ref_id))

    if citation_pairs:
        execute_values(
            cur,
            """
            INSERT INTO paper_citations (paper_id, cited_paper_id)
            VALUES %s
            ON CONFLICT (paper_id, cited_paper_id) DO NOTHING
            """,
            list(citation_pairs),
            page_size=2000,
        )

    print(f"Loaded {len(paper_rows)} papers and {len(citation_pairs)} citation links.")
    return len(paper_rows)


def load_synthetic(cur: Any) -> None:
    if not SYNTHETIC_PATH.exists():
        raise FileNotFoundError(
            f"{SYNTHETIC_PATH} not found. Run backend/generate_synthetic.py first."
        )

    syn = json.loads(SYNTHETIC_PATH.read_text(encoding="utf-8"))

    users = syn.get("users", [])
    user_interests = syn.get("user_interests", [])
    follows = syn.get("follows", [])
    library = syn.get("library", [])
    posts = syn.get("posts", [])
    comments = syn.get("comments", [])
    events = syn.get("activity_events", [])

    if users:
        execute_values(
            cur,
            """
            INSERT INTO users (id, name, email, password_hash, role, department, bio, created_at)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    int(u["id"]),
                    u["name"],
                    u["email"],
                    u.get("password_hash"),
                    u.get("role", "student"),
                    u.get("department", "Computer Science"),
                    u.get("bio", ""),
                    u.get("created_at"),
                )
                for u in users
            ],
            page_size=500,
        )

    if user_interests:
        execute_values(
            cur,
            """
            INSERT INTO user_interests (id, user_id, tag)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            [(int(ui["id"]), int(ui["user_id"]), ui["tag"]) for ui in user_interests],
            page_size=500,
        )

    if follows:
        execute_values(
            cur,
            """
            INSERT INTO follows (id, follower_id, following_id, created_at)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    int(f["id"]),
                    int(f["follower_id"]),
                    int(f["following_id"]),
                    f.get("created_at"),
                )
                for f in follows
            ],
            page_size=500,
        )

    if library:
        execute_values(
            cur,
            """
            INSERT INTO library (id, user_id, paper_id, notes, collection_name, created_at)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    int(item["id"]),
                    int(item["user_id"]),
                    str(item["paper_id"]),
                    item.get("notes", ""),
                    item.get("collection_name", "General"),
                    item.get("created_at"),
                )
                for item in library
            ],
            page_size=500,
        )

    if posts:
        execute_values(
            cur,
            """
            INSERT INTO posts (id, user_id, title, content, tags, attached_paper_id, created_at)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    int(p["id"]),
                    int(p["user_id"]),
                    p["title"],
                    p["content"],
                    json.dumps(p.get("tags") or []),
                    p.get("attached_paper_id"),
                    p.get("created_at"),
                )
                for p in posts
            ],
            template="(%s, %s, %s, %s, %s::jsonb, %s, COALESCE(%s::timestamptz, NOW()))",
            page_size=500,
        )

    if comments:
        execute_values(
            cur,
            """
            INSERT INTO comments (id, post_id, user_id, content, created_at)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
            """,
            [
                (
                    int(c["id"]),
                    int(c["post_id"]),
                    int(c["user_id"]),
                    c["content"],
                    c.get("created_at"),
                )
                for c in comments
            ],
            page_size=1000,
        )

    if events:
        execute_values(
            cur,
            """
            INSERT INTO activity_events (id, user_id, event_type, target_id, query_text, timestamp)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
            """,
            [
                (
                    int(e["id"]),
                    int(e["user_id"]),
                    e["event_type"],
                    e.get("target_id"),
                    e.get("query_text"),
                    e.get("timestamp"),
                )
                for e in events
            ],
            page_size=2000,
        )

    # Sync SERIAL sequences so subsequent API inserts auto-increment cleanly
    for table in SERIAL_TABLES:
        cur.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 1), true);"
        )

    print(
        f"Loaded synthetic data: {len(users)} users, {len(user_interests)} interests, "
        f"{len(follows)} follows, {len(library)} library items, {len(posts)} posts, "
        f"{len(comments)} comments, {len(events)} activity events."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Research Commons data into PostgreSQL.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate existing tables before loading fresh JSON data.",
    )
    args = parser.parse_args()

    print(f"Connecting to PostgreSQL at {DATABASE_URL}...")
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            ensure_schema(cur)
            if args.reset:
                cur.execute(
                    "TRUNCATE TABLE activity_events, comments, posts, library, "
                    "paper_citations, follows, user_interests, papers, users "
                    "RESTART IDENTITY CASCADE;"
                )
                print("Cleared existing tables (--reset).")
            load_papers(cur)
            load_synthetic(cur)
        conn.commit()
    print("PostgreSQL data load completed successfully.")


if __name__ == "__main__":
    main()
