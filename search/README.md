# Search & Analytics Module (Research Commons)

**Assigned Team Member:** Suhas  
**Git Branch:** `suhas-search`  
**Core Technologies:** BM25 (`rank-bm25`), Sentence Transformers (`all-MiniLM-L6-v2`), DuckDB (OLAP Columnar), MinHash & LSH (`datasketch`), PageRank (`networkx`).

---

## 🚀 Implemented Capabilities

### 1. Keyword Search (BM25) — `search/bm25_search.py`
* Tokenizes text, cleans punctuation, and removes English stopwords.
* Implements the **BM25Okapi** probabilistic ranking formula ($k_1=1.5, b=0.75$).
* Handles exact domain-specific queries and technical keywords.

### 2. Semantic Search (Dense Vector Embeddings) — `search/semantic_search.py`
* Encodes paper titles, abstracts, and concept tags into **384-dimensional dense vectors** using `sentence-transformers/all-MiniLM-L6-v2`.
* Computes normalized **cosine similarity** between the search query vector and paper vectors.
* Employs disk-based embedding caching (`paper_embeddings.npy`) for sub-second query latency.

### 3. Near-Duplicate Detection (MinHash + LSH) — `search/deduplication.py`
* Satisfies the course syllabus requirement for **near-duplicate detection and entity resolution**.
* Combines exact DOI/arXiv identifier matching with **MinHash & Locality-Sensitive Hashing (LSH)** on character 3-shingles.
* Groups duplicate preprints/reprints and merges them into canonical papers with aggregated source attributions (`["openalex", "arxiv"]`).

### 4. Citation Graph PageRank — `search/citation_pagerank.py`
* Builds a directed academic citation graph ($A \to B$) from paper reference networks.
* Applies Google's **PageRank algorithm** ($\alpha = 0.85$) to compute academic prestige and authority scores.
* High-influence papers receive normalized authority boosts in search rankings.

### 5. Hybrid Search (RRF) — `search/hybrid_search.py`
* Fuses lexical BM25 ranks and dense semantic ranks using **Reciprocal Rank Fusion (RRF)**:
  $$\text{RRF Score} = \frac{w_{\text{bm25}}}{60 + \text{Rank}_{\text{bm25}}} + \frac{w_{\text{semantic}}}{60 + \text{Rank}_{\text{semantic}}} + w_{\text{pr}} \cdot \text{PageRank}$$
* Automatically merges near-duplicates on the fly.

### 6. Columnar OLAP Analytics — `search/analytics_duckdb.py`
* Creates an in-memory **Star Schema** data mart in DuckDB (`dim_paper`, `dim_user`, `fact_events`, `fact_posts`).
* Delivers sub-second queries for the **Institutional Analytics Dashboard (F9)**:
  - Research topics distribution by department over time.
  - Cross-department collaboration matrix.
  - Most saved and discussed papers.
  - 6-month monthly and weekly engagement trends.

### 7. Unified 4-in-1 Federated Search — `search/unified_search.py`
* Satisfies the central **F5** requirement: One search box yielding 4 distinct panels:
  1. `papers`: Top matching academic papers.
  2. `library`: University-saved library bookmarks.
  3. `people`: Matching university members & faculty.
  4. `posts`: Matching community forum discussions.

---

## 📊 Evaluation & Verification

To satisfy the rubric requirement that *"every intelligent feature must be evaluated with numbers"*:

### 1. Duplicate Detection Benchmark
```bash
python evaluation/eval_duplicates.py
```
* **Evaluated against:** 10 planted ground-truth duplicates in `data/ground_truth/ground_truth.json`.
* **Results:**
  - **Precision:** 100.00%
  - **Recall:** 100.00%
  - **F1-Score:** 1.0000

### 2. Search Retrieval Quality Benchmark
```bash
python evaluation/eval_search.py
```
* Compares BM25 vs. Dense Semantic Vector vs. Hybrid Search across benchmark queries.
* Reports Mean Reciprocal Rank (MRR) and execution latency.
