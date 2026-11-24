# Evaluation & Testing

## Overview
This folder contains evaluation scripts, benchmark datasets, and accuracy test runners for the various algorithmic modules of **Research Commons**.

- **Maintainers:** Suhas, Siddharth, and Mokshith

---

## Planned Responsibilities
1. **Search Evaluation:**
   - Benchmarking BM25, semantic search, and hybrid search against test queries.
   - Measuring precision, recall, and duplicate detection accuracy using MinHash/LSH against `data/ground_truth/`.
2. **Recommendation & Trend Evaluation:**
   - Testing FP-Growth itemset generation and recommendation relevance.
   - Verifying Z-score spike alerts and Isolation Forest anomaly detection against planted ground truth events.
3. **Research Assistant Evaluation:**
   - Validating source citation grounding and RAG response faithfulness.
4. **Reproducible Test Logs:**
   - Storing empirical results, run logs, and error analysis for project reports and presentations.
