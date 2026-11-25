"""
Generate synthetic community data and planted ground-truth evaluation cases
for Research Commons (Chanakya University Mini-Project).

Produces:
- 55 realistic members across 6 departments + 3 spam accounts (58 users total)
- User research interests and follow graph
- User library collections & co-saved paper patterns
- 2,050+ posts and 2,500+ comments with relevant tags and attached papers
- 10,500+ activity events (view, save, search) spread over the last 6 months
- Planted ground truth in data/ground_truth/ground_truth.json:
  1. 10 deliberate near-duplicate papers (also injected into data/processed/papers.json)
  2. 3 spam accounts posting repeated promotional content
  3. 2 sudden topic spikes in specific weeks for Z-score trend detection
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from faker import Faker

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_PAPERS_PATH = BASE_DIR / "data" / "processed" / "papers.json"
SYNTHETIC_OUTPUT_PATH = BASE_DIR / "data" / "synthetic" / "synthetic_data.json"
GROUND_TRUTH_OUTPUT_PATH = BASE_DIR / "data" / "ground_truth" / "ground_truth.json"

SEED = 42
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

DEPARTMENTS = [
    "Computer Science",
    "Data Science",
    "AI & ML",
    "Bioinformatics",
    "Electronics",
    "Management",
]

DEPARTMENT_INTERESTS: dict[str, list[str]] = {
    "Computer Science": [
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

POST_TEMPLATES = [
    (
        "Key takeaways from '{title}'",
        "I just finished reading '{title}' and found the methodology especially relevant to our {topic} work. "
        "Their experimental evaluation highlights strong gains in scalability and reproducibility. "
        "Has anyone in {dept} tried replicating their baseline?",
    ),
    (
        "Discussion: Applying {topic} in university research projects",
        "We are exploring how recent advances in {topic} can improve our department's ongoing mini-projects. "
        "Looking for collaborators interested in benchmarking open datasets and comparing evaluation metrics.",
    ),
    (
        "Reading group notes on {topic}",
        "Summary from this week's {dept} reading seminar covering {topic}. Main open challenge remains "
        "balancing computational efficiency with interpretability across noisy real-world corpora.",
    ),
    (
        "Dataset & tooling recommendations for {topic}",
        "Could anyone share reliable open-source benchmarks or libraries for {topic}? "
        "We noticed significant variance across preprocessing pipelines and want a clean baseline.",
    ),
    (
        "Open questions in {topic} literature",
        "Reviewing papers published over the last few years in {topic}, there is a clear gap in standardized "
        "cross-domain evaluation. Sharing notes and would love feedback from faculty and peers.",
    ),
]

COMMENT_TEMPLATES = [
    "Great summary! We observed very similar results when testing on our lab dataset.",
    "Thanks for sharing this paper. I added it to my reading collection for next week's seminar.",
    "Have you compared this approach with a simple BM25 + dense reranker baseline?",
    "Interesting point about reproducibility — the hyperparameter sensitivity here is worth noting.",
    "I'm working on a closely related problem in {dept}, happy to collaborate on benchmarks!",
    "The citation network around this work has grown rapidly over the past two years.",
    "Solid breakdown. Section 4 on ablation studies is particularly insightful.",
    "Following this thread — curious if anyone has code or notebooks implementing this.",
]

SPAM_POST_TEMPLATES = [
    (
        "URGENT: Publish Your Paper in 48 Hours - Guaranteed Scopus & IEEE Indexing!!",
        "Limited time academic offer! Boost your citations 10x instantly with guaranteed fast-track acceptance. "
        "Visit fast-track-journals-promo.example.com now for 70% discount on publication fees! DM for bulk packages.",
    ),
    (
        "Best Cheap Thesis Writing & Plagiarism Removal Service - 100% Guaranteed Pass",
        "Struggling with deadlines? Our expert ghostwriters deliver complete MTech/PhD dissertations overnight. "
        "Click buy-research-papers-now.example.com and use promo code PUBLISH100 today!!",
    ),
    (
        "Buy Instant Google Scholar Citations & H-Index Boost Package",
        "Increase your academic profile metrics in 7 days! Affordable citation bundles available for faculty and students. "
        "Contact promo-citations-agency.example.com immediately for special student rates!",
    ),
]

COLLECTIONS = ["To Read", "Literature Review", "Core References", "Thesis", "Lab Seminar"]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_papers() -> list[dict[str, Any]]:
    if not PROCESSED_PAPERS_PATH.exists():
        raise FileNotFoundError(
            f"{PROCESSED_PAPERS_PATH} not found. Run backend/fetch_papers.py first."
        )
    with PROCESSED_PAPERS_PATH.open("r", encoding="utf-8") as f:
        papers = json.load(f)
    # Remove any previously planted duplicates so re-runs stay clean and idempotent
    return [p for p in papers if not str(p.get("id", "")).startswith("W_DUP_")]


def generate_duplicate_papers(
    papers: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create 10 deliberate near-duplicate papers for MinHash/LSH evaluation."""
    candidates = [p for p in papers if len(p.get("title", "")) > 25 and len(p.get("abstract", "")) > 80]
    chosen = random.sample(candidates, min(10, len(candidates)))

    duplicates: list[dict[str, Any]] = []
    gt_records: list[dict[str, Any]] = []

    for idx, orig in enumerate(chosen, start=1):
        dup_id = f"W_DUP_{idx:03d}"
        orig_title = orig["title"]
        words = orig_title.split()

        if idx % 3 == 0:
            dup_title = orig_title.replace(":", " -") if ":" in orig_title else f"{orig_title}: A Survey"
            mutation_type = "punctuation_and_subtitle_variant"
        elif idx % 3 == 1 and len(words) > 4:
            # Minor wording / casing / hyphen variation
            dup_title = " ".join(words[:-1]) + " " + words[-1].lower() + " (Preprint)"
            mutation_type = "preprint_suffix_and_casing"
        else:
            dup_title = orig_title.replace(" and ", " & ").replace("-", " ")
            if dup_title == orig_title:
                dup_title = f"An Empirical Study of {orig_title}"
            mutation_type = "conjunction_and_prefix_variant"

        # Slightly alter author formatting (e.g. "First Last" -> "F. Last")
        dup_authors = []
        for a in orig.get("authors", []):
            parts = a.split()
            if len(parts) >= 2:
                dup_authors.append(f"{parts[0][0]}. {' '.join(parts[1:])}")
            else:
                dup_authors.append(a)

        # Slightly perturb abstract tail while keeping high Jaccard/MinHash similarity
        orig_abs = orig.get("abstract", "")
        dup_abstract = f"{orig_abs} Extended version with additional experimental details."

        dup_record = {
            "id": dup_id,
            "title": dup_title,
            "abstract": dup_abstract,
            "authors": dup_authors,
            "doi": None,
            "arxiv_id": f"250{idx}.0{1000 + idx}",
            "source": "arxiv",
            "publication_year": orig.get("publication_year"),
            "citation_count": max(0, int(orig.get("citation_count", 0) * 0.2)),
            "concepts": orig.get("concepts", []),
            "department_topic": orig.get("department_topic"),
            "referenced_works": orig.get("referenced_works", [])[:5],
            "url": f"https://arxiv.org/abs/250{idx}.0{1000 + idx}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        duplicates.append(dup_record)
        gt_records.append(
            {
                "original_paper_id": orig["id"],
                "duplicate_paper_id": dup_id,
                "original_title": orig_title,
                "duplicate_title": dup_title,
                "mutation_type": mutation_type,
            }
        )

    return duplicates, gt_records


def generate_users(now: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate 55 normal members + 3 spam accounts across 6 departments."""
    users: list[dict[str, Any]] = []
    user_interests: list[dict[str, Any]] = []
    spam_gt: list[dict[str, Any]] = []

    default_pw_hash = hash_password("password123")

    # Seed core team accounts for easy demo login
    core_members = [
        ("Mokshith R", "mokshith@chanakya.edu.in", "student", "Data Science", "Backend and database lead for Research Commons."),
        ("Poorna S", "poorna@chanakya.edu.in", "student", "Computer Science", "Frontend architect building interactive academic UIs."),
        ("Suhas K", "suhas@chanakya.edu.in", "student", "AI & ML", "Search engines, MinHash/LSH, and DuckDB analytics."),
        ("Siddharth V", "siddharth@chanakya.edu.in", "student", "AI & ML", "Recommender systems, anomaly detection, and RAG."),
        ("Dr. Ananya Rao", "admin@chanakya.edu.in", "admin", "Computer Science", "Faculty coordinator for Data Mining and Warehousing."),
    ]

    interest_id = 1
    used_emails = set()

    def add_user_record(
        uid: int,
        name: str,
        email: str,
        role: str,
        dept: str,
        bio: str,
        days_ago: int,
        interests: list[str],
    ) -> dict[str, Any]:
        nonlocal interest_id
        used_emails.add(email)
        created_at = (now - timedelta(days=days_ago)).isoformat()
        for tag in interests:
            user_interests.append({"id": interest_id, "user_id": uid, "tag": tag})
            interest_id += 1
        user_obj = {
            "id": uid,
            "name": name,
            "email": email,
            "password_hash": default_pw_hash,
            "role": role,
            "department": dept,
            "bio": bio,
            "interests": interests,
            "created_at": created_at,
        }
        users.append(user_obj)
        return user_obj

    for idx, (name, email, role, dept, bio) in enumerate(core_members, start=1):
        tags = random.sample(DEPARTMENT_INTERESTS[dept], 4)
        add_user_record(idx, name, email, role, dept, bio, random.randint(150, 180), tags)

    roles_pool = ["student"] * 30 + ["researcher"] * 10 + ["faculty"] * 9 + ["admin"] * 1
    random.shuffle(roles_pool)

    # Generate remaining 50 normal members (total 55 normal members)
    for i in range(6, 56):
        dept = DEPARTMENTS[(i - 6) % len(DEPARTMENTS)]
        role = roles_pool[(i - 6) % len(roles_pool)]
        name = fake.name()
        slug = "".join(ch.lower() if ch.isalnum() else "." for ch in name).strip(".")
        email = f"{slug}.{i}@chanakya.edu.in"
        while email in used_emails:
            email = f"{slug}.{i}.{random.randint(10, 99)}@chanakya.edu.in"

        tags = random.sample(DEPARTMENT_INTERESTS[dept], random.randint(3, 5))
        bio = (
            f"{role.capitalize()} in {dept} at Chanakya University researching "
            f"{tags[0]} and {tags[1]}."
        )
        add_user_record(i, name, email, role, dept, bio, random.randint(60, 180), tags)

    # Inject 3 spam accounts (IDs 56, 57, 58) with normal-looking identities
    spam_profiles = [
        ("Vikram Malhotra", "vikram.m56@external-mail.org", "Management"),
        ("Riya Kapoor", "riya.k57@external-mail.org", "Computer Science"),
        ("Arjun Verma", "arjun.v58@external-mail.org", "Data Science"),
    ]
    for offset, (name, email, dept) in enumerate(spam_profiles):
        uid = 56 + offset
        tags = ["fast publication", "citation boost", "scopus indexing"]
        user_obj = add_user_record(
            uid,
            name,
            email,
            "student",
            dept,
            "Academic publishing consultant & fast-track services.",
            random.randint(10, 25),
            tags,
        )
        spam_gt.append(
            {
                "user_id": uid,
                "name": name,
                "email": email,
                "department": dept,
                "spam_reason": "High-frequency repetitive promotional posts and automated activity bursts",
                "post_ids": [],
            }
        )

    return users, user_interests, spam_gt


def generate_follows(users: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    follows: list[dict[str, Any]] = []
    seen_pairs: set[tuple[int, int]] = set()
    normal_users = [u for u in users if u["id"] <= 55]

    fid = 1
    for u in normal_users:
        same_dept = [o["id"] for o in normal_users if o["id"] != u["id"] and o["department"] == u["department"]]
        other_dept = [o["id"] for o in normal_users if o["id"] != u["id"] and o["department"] != u["department"]]
        targets = random.sample(same_dept, min(4, len(same_dept))) + random.sample(
            other_dept, min(2, len(other_dept))
        )
        for target_id in targets:
            pair = (u["id"], target_id)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                follows.append(
                    {
                        "id": fid,
                        "follower_id": u["id"],
                        "following_id": target_id,
                        "created_at": (now - timedelta(days=random.randint(1, 160))).isoformat(),
                    }
                )
                fid += 1
    return follows


def generate_library_and_cosaves(
    users: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    now: datetime,
) -> list[dict[str, Any]]:
    """Generate realistic library entries, including co-saved clusters for FP-Growth."""
    library_entries: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()
    normal_users = [u for u in users if u["id"] <= 55]
    paper_ids = [p["id"] for p in papers]

    # Create 6 frequent co-saved bundles so FP-Growth discovers clear patterns
    bundles = [random.sample(paper_ids, 4) for _ in range(6)]

    lid = 1
    for u in normal_users:
        collection = random.choice(COLLECTIONS)
        # Assign 1-2 co-save bundles to subsets of users
        chosen_bundle = bundles[u["id"] % len(bundles)]
        for pid in random.sample(chosen_bundle, random.randint(2, 4)):
            key = (u["id"], pid, collection)
            if key not in seen:
                seen.add(key)
                library_entries.append(
                    {
                        "id": lid,
                        "user_id": u["id"],
                        "paper_id": pid,
                        "notes": f"Key reference for {u['department']} project.",
                        "collection_name": collection,
                        "created_at": (now - timedelta(days=random.randint(1, 150))).isoformat(),
                    }
                )
                lid += 1

        # Add additional individual papers
        for pid in random.sample(paper_ids, random.randint(3, 6)):
            col = random.choice(COLLECTIONS)
            key = (u["id"], pid, col)
            if key not in seen:
                seen.add(key)
                library_entries.append(
                    {
                        "id": lid,
                        "user_id": u["id"],
                        "paper_id": pid,
                        "notes": "Saved during literature exploration.",
                        "collection_name": col,
                        "created_at": (now - timedelta(days=random.randint(1, 150))).isoformat(),
                    }
                )
                lid += 1

    return library_entries


def generate_posts_comments_and_events(
    users: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    library_entries: list[dict[str, Any]],
    spam_gt: list[dict[str, Any]],
    now: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Generate:
    - 2,000+ posts (normal + spam + topic-spike posts)
    - 2,500+ comments
    - 10,000+ activity events over the last 6 months (180 days)
    - 2 planted topic spikes in specific weeks
    """
    normal_users = [u for u in users if u["id"] <= 55]
    paper_ids = [p["id"] for p in papers]
    paper_lookup = {p["id"]: p for p in papers}

    posts: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    post_id = 1
    comment_id = 1
    event_id = 1

    # 1. Generate 1,920 baseline normal posts distributed across 180 days
    for _ in range(1920):
        author = random.choice(normal_users)
        dept = author["department"]
        topic = random.choice(author["interests"])
        attached_pid = random.choice(paper_ids) if random.random() < 0.45 else None
        attached_title = paper_lookup[attached_pid]["title"] if attached_pid else f"Advances in {topic}"

        tpl_title, tpl_body = random.choice(POST_TEMPLATES)
        title = tpl_title.format(title=attached_title[:85], topic=topic, dept=dept)
        content = tpl_body.format(title=attached_title[:120], topic=topic, dept=dept)
        tags = list({topic, dept.lower(), random.choice(DEPARTMENT_INTERESTS[dept])})
        created_dt = now - timedelta(
            days=random.randint(0, 179),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        posts.append(
            {
                "id": post_id,
                "user_id": author["id"],
                "title": title[:290],
                "content": content,
                "tags": tags,
                "attached_paper_id": attached_pid,
                "created_at": created_dt.isoformat(),
            }
        )

        # Add 1 to 2 comments on most normal posts
        num_comments = random.choices([0, 1, 2, 3], weights=[0.15, 0.45, 0.30, 0.10])[0]
        for c_idx in range(num_comments):
            commenter = random.choice(normal_users)
            c_dt = min(now, created_dt + timedelta(hours=random.randint(1, 72) * (c_idx + 1)))
            c_text = random.choice(COMMENT_TEMPLATES).format(dept=commenter["department"])
            comments.append(
                {
                    "id": comment_id,
                    "post_id": post_id,
                    "user_id": commenter["id"],
                    "content": c_text,
                    "created_at": c_dt.isoformat(),
                }
            )
            comment_id += 1

        post_id += 1

    # 2. Inject 90 promotional spam posts across the 3 spam accounts (30 each) in recent days
    for spam_info in spam_gt:
        suid = spam_info["user_id"]
        for s_idx in range(30):
            s_title, s_content = SPAM_POST_TEMPLATES[s_idx % len(SPAM_POST_TEMPLATES)]
            s_dt = now - timedelta(days=random.randint(0, 5), hours=random.randint(0, 23), minutes=random.randint(0, 59))
            posts.append(
                {
                    "id": post_id,
                    "user_id": suid,
                    "title": s_title,
                    "content": f"{s_content} [Ref #{s_idx + 1}]",
                    "tags": ["fast publication", "citation boost", "promo"],
                    "attached_paper_id": None,
                    "created_at": s_dt.isoformat(),
                }
            )
            spam_info["post_ids"].append(post_id)
            post_id += 1

            # Burst spam activity events
            for _ in range(8):
                events.append(
                    {
                        "id": event_id,
                        "user_id": suid,
                        "event_type": "search",
                        "target_id": None,
                        "query_text": "fast scopus publication promotion",
                        "timestamp": s_dt.isoformat(),
                    }
                )
                event_id += 1

    # 3. Inject 2 sudden topic spikes in a specific ISO week (Monday-Sunday) for Z-score evaluation.
    #    Aligning to Monday ensures all spike events fall cleanly within one ISO week.
    days_since_monday = now.weekday()
    spike_week_start = (now - timedelta(days=days_since_monday + 14)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    spike_week_end = (spike_week_start + timedelta(days=6)).replace(
        hour=23, minute=59, second=0, microsecond=0
    )

    spike_topics = [
        {
            "topic": "quantum machine learning",
            "baseline_posts": 12,
            "baseline_searches": 20,
            "spike_posts": 45,
            "spike_searches": 180,
        },
        {
            "topic": "agentic rag systems",
            "baseline_posts": 10,
            "baseline_searches": 18,
            "spike_posts": 45,
            "spike_searches": 180,
        },
    ]

    topic_spikes_gt: list[dict[str, Any]] = []

    for st in spike_topics:
        topic_name = st["topic"]
        # Low baseline spread outside the spike week
        for _ in range(st["baseline_posts"]):
            author = random.choice(normal_users)
            days_ago = random.choice([d for d in range(25, 178)])
            dt = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            posts.append(
                {
                    "id": post_id,
                    "user_id": author["id"],
                    "title": f"Exploratory note on {topic_name}",
                    "content": f"Early reading notes and open questions regarding {topic_name}.",
                    "tags": [topic_name, author["department"].lower()],
                    "attached_paper_id": random.choice(paper_ids),
                    "created_at": dt.isoformat(),
                }
            )
            post_id += 1

        for _ in range(st["baseline_searches"]):
            user = random.choice(normal_users)
            days_ago = random.choice([d for d in range(25, 178)])
            dt = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            events.append(
                {
                    "id": event_id,
                    "user_id": user["id"],
                    "event_type": "search",
                    "target_id": None,
                    "query_text": topic_name,
                    "timestamp": dt.isoformat(),
                }
            )
            event_id += 1

        # Sharp surge inside the specific spike week
        for _ in range(st["spike_posts"]):
            author = random.choice(normal_users)
            dt = spike_week_start + timedelta(
                days=random.randint(0, 6),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            posts.append(
                {
                    "id": post_id,
                    "user_id": author["id"],
                    "title": f"Breakthrough benchmarks in {topic_name}",
                    "content": f"Rapid surge in {topic_name} discussions across Chanakya University labs this week.",
                    "tags": [topic_name, "trending", author["department"].lower()],
                    "attached_paper_id": random.choice(paper_ids),
                    "created_at": dt.isoformat(),
                }
            )
            post_id += 1

        for _ in range(st["spike_searches"]):
            user = random.choice(normal_users)
            dt = spike_week_start + timedelta(
                days=random.randint(0, 6),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            events.append(
                {
                    "id": event_id,
                    "user_id": user["id"],
                    "event_type": "search",
                    "target_id": None,
                    "query_text": topic_name,
                    "timestamp": dt.isoformat(),
                }
            )
            event_id += 1

        baseline_weekly_avg = round((st["baseline_posts"] + st["baseline_searches"]) / 25.0, 2)
        spike_total = st["spike_posts"] + st["spike_searches"]
        iso_year, iso_week, _ = spike_week_start.isocalendar()
        topic_spikes_gt.append(
            {
                "topic": topic_name,
                "spike_week_start": spike_week_start.date().isoformat(),
                "spike_week_end": spike_week_end.date().isoformat(),
                "iso_week": f"{iso_year}-W{iso_week:02d}",
                "baseline_weekly_avg": baseline_weekly_avg,
                "spike_week_total_mentions": spike_total,
                "spike_posts": st["spike_posts"],
                "spike_searches": st["spike_searches"],
            }
        )

    # 4. Create 'save' events matching library entries
    for entry in library_entries:
        events.append(
            {
                "id": event_id,
                "user_id": entry["user_id"],
                "event_type": "save",
                "target_id": entry["paper_id"],
                "query_text": None,
                "timestamp": entry["created_at"],
            }
        )
        event_id += 1

    # 5. Fill remaining activity events up to at least 10,500 total across 180 days
    all_search_queries = [
        tag for tags in DEPARTMENT_INTERESTS.values() for tag in tags
    ]
    while len(events) < 10500:
        user = random.choice(normal_users)
        ev_type = random.choices(["view", "save", "search"], weights=[0.55, 0.15, 0.30])[0]
        dt = now - timedelta(
            days=random.randint(0, 179),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        if ev_type == "search":
            q = random.choice(user["interests"]) if random.random() < 0.7 else random.choice(all_search_queries)
            target_id = None
        elif ev_type == "save":
            q = None
            target_id = random.choice(paper_ids)
        else:
            q = None
            target_id = random.choice(paper_ids) if random.random() < 0.75 else str(random.randint(1, len(posts)))

        events.append(
            {
                "id": event_id,
                "user_id": user["id"],
                "event_type": ev_type,
                "target_id": target_id,
                "query_text": q,
                "timestamp": dt.isoformat(),
            }
        )
        event_id += 1

    # Sort events chronologically for clean time-series analytics
    events.sort(key=lambda e: e["timestamp"])
    for idx, ev in enumerate(events, start=1):
        ev["id"] = idx

    return posts, comments, events, topic_spikes_gt


def main() -> None:
    SYNTHETIC_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    clean_papers = load_papers()

    # 1. Inject 10 deliberate duplicate papers into processed papers dataset
    duplicate_papers, duplicate_gt = generate_duplicate_papers(clean_papers)
    papers_with_duplicates = clean_papers + duplicate_papers
    with PROCESSED_PAPERS_PATH.open("w", encoding="utf-8") as f:
        json.dump(papers_with_duplicates, f, indent=2, ensure_ascii=False)

    # 2. Generate users, interests, follows, library, posts, comments, events
    users, user_interests, spam_gt = generate_users(now)
    follows = generate_follows(users, now)
    library = generate_library_and_cosaves(users, clean_papers, now)
    posts, comments, activity_events, topic_spikes_gt = generate_posts_comments_and_events(
        users, clean_papers, library, spam_gt, now
    )

    synthetic_payload = {
        "metadata": {
            "generated_at": now.isoformat(),
            "seed": SEED,
            "counts": {
                "users": len(users),
                "user_interests": len(user_interests),
                "follows": len(follows),
                "library": len(library),
                "posts": len(posts),
                "comments": len(comments),
                "activity_events": len(activity_events),
            },
        },
        "users": users,
        "user_interests": user_interests,
        "follows": follows,
        "library": library,
        "posts": posts,
        "comments": comments,
        "activity_events": activity_events,
    }

    ground_truth_payload = {
        "generated_at": now.isoformat(),
        "description": "Planted ground truth evaluation cases for MinHash/LSH, Isolation Forest, and Z-score trend detection.",
        "duplicate_papers": duplicate_gt,
        "spam_accounts": spam_gt,
        "topic_spikes": topic_spikes_gt,
    }

    with SYNTHETIC_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(synthetic_payload, f, indent=2, ensure_ascii=False)

    with GROUND_TRUTH_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(ground_truth_payload, f, indent=2, ensure_ascii=False)

    print("Synthetic data & ground truth generation complete!")
    print(f"  Papers (with 10 duplicates): {len(papers_with_duplicates)} -> {PROCESSED_PAPERS_PATH}")
    print(f"  Users:                       {len(users)} (55 members + 3 spam accounts)")
    print(f"  Follows:                     {len(follows)}")
    print(f"  Library entries:             {len(library)}")
    print(f"  Posts:                       {len(posts)}")
    print(f"  Comments:                    {len(comments)}")
    print(f"  Activity events:             {len(activity_events)}")
    print(f"  Synthetic JSON:              {SYNTHETIC_OUTPUT_PATH}")
    print(f"  Ground truth JSON:           {GROUND_TRUTH_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
