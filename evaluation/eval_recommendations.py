"""
Evaluation & Benchmark Suite for Research Commons Recommendations & AI Module.

Benchmarks against `data/ground_truth/ground_truth.json`:
1. Isolation Forest Spam Detection vs. planted spam accounts
   (vikram.m56, riya.k57, arjun.v58) -> Precision, Recall / Detection Rate, F1.
2. Sliding Window Z-Score Topic Spike Detection vs. planted week-46 surges
   ("quantum machine learning", "agentic rag systems") -> Z-scores & Spike Recall.
3. FP-Growth Association Rule Mining on co-saved library items -> itemsets,
   rules, confidence, lift, and sample recommendations.
4. Smoke verification of PaperRecommender (including cold-start fallback),
   ResearcherRecommender, and RAGAssistant citation grounding.

Usage:
    python evaluation/eval_recommendations.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from recommendations.data_loader import (
    DEFAULT_GROUND_TRUTH_PATH,
    DEFAULT_PAPERS_PATH,
    DEFAULT_SYNTHETIC_PATH,
    ResearchCommonsData,
    load_data,
)
from recommendations.recommendation_service import RecommendationService


def _build_fallback_fixture(gt: dict[str, Any]) -> ResearchCommonsData:
    """
    Build a deterministic in-memory dataset aligned with `ground_truth.json`
    if local gitignored `data/processed/papers.json` or `data/synthetic/synthetic_data.json`
    have not yet been generated.
    """
    papers = [
        {
            "id": "W1001",
            "title": "Foundations of Quantum Machine Learning",
            "abstract": "Quantum machine learning bridges parameterized quantum circuits with kernel methods and variational optimization.",
            "authors": ["Alice Quantum", "Bob Tensor"],
            "publication_year": 2024,
            "citation_count": 420,
            "concepts": ["Quantum Machine Learning", "Machine Learning", "Quantum Computing"],
            "department_topic": "machine learning",
        },
        {
            "id": "W1002",
            "title": "Agentic RAG Systems for Multi-Step Academic Discovery",
            "abstract": "Agentic retrieval-augmented generation combines iterative query planning with citation verification over scientific corpora.",
            "authors": ["Clara Agent", "Dev Retriever"],
            "publication_year": 2025,
            "citation_count": 310,
            "concepts": ["Agentic RAG Systems", "Retrieval Augmented Generation", "Natural Language Processing"],
            "department_topic": "artificial intelligence",
        },
        {
            "id": "W1003",
            "title": "Scalable Frequent Pattern Mining with FP-Trees",
            "abstract": "FP-Growth eliminates candidate generation via prefix-tree compression for high-throughput association mining.",
            "authors": ["Jiawei Han"],
            "publication_year": 2000,
            "citation_count": 9800,
            "concepts": ["Data Mining", "FP-Growth", "Association Rules"],
            "department_topic": "data mining",
        },
        {
            "id": "W1004",
            "title": "Isolation Forest for High-Dimensional Anomaly Detection",
            "abstract": "Isolation Forest isolates anomalies using random recursive partitioning with linear time complexity.",
            "authors": ["Fei Tony Liu"],
            "publication_year": 2008,
            "citation_count": 5600,
            "concepts": ["Anomaly Detection", "Isolation Forest", "Data Mining"],
            "department_topic": "data mining",
        },
        {
            "id": "W1005",
            "title": "Attention Is All You Need",
            "abstract": "The Transformer architecture relies entirely on self-attention mechanisms for sequence transduction.",
            "authors": ["Ashish Vaswani"],
            "publication_year": 2017,
            "citation_count": 120000,
            "concepts": ["Transformers", "Deep Learning", "Natural Language Processing"],
            "department_topic": "artificial intelligence",
        },
    ]

    users: list[dict[str, Any]] = []
    for uid in range(1, 31):
        users.append(
            {
                "id": uid,
                "name": f"Researcher {uid}",
                "email": f"researcher{uid}@chanakya.edu.in",
                "role": "faculty" if uid % 5 == 0 else "student",
                "department": "AI & ML" if uid % 2 == 0 else "Data Science",
                "bio": "University researcher working on data mining and machine learning.",
                "interests": ["machine learning", "data mining", "retrieval augmented generation"],
            }
        )

    for sp in gt.get("spam_accounts", []):
        users.append(
            {
                "id": int(sp["user_id"]),
                "name": sp["name"],
                "email": sp["email"],
                "role": "student",
                "department": sp["department"],
                "bio": "Fast-track publication consultant.",
                "interests": ["fast publication", "citation boost"],
            }
        )

    library: list[dict[str, Any]] = []
    for uid in range(1, 25):
        for pid in ("W1001", "W1002", "W1005"):
            library.append(
                {
                    "id": len(library) + 1,
                    "user_id": uid,
                    "paper_id": pid,
                    "collection_name": "Core References",
                    "created_at": "2026-10-15T10:00:00+00:00",
                }
            )

    posts: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    base_dt = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)

    for idx in range(120):
        uid = (idx % 30) + 1
        dt = base_dt + timedelta(days=idx % 140, hours=idx % 12)
        posts.append(
            {
                "id": len(posts) + 1,
                "user_id": uid,
                "title": f"Weekly seminar notes #{idx}",
                "content": f"Discussing experimental findings #{idx} in university reading group.",
                "tags": ["machine learning", "data mining"],
                "attached_paper_id": "W1003",
                "created_at": dt.isoformat(),
            }
        )
        events.append(
            {
                "id": len(events) + 1,
                "user_id": uid,
                "event_type": "search",
                "target_id": None,
                "query_text": "machine learning",
                "timestamp": dt.isoformat(),
            }
        )

    # Plant spam bursts for ground truth spam accounts
    spam_dt = datetime(2026, 11, 22, 14, 0, tzinfo=timezone.utc)
    for sp in gt.get("spam_accounts", []):
        suid = int(sp["user_id"])
        for j in range(30):
            dt = spam_dt + timedelta(hours=j % 4)
            posts.append(
                {
                    "id": len(posts) + 1,
                    "user_id": suid,
                    "title": "URGENT: Publish Your Paper in 48 Hours - Guaranteed Scopus!!",
                    "content": f"Visit fast-track-journals-promo.example.com promo code PUBLISH100! [Ref #{j + 1}]",
                    "tags": ["fast publication", "promo"],
                    "attached_paper_id": None,
                    "created_at": dt.isoformat(),
                }
            )
            for _ in range(8):
                events.append(
                    {
                        "id": len(events) + 1,
                        "user_id": suid,
                        "event_type": "search",
                        "target_id": None,
                        "query_text": "fast scopus publication promotion",
                        "timestamp": dt.isoformat(),
                    }
                )

    # Plant topic spikes matching ground truth
    for spike in gt.get("topic_spikes", []):
        topic = spike["topic"]
        start_dt = datetime.fromisoformat(f"{spike['spike_week_start']}T09:00:00+00:00")
        for j in range(int(spike.get("spike_posts", 45))):
            dt = start_dt + timedelta(days=j % 6, hours=j % 10)
            posts.append(
                {
                    "id": len(posts) + 1,
                    "user_id": (j % 30) + 1,
                    "title": f"Breakthrough benchmarks in {topic}",
                    "content": f"Rapid surge in {topic} discussions.",
                    "tags": [topic],
                    "attached_paper_id": "W1001",
                    "created_at": dt.isoformat(),
                }
            )
        for j in range(int(spike.get("spike_searches", 180))):
            dt = start_dt + timedelta(days=j % 6, hours=j % 10)
            events.append(
                {
                    "id": len(events) + 1,
                    "user_id": (j % 30) + 1,
                    "event_type": "search",
                    "target_id": None,
                    "query_text": topic,
                    "timestamp": dt.isoformat(),
                }
            )

    return ResearchCommonsData(
        papers=papers,
        users=users,
        library=library,
        posts=posts,
        activity_events=events,
    )


def evaluate() -> int:
    if not DEFAULT_GROUND_TRUTH_PATH.exists():
        print(f"[ERROR] Ground truth file not found: {DEFAULT_GROUND_TRUTH_PATH}")
        return 1

    with DEFAULT_GROUND_TRUTH_PATH.open("r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    has_local_json = DEFAULT_PAPERS_PATH.exists() and DEFAULT_SYNTHETIC_PATH.exists()
    if has_local_json:
        data = load_data()
        dataset_source = f"{DEFAULT_PAPERS_PATH.name} + {DEFAULT_SYNTHETIC_PATH.name}"
    else:
        data = _build_fallback_fixture(ground_truth)
        dataset_source = "in-memory ground-truth aligned fallback fixture (local JSON files not present)"

    service = RecommendationService(data=data)

    print("=" * 72)
    print("RESEARCH COMMONS - RECOMMENDATIONS & AI EVALUATION REPORT")
    print("=" * 72)
    print(f"Dataset Source   : {dataset_source}")
    print(f"Ground Truth     : {DEFAULT_GROUND_TRUTH_PATH}")
    print(
        f"Corpus Counts    : {len(data.papers)} papers | {len(data.users)} users | "
        f"{len(data.library)} library saves | {len(data.posts)} posts | "
        f"{len(data.activity_events)} activity events"
    )
    print()

    # ------------------------------------------------------------------
    # 1. Isolation Forest Spam Detection Benchmark
    # ------------------------------------------------------------------
    gt_spam = ground_truth.get("spam_accounts", [])
    gt_spam_ids = {int(item["user_id"]) for item in gt_spam}
    gt_spam_emails = {item["email"]: int(item["user_id"]) for item in gt_spam}

    flagged = service.detect_spam_accounts()
    flagged_ids = {int(item["user_id"]) for item in flagged}

    tp = len(flagged_ids & gt_spam_ids)
    fp = len(flagged_ids - gt_spam_ids)
    fn = len(gt_spam_ids - flagged_ids)
    tn = max(len(data.users) - (tp + fp + fn), 0)

    recall = tp / len(gt_spam_ids) if gt_spam_ids else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    print("[1] ISOLATION FOREST SPAM ACCOUNT DETECTION")
    print("-" * 72)
    print(f"Planted Spam Accounts : {len(gt_spam_ids)} -> {sorted(gt_spam_emails.keys())}")
    print(f"Flagged Accounts      : {len(flagged_ids)}")
    print(f"TP={tp} | FP={fp} | FN={fn} | TN={tn}")
    print(
        f"Detection Rate (Recall): {recall * 100:.2f}% | "
        f"Precision: {precision * 100:.2f}% | F1-Score: {f1 * 100:.2f}%"
    )
    for item in flagged:
        tag = "MATCH" if int(item["user_id"]) in gt_spam_ids else "FALSE_POS"
        print(
            f"  - [{tag}] user_id={item['user_id']} ({item['email']}) "
            f"risk_score={item['risk_score']:.2f}/100 | "
            f"dup_ratio={item['features']['post_duplication_ratio']:.2f}, "
            f"max_ev/hr={item['features']['max_events_per_hour']}, "
            f"promo_ratio={item['features']['promo_link_ratio']:.2f}"
        )
        for reason in item["reasons"]:
            print(f"      reason: {reason}")
    print()

    # ------------------------------------------------------------------
    # 2. Z-Score Sliding Window Topic Spike Detection Benchmark
    # ------------------------------------------------------------------
    gt_spikes = ground_truth.get("topic_spikes", [])
    detected_spikes = service.detect_topic_spikes(z_threshold=2.5)
    detected_by_topic: dict[str, list[dict[str, Any]]] = {}
    for s in detected_spikes:
        detected_by_topic.setdefault(s["topic"].lower(), []).append(s)

    matched_spikes = 0
    print("[2] SLIDING WINDOW Z-SCORE TOPIC SPIKE DETECTION (THRESHOLD Z > 2.5)")
    print("-" * 72)
    for gt_sp in gt_spikes:
        topic_lower = gt_sp["topic"].lower()
        target_week = gt_sp["iso_week"]
        candidates = detected_by_topic.get(topic_lower, [])
        exact = next((c for c in candidates if c["iso_week"] == target_week), None)
        if exact and exact["z_score"] > 2.5:
            matched_spikes += 1
            print(
                f"  - [ALERT TRIGGERED] topic='{gt_sp['topic']}' | "
                f"iso_week={exact['iso_week']} ({exact['week_start']}..{exact['week_end']}) | "
                f"mentions={exact['mentions']} (gt={gt_sp['spike_week_total_mentions']}) | "
                f"baseline_mean={exact['baseline_mean']:.2f} | "
                f"Z-score={exact['z_score']:.2f} > 2.5"
            )
        else:
            print(
                f"  - [MISSED] topic='{gt_sp['topic']}' | expected_week={target_week}"
            )

    spike_recall = matched_spikes / len(gt_spikes) if gt_spikes else 0.0
    print(f"Topic Spike Detection Rate (Recall): {spike_recall * 100:.2f}% ({matched_spikes}/{len(gt_spikes)})")
    trending = service.get_trending_topics(top_k=5)
    print("Top 5 Trending Topics:")
    for idx, tr in enumerate(trending, start=1):
        print(
            f"  {idx}. {tr['topic']} (peak_week={tr['peak_week']}, "
            f"Z={tr['z_score']:.2f}, status={tr['trend_status']})"
        )
    print()

    # ------------------------------------------------------------------
    # 3. FP-Growth Co-Saved Library Association Mining Benchmark
    # ------------------------------------------------------------------
    itemsets_all = service.fpgrowth.get_frequent_itemsets(min_length=1)
    itemsets_multi = service.fpgrowth.get_frequent_itemsets(min_length=2)
    rules = service.fpgrowth.get_association_rules(top_k=50)

    print("[3] FP-GROWTH CO-SAVED PAPER ASSOCIATION RULES")
    print("-" * 72)
    print(f"User Library Baskets         : {len(service.fpgrowth.baskets)}")
    print(f"Frequent Itemsets (len >= 1) : {len(itemsets_all)}")
    print(f"Frequent Co-Save Sets (>= 2) : {len(itemsets_multi)}")
    print(f"Association Rules Generated  : {len(rules)}")

    sample_cosaves: list[dict[str, Any]] = []
    if rules:
        avg_conf = sum(r["confidence"] for r in rules) / len(rules)
        avg_lift = sum(r["lift"] for r in rules) / len(rules)
        max_lift = max(r["lift"] for r in rules)
        print(
            f"Mean Confidence: {avg_conf * 100:.2f}% | "
            f"Mean Lift: {avg_lift:.2f} | Max Lift: {max_lift:.2f}"
        )
        seed_paper = rules[0]["antecedents"][0]
        sample_cosaves = service.get_cosaved_recommendations(seed_paper, top_k=5)
        seed_title = data.papers_by_id.get(seed_paper, {}).get("title", seed_paper)
        print(f'Sample Query ("Members who saved \'{seed_title[:60]}\' also saved..."):')
        for rec in sample_cosaves:
            print(
                f"  - {rec['paper_id']}: {rec['title'][:65]} "
                f"(conf={rec['confidence'] * 100:.1f}%, lift={rec['lift']:.2f}, support={rec['support']:.3f})"
            )
    print()

    # ------------------------------------------------------------------
    # 4. Paper, Cold-Start, Researcher & RAG Assistant Verification
    # ------------------------------------------------------------------
    print("[4] PAPER, COLD-START, RESEARCHER & RAG ASSISTANT VERIFICATION")
    print("-" * 72)
    sample_uid = int(data.users[0]["id"]) if data.users else 1
    paper_recs = service.recommend_papers(sample_uid, top_k=5)

    # Create a temporary cold-start user profile with zero history
    cold_user_id = 99999
    data.users.append(
        {
            "id": cold_user_id,
            "name": "Cold Start Student",
            "email": "coldstart@chanakya.edu.in",
            "role": "student",
            "department": "AI & ML",
            "bio": "",
            "interests": [],
        }
    )
    data.rebuild_indexes()
    cold_recs = service.recommend_papers(cold_user_id, top_k=3)
    # Remove temporary synthetic user after cold-start check
    data.users.pop()
    data.rebuild_indexes()

    colleague_recs = service.recommend_colleagues(sample_uid, top_k=3)
    rag_result = service.ask_assistant(
        "What techniques are used for anomaly detection or retrieval augmented generation?",
        top_k_sources=3,
    )

    print(f"Active User (id={sample_uid}) Paper Recs : {len(paper_recs)} returned")
    if paper_recs:
        print(f"  Top paper: {paper_recs[0]['title'][:70]} (score={paper_recs[0]['score']})")
    print(
        f"Cold-Start User Paper Recs     : {len(cold_recs)} returned "
        f"(cold_start_flag={all(r['cold_start'] for r in cold_recs)})"
    )
    if cold_recs:
        print(
            f"  Top foundational: {cold_recs[0]['title'][:65]} "
            f"(citations={cold_recs[0]['citation_count']})"
        )
    print(f"Colleague Recommendations      : {len(colleague_recs)} returned")
    if colleague_recs:
        top_c = colleague_recs[0]
        print(
            f"  Top match: {top_c['name']} ({top_c['role']}, {top_c['department']}, "
            f"score={top_c['similarity_score']})"
        )
    print(
        f"RAG Assistant                  : model={rag_result['model_used']}, "
        f"ollama_available={rag_result['ollama_available']}, "
        f"sources={len(rag_result['sources'])}"
    )
    for src in rag_result["sources"]:
        print(f"  Citation: {src['citation']}")
    print()

    passed = (
        recall == 1.0
        and spike_recall == 1.0
        and len(rules) > 0
        and len(paper_recs) > 0
        and len(cold_recs) > 0
        and all(r["cold_start"] for r in cold_recs)
        and len(rag_result["sources"]) > 0
    )
    print("=" * 72)
    print(f"OVERALL EVALUATION STATUS: {'PASS' if passed else 'FAIL'}")
    print("=" * 72)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(evaluate())
