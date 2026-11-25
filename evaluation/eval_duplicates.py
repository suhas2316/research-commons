"""
Evaluation Script: Duplicate Paper Detection & Entity Resolution
Benchmarks MinHash & LSH against the 10 planted ground-truth duplicates in data/ground_truth/ground_truth.json.
Calculates and reports Precision, Recall, and F1-Score for college viva & project report.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from search.deduplication import DuplicateDetector

GROUND_TRUTH_FILE = BASE_DIR / "data" / "ground_truth" / "ground_truth.json"
PROCESSED_PAPERS_FILE = BASE_DIR / "data" / "processed" / "papers.json"


def evaluate_duplicate_detection() -> dict[str, float]:
    print("=" * 70)
    print("RESEARCH COMMONS: DUPLICATE DETECTION EVALUATION BENCHMARK")
    print("Algorithm: MinHash & Locality-Sensitive Hashing (LSH) + DOI Matching")
    print("=" * 70)

    if not GROUND_TRUTH_FILE.exists():
        print(f"[ERROR] Ground truth file not found: {GROUND_TRUTH_FILE}")
        return {}

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    planted_duplicates = gt_data.get("duplicate_papers", [])
    expected_pairs = {
        frozenset([d["original_paper_id"], d["duplicate_paper_id"]])
        for d in planted_duplicates
    }

    # Load papers (or create synthetic test batch if not populated yet)
    if PROCESSED_PAPERS_FILE.exists():
        with open(PROCESSED_PAPERS_FILE, "r", encoding="utf-8") as f:
            papers = json.load(f)
    else:
        # Build mock evaluation corpus from ground truth
        papers = []
        for d in planted_duplicates:
            papers.append({
                "id": d["original_paper_id"],
                "title": d["original_title"],
                "abstract": "Sample abstract for research evaluation.",
                "doi": f"10.1000/{d['original_paper_id']}",
            })
            papers.append({
                "id": d["duplicate_paper_id"],
                "title": d["duplicate_title"],
                "abstract": "Sample abstract for research evaluation.",
                "doi": "",
            })

    print(f"Total Papers in Corpus: {len(papers)}")
    print(f"Total Planted Ground Truth Duplicates: {len(expected_pairs)}\n")

    detector = DuplicateDetector(threshold=0.65, num_perm=128)
    detected_clusters = detector.find_duplicate_clusters(papers)

    detected_pairs = set()
    for cluster in detected_clusters:
        cluster_list = list(cluster)
        for i in range(len(cluster_list)):
            for j in range(i + 1, len(cluster_list)):
                detected_pairs.add(frozenset([cluster_list[i], cluster_list[j]]))

    tp_pairs = detected_pairs & expected_pairs
    fp_pairs = detected_pairs - expected_pairs
    fn_pairs = expected_pairs - detected_pairs

    tp = len(tp_pairs)
    fp = len(fp_pairs)
    fn = len(fn_pairs)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print("--- EVALUATION METRICS REPORT ---")
    print(f"True Positives (Correctly Detected Duplicates): {tp} / {len(expected_pairs)}")
    print(f"False Positives (Incorrectly Grouped):         {fp}")
    print(f"False Negatives (Missed Duplicates):           {fn}")
    print(f"Precision: {precision:.4f} ({precision * 100:.2f}%)")
    print(f"Recall:    {recall:.4f} ({recall * 100:.2f}%)")
    print(f"F1-Score:  {f1:.4f} ({f1 * 100:.2f}%)")
    print("=" * 70)

    print("\nSample Detected Duplicate Pairs:")
    for pair in list(tp_pairs)[:5]:
        p1, p2 = list(pair)
        print(f"  [MATCH] {p1} <---> {p2}")

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": tp,
        "total_expected": len(expected_pairs),
    }


if __name__ == "__main__":
    evaluate_duplicate_detection()
