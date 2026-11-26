"""
Shared data loader for the Research Commons Recommendations & AI module.

Loads papers, users, interests, library saves, posts, comments, follows,
and activity events from local JSON datasets (or PostgreSQL when configured),
and provides clean lookup helpers across all recommenders and detectors.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PAPERS_PATH = BASE_DIR / "data" / "processed" / "papers.json"
DEFAULT_SYNTHETIC_PATH = BASE_DIR / "data" / "synthetic" / "synthetic_data.json"
DEFAULT_GROUND_TRUTH_PATH = BASE_DIR / "data" / "ground_truth" / "ground_truth.json"

DEPARTMENT_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "Computer Science": [
        "computer science",
        "distributed systems",
        "cloud computing",
        "compilers",
        "operating systems",
        "databases",
        "cybersecurity",
        "software engineering",
        "algorithms",
    ],
    "Data Science": [
        "data mining",
        "big data",
        "olap analytics",
        "duckdb",
        "visualization",
        "statistical modeling",
        "time series",
        "etl pipelines",
    ],
    "AI & ML": [
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "natural language processing",
        "computer vision",
        "retrieval augmented generation",
        "transformers",
        "reinforcement learning",
        "graph neural networks",
    ],
    "Bioinformatics": [
        "bioinformatics",
        "genomics",
        "proteomics",
        "computational biology",
        "drug discovery",
        "sequence alignment",
        "systems biology",
        "biomedical nlp",
        "molecular docking",
    ],
    "Electronics": [
        "vlsi design",
        "embedded systems",
        "iot",
        "signal processing",
        "edge computing",
        "fpga",
        "wireless networks",
        "robotics",
    ],
    "Management": [
        "research analytics",
        "innovation management",
        "technology policy",
        "operations research",
        "decision sciences",
        "digital transformation",
        "supply chain analytics",
        "knowledge management",
    ],
}


def parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp string or datetime into a UTC-aware datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@dataclass
class ResearchCommonsData:
    """In-memory container unifying all Research Commons datasets."""

    papers: list[dict[str, Any]] = field(default_factory=list)
    users: list[dict[str, Any]] = field(default_factory=list)
    user_interests: list[dict[str, Any]] = field(default_factory=list)
    follows: list[dict[str, Any]] = field(default_factory=list)
    library: list[dict[str, Any]] = field(default_factory=list)
    posts: list[dict[str, Any]] = field(default_factory=list)
    comments: list[dict[str, Any]] = field(default_factory=list)
    activity_events: list[dict[str, Any]] = field(default_factory=list)

    papers_by_id: dict[str, dict[str, Any]] = field(init=False, default_factory=dict)
    users_by_id: dict[int, dict[str, Any]] = field(init=False, default_factory=dict)
    interests_by_user: dict[int, list[str]] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self.rebuild_indexes()

    def rebuild_indexes(self) -> None:
        """Rebuild fast lookup maps for papers, users, and per-user interest tags."""
        self.papers_by_id = {str(p["id"]): p for p in self.papers if "id" in p}
        self.users_by_id = {int(u["id"]): u for u in self.users if "id" in u}

        interests_map: dict[int, list[str]] = {}
        for row in self.user_interests:
            uid = int(row["user_id"])
            tag = str(row.get("tag", "")).strip()
            if tag:
                interests_map.setdefault(uid, [])
                if tag not in interests_map[uid]:
                    interests_map[uid].append(tag)

        for user in self.users:
            uid = int(user["id"])
            merged = list(interests_map.get(uid, []))
            for tag in user.get("interests") or []:
                clean = str(tag).strip()
                if clean and clean not in merged:
                    merged.append(clean)
            interests_map[uid] = merged

        self.interests_by_user = interests_map


def _load_json_file(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _try_load_postgres() -> ResearchCommonsData | None:
    """Attempt to load datasets from PostgreSQL when DATABASE_URL is reachable."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    try:
        import psycopg2  # type: ignore
        from psycopg2.extras import RealDictCursor  # type: ignore
    except ImportError:
        return None

    try:
        conn = psycopg2.connect(db_url, connect_timeout=2)
    except Exception:
        return None

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT to_regclass('public.papers') IS NOT NULL AS ok;")
            if not cur.fetchone()["ok"]:
                return None

            def fetch_all(query: str) -> list[dict[str, Any]]:
                cur.execute(query)
                return [dict(r) for r in cur.fetchall()]

            return ResearchCommonsData(
                papers=fetch_all("SELECT * FROM papers"),
                users=fetch_all("SELECT * FROM users"),
                user_interests=fetch_all("SELECT * FROM user_interests"),
                follows=fetch_all("SELECT * FROM follows"),
                library=fetch_all("SELECT * FROM library"),
                posts=fetch_all("SELECT * FROM posts"),
                comments=fetch_all("SELECT * FROM comments"),
                activity_events=fetch_all("SELECT * FROM activity_events"),
            )
    except Exception:
        return None
    finally:
        conn.close()


def load_data(
    papers_path: Path | str | None = None,
    synthetic_path: Path | str | None = None,
    prefer_db: bool = False,
) -> ResearchCommonsData:
    """
    Load Research Commons data from JSON files or PostgreSQL.

    By default loads local JSON files (`data/processed/papers.json` and
    `data/synthetic/synthetic_data.json`), falling back to PostgreSQL if
    configured and JSON files are absent (or when `prefer_db=True`).
    """
    if prefer_db:
        db_data = _try_load_postgres()
        if db_data is not None and db_data.papers:
            return db_data

    p_path = Path(papers_path) if papers_path else DEFAULT_PAPERS_PATH
    s_path = Path(synthetic_path) if synthetic_path else DEFAULT_SYNTHETIC_PATH

    raw_papers = _load_json_file(p_path)
    papers = (
        raw_papers
        if isinstance(raw_papers, list)
        else (raw_papers.get("papers", []) if isinstance(raw_papers, dict) else [])
    )

    syn = _load_json_file(s_path) or {}
    if not papers and not syn:
        db_data = _try_load_postgres()
        if db_data is not None:
            return db_data

    return ResearchCommonsData(
        papers=papers,
        users=syn.get("users", []),
        user_interests=syn.get("user_interests", []),
        follows=syn.get("follows", []),
        library=syn.get("library", []),
        posts=syn.get("posts", []),
        comments=syn.get("comments", []),
        activity_events=syn.get("activity_events", []),
    )
