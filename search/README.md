# Search and Analytics Module

## Module Overview
This folder contains the search engines, similarity algorithms, citation graph analysis, and OLAP analytics services for **Research Commons**.

- **Assigned Team Member:** Suhas
- **Primary Tech Stack:** Python, BM25 (`rank-bm25`), Sentence Transformers (`all-MiniLM-L6-v2`), DuckDB, Parquet, NetworkX (or graph libraries)

---

## Planned Responsibilities & Features
1. **Keyword Search (BM25):**
   - Inverted indexing and BM25 token-based matching across paper titles, abstracts, and posts.
2. **Semantic Search (Dense Embeddings):**
   - Vector embeddings using `all-MiniLM-L6-v2` and cosine similarity for meaning-based search.
3. **Hybrid Search:**
   - Combining BM25 keyword rankings with dense semantic similarity scores.
4. **Duplicate Paper Detection:**
   - Identical identifier matching (DOI, arXiv ID) and near-duplicate detection using MinHash and Locality-Sensitive Hashing (LSH).
5. **Citation Ranking (PageRank):**
   - Building a citation graph from paper citation networks and computing PageRank scores to rank influential papers.
6. **Analytics Engine (DuckDB & Parquet):**
   - Fast analytical queries (OLAP / star schema) summarizing department activity, research trends, and collaboration patterns for the admin dashboard.

---

## Getting Started (Planned)
1. Ensure the Python environment has required search and analytics packages:
   ```bash
   pip install rank-bm25 sentence-transformers duckdb pyarrow networkx
   ```
2. Build indexing scripts that read cleaned records from PostgreSQL / `data/processed/`.
3. Provide modular search and analytics APIs to integrate into the main backend.
