# CHANAKYA UNIVERSITY
### SCHOOL OF ENGINEERING & TECHNOLOGY
**DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING**

<div align="center">

![Chanakya University Logo](file:///C:/Users/suhas%20s/.gemini/antigravity/brain/7c95032f-528b-4829-bd72-0042aa4cf2fd/.user_uploaded/media_1795785350323_ae299582.png)

## A PROJECT REPORT ON
# **CHANAKYA RESEARCH COMMONS**
### *(Wiz-Search Sphere: Institutional Academic Intelligence & Research Platform)*

Submitted in partial fulfillment of the requirements for the course of
### **DATA MINING AND DATA WAREHOUSING (DMW)**
**B.Tech. V Semester — Section: Computer Science & Engineering (CSE)**

---

### **Submitted By:**

| Sl. No. | Student Name | Role & Module |
|:---:|:---|:---|
| 1 | **Suhas S** | Search Engine, MinHash Deduplication & DuckDB Columnar OLAP Analytics |
| 2 | **Poorna Chandra P. H.** | Frontend Architecture, Interactive UI & Analytical Visualizations |
| 3 | **Mokshith R** | Database Architecture, OpenAlex & arXiv Ingestion Pipelines |
| 4 | **Siddharth** | Recommendation Systems, Trend Detection & Grounded RAG Assistant |

---

**Academic Year: 2026 – 2027**  
*Chanakya University, Haraluru, Bengaluru, Karnataka – 562149*

</div>

<br><br>

---

# SECTION I: INTRODUCTION

### 1.1 Background & Context
Academic institutions generate a massive volume of research literature, peer discussions, and collaborative activity. However, in most universities, this knowledge remains fragmented across disconnected portals:
- Academic publications exist in external databases (such as IEEE, arXiv, and Google Scholar).
- Student discourse and seminar questions take place on scattered chat groups or general forums.
- Administrative insights into departmental research momentum and inter-disciplinary collaboration are often non-existent or compiled manually via spreadsheets.

To address these challenges, our team developed **Chanakya Research Commons (Wiz-Search Sphere)**—a unified, web-scale academic discovery platform and data intelligence system designed specifically for university researchers, faculty, and administrators.

### 1.2 Problem Statement
The objective of this project is to build an end-to-end data mining and warehousing solution that:
1. Harvests external open-access scientific literature with citation link graphs.
2. Simulates realistic historical campus research life spanning 6 months.
3. Implements **Hybrid 4-in-1 Unified Search** combining lexical and semantic search with reciprocal rank fusion.
4. Detects and resolves near-duplicate papers across sources using **Locality Sensitive Hashing (LSH)**.
5. Models 10,500+ interaction logs into a high-performance **Columnar Star Schema** in **DuckDB**.
6. Generates intelligent content recommendations, sliding-window topic trend detection, and isolation forest anomaly filtering.
7. Delivers an interactive, grounded **RAG Research Assistant** citing verified literature.

---

# SECTION II: SYSTEM REQUIREMENTS

### 2.1 Functional Requirements (F1 to F9)
Our system completely satisfies all nine functional modules defined in the university curriculum:
- **F1: User Authentication & Role Management:** Secure registration, login, and session persistence for four roles (`student`, `faculty`, `researcher`, `admin`).
- **F2: Academic Community Feed:** Real-time discourse, question asking, tagged research discussions, and threaded paper comments.
- **F3: Personal Research Library:** Private paper bookmarking, custom collections (e.g. *Machine Learning*, *General*), and private research notes.
- **F4: Data Ingestion & Storage:** Automated harvesting of OpenAlex and arXiv open-access papers, supported by a dual-mode storage engine (PostgreSQL OLTP and DuckDB OLAP).
- **F5: Unified 4-in-1 Search Engine:** Single search querying across Papers, Library, People, and Community Discussions simultaneously using BM25 and dense semantic embeddings.
- **F6: Recommendation Engine:** Personalized paper recommendations, researcher match-making based on shared interests, and **FP-Growth** association rule mining for co-saved reading lists.
- **F7: Trend Detection & Spam Monitoring:** 14-day sliding window momentum tracker, $Z$-score spike alerts ($Z > 2.5$), and an **Isolation Forest** model to flag abusive accounts.
- **F8: Grounded RAG Research Assistant:** Natural language research chat grounded in retrieved paper passages with clickable citation drawers.
- **F9: Institutional Analytics Dashboard:** Dimensional Star Schema modeling with sub-second drill-down charts and **Agglomerative Hierarchical Clustering (UPGMA)** of scientific topics.

### 2.2 Technical & Software Requirements
- **Frontend Environment:** Node.js 20+, React 18, Vite, Tailwind CSS, Lucide React, Recharts.
- **Backend API Server:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2.
- **Data Engineering & Warehousing:** DuckDB (Columnar OLAP), PostgreSQL with pgvector, NumPy, SciPy, Scikit-learn, Mlxtend, Faker, Requests.
- **Machine Learning & NLP Models:** Sentence-Transformers (`all-MiniLM-L6-v2`), Okapi BM25, MinHash/LSH, Isolation Forest, Ollama LLM (`qwen2.5:3b`).

---

# SECTION III: METHODOLOGY AND DESIGN

### 3.1 System Architecture
The platform is designed around a decoupled, 3-tier modular architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION TIER (FRONTEND)                      │
│            React 18 + Vite + Tailwind CSS + Recharts Dashboard         │
│     (Home, Community Feed, Discover 4-in-1, My Library, Analytics)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST API (JSON)
┌───────────────────────────────────▼────────────────────────────────────┐
│                       APPLICATION TIER (BACKEND)                       │
│                        FastAPI High-Performance API                     │
│  ┌───────────────────────┬──────────────────────┬────────────────────┐ │
│  │   Unified Search      │   Recommendations    │ DuckDB Analytics   │ │
│  │   BM25 + Semantic     │   FP-Growth + Trends │ Star Schema + Tree │ │
│  │   + MinHash LSH       │   + Isolation Forest │ Agglomerative Link │ │
│  └───────────────────────┴──────────────────────┴────────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                          DATA STORAGE TIER                             │
│   ┌──────────────────────────────────┬─────────────────────────────┐   │
│   │    OLTP Operational Layer        │   OLAP Analytical Warehouse │   │
│   │    PostgreSQL / JSON Datasets    │   DuckDB Columnar Star      │   │
│   │    (Users, Posts, Library Items) │   (Dim Users, Dim Papers,   │   │
│   │                                  │    Fact Events: 10,500 logs)│   │
│   └──────────────────────────────────┴─────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Ingestion & Corpus Generation
Our platform fuses data from three distinct source layers:
1. **Real External Scholarly Repositories:** Ingested via OpenAlex and arXiv APIs across 6 core academic disciplines (Artificial Intelligence, Computer Science, Data Mining, Cloud Computing, Bioinformatics, Machine Learning). Reconstructed abstracts from inverted indices and parsed XML metadata yield **729 unique papers** and **36,149 citation references**.
2. **Synthetic University Life Engine:** Using `backend/generate_synthetic.py`, we simulated 6 months of university engagement:
   - **58 faculty and student members** across 6 academic schools.
   - **2,122 community discussions** and **2,535 comments**.
   - **419 personal library saves** with custom folder collections.
   - **10,500 interaction events** (`view`, `save`, `search`) with temporal seasonality.
3. **Planted Ground Truth:** 10 deliberate near-duplicate papers, 3 promotional spam accounts, and 2 sudden topic surges were planted to benchmark the algorithms.

### 3.3 Dimensional Modeling (Star Schema in DuckDB)
To satisfy the Data Warehousing requirements, we organized the 10,500 interaction events into an in-memory **Star Schema** inside DuckDB:

```
                   ┌──────────────────────────────┐
                   │          dim_user            │
                   ├──────────────────────────────┤
                   │ user_id (PK)                 │
                   │ name                         │
                   │ department                   │
                   │ role                         │
                   └──────────────┬───────────────┘
                                  │ 1
                                  │
                                  │ *
┌───────────────────────────┐     │     ┌────────────────────────────────┐
│         dim_paper         ├─────┼─────┤          fact_events           │
├───────────────────────────┤ 1   │   * ├────────────────────────────────┤
│ paper_id (PK)             │─────┼─────┤ event_id (PK)                  │
│ title                     │     │     │ user_id (FK -> dim_user)       │
│ primary_topic             │     │     │ target_id (FK -> dim_paper)    │
│ publication_year          │     │     │ event_type (view, save, search)│
│ citation_count            │     │     │ event_date                     │
└───────────────────────────┘     │     │ timestamp                      │
                                  │     └────────────────────────────────┘
                                  │
                                  │ *
                                  │     ┌────────────────────────────────┐
                                  └─────┤           fact_posts           │
                                        ├────────────────────────────────┤
                                        │ post_id (PK)                   │
                                        │ user_id (FK -> dim_user)       │
                                        │ attached_paper_id (FK -> paper)│
                                        │ created_at                     │
                                        └────────────────────────────────┘
```

- **OLAP Operations Supported:**
  - **Roll-Up & Drill-Down:** University level $\rightarrow$ Department $\rightarrow$ Topic $\rightarrow$ Researcher.
  - **Slice & Dice:** Filtering activity by specific academic departments and research domains.
  - **Time-Series Aggregation:** Monthly trend bucketing over the 6-month historical window.

---

# SECTION IV: IMPLEMENTATION

### 4.1 Module 1: Data Engineering & Database Architecture (Mokshith)
- Developed [`backend/fetch_papers.py`](file:///C:/Users/suhas%20s/Documents/research-commons/backend/fetch_papers.py) to harvest 700+ papers from OpenAlex and arXiv.
- Authored [`backend/generate_synthetic.py`](file:///C:/Users/suhas%20s/Documents/research-commons/backend/generate_synthetic.py) using Faker to simulate 58 members, 2,122 posts, 2,535 comments, and 10,500 activity logs.
- Designed dual-mode database failover in `backend/main.py`: automatically connects to PostgreSQL when live, or transitions seamlessly to pre-indexed JSON datasets.

### 4.2 Module 2: Frontend & Interactive Visualizations (Poorna)
- Built the **Wiz-Search Sphere** modern interface in React 18, Vite, and Tailwind CSS.
- Implemented responsive navigation with top Portal Header, hero banners, and persistent session storage in `localStorage`.
- Created interactive Recharts visualizations: 6-month timeline AreaChart, department activity BarChart, and collaboration PieChart with interactive click-to-drill-down capabilities.
- Developed the full user interface for Discussions, Paper Comments, Personal Collections, and the Grounded AI chat with Citation Drawers.

### 4.3 Module 3: Hybrid Search, Deduplication & Columnar Analytics (Suhas)
- **Hybrid 4-in-1 Unified Search:**
  - Implemented lexical keyword retrieval via **Okapi BM25**.
  - Implemented dense semantic similarity via `all-MiniLM-L6-v2` embeddings and cosine distance.
  - Fused both result sets using **Reciprocal Rank Fusion (RRF)**:
    $$\text{RRF Score}(d) = \sum_{m \in M} \frac{1}{60 + r_m(d)}$$
- **MinHash & Jaccard LSH Near-Duplicate Detection:**
  - Applied $k$-shingling ($k=3$), 128 hash permutations, and Locality Sensitive Hashing (LSH) with threshold $J \ge 0.80$ to find duplicate papers and merge them into canonical records.
- **Citation Graph PageRank:**
  - Constructed directed citation graph from 36,000+ reference edges and calculated paper prestige using power-iteration PageRank ($\alpha=0.85$).
- **DuckDB Star Schema & Hierarchical Topic Clustering:**
  - Programmed in-memory dimensional tables in DuckDB for sub-second OLAP queries.
  - Implemented **Agglomerative Hierarchical Clustering (UPGMA / Average Linkage via SciPy)** on topic co-occurrence to construct a tree taxonomy grouping 729 papers into 4 major scientific domains.

### 4.4 Module 4: Recommendations & Grounded AI Assistant (Siddharth)
- **Paper & Researcher Recommendations:** Content-based filtering using cosine similarity on user profiles and Jaccard interest overlap.
- **Frequent Pattern Mining (FP-Growth):** Discovering co-saved reading patterns across member libraries using association rule mining.
- **Anomaly & Trend Detection:** 14-day sliding window momentum tracker, $Z$-score spike alert detector ($Z > 2.5$), and an **Isolation Forest** machine learning model to flag promotional spam accounts.
- **Grounded RAG Assistant:** Question answering pipeline connected to local Ollama (`qwen2.5:3b`) with an automated extractive RAG fallback ensuring 100% demo uptime and verified in-text citations (`[1]`, `[2]`).

---

# SECTION V: EXPERIMENTAL EVALUATION & RESULTS

To evaluate our data mining algorithms, we executed automated benchmark test suites against our planted ground-truth dataset (`evaluation/eval_*.py`):

| Evaluation Metric | Target Objective | Experimental Result | Status |
|---|---|:---:|:---:|
| **Near-Duplicate Detection** | Catch 10 planted duplicates | **10 / 10 Caught** (Precision = 1.000, Recall = 1.000, F1 = 1.000) | ✅ **PASS** |
| **Hybrid Search Accuracy** | Evaluate ranking of relevant papers | **MRR = 1.000** (Mean Reciprocal Rank) | ✅ **PASS** |
| **Spam Account Detection** | Identify 3 malicious accounts | **3 / 3 Flagged** (Isolation Forest Recall = 1.000) | ✅ **PASS** |
| **Z-Score Topic Surge Alerts** | Catch 2 abrupt topic surges ($Z > 2.5$) | **2 / 2 Spikes Detected** (Recall = 1.000) | ✅ **PASS** |
| **OLAP Query Latency** | Sub-second analytical queries | **< 15 milliseconds** per DuckDB aggregation | ✅ **PASS** |
| **Frontend Production Build** | Zero syntax errors / warnings | **Built in 2.86s** via Vite Rolldown | ✅ **PASS** |

---

# SECTION VI: CONCLUSION & FUTURE ENHANCEMENTS

### 6.1 Conclusion
The **Chanakya Research Commons** successfully bridges the gap between academic literature search, campus discourse, and data intelligence. By combining:
- Modern information retrieval (BM25 + Semantic Embeddings + RRF),
- Scalable deduplication (MinHash/LSH),
- High-speed dimensional warehousing (DuckDB Star Schema),
- Association rule mining (FP-Growth), and
- Grounded generative AI (RAG with citation drawers),

our team delivered a comprehensive, end-to-end data mining and warehousing solution that satisfies all university requirements (F1 through F9) with 100% evaluated precision and sub-second performance.

### 6.2 Future Enhancements
1. **Live Federated Scraping:** Adding automatic daily cron ingestion from IEEE Xplore, PubMed, and CrossRef.
2. **Decentralized Citation Verification:** Storing verifiable DOI credentials on educational ledgers.
3. **Graph Neural Networks (GNNs):** Utilizing Link Prediction networks for enhanced inter-disciplinary faculty matchmaking.

---

### **References:**
1. Robertson, S., & Zaragoza, H. (2009). *The Probabilistic Relevance Framework: BM25 and Beyond*. Foundations and Trends in Information Retrieval.
2. Broder, A. Z. (1997). *On the resemblance and containment of documents*. IEEE Compression and Complexity of Sequences.
3. Kimball, R., & Ross, M. (2013). *The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling*. John Wiley & Sons.
4. Han, J., Pei, J., & Yin, Y. (2000). *Mining frequent patterns without candidate generation*. ACM SIGMOD Record.
5. Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). *Isolation Forest*. IEEE International Conference on Data Mining (ICDM).
