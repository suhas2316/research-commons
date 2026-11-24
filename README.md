# Research Commons

## Project Description
**Research Commons** is a university collaboration platform where students, faculty, and researchers can share research, find papers, participate in discussions, and view academic research analytics. The platform integrates community discussion features with research exploration tools in a unified application.

> **Status:** Project initialization phase. Module folder structures and repository branches are prepared for independent module development by team members.

---

## Technologies Used
- **Frontend:** React, Vite, Tailwind CSS, Recharts
- **Backend & APIs:** Python, FastAPI, Uvicorn
- **Databases & Storage:** PostgreSQL, pgvector, MinIO (raw data storage)
- **Search & Graph Analytics:** BM25, Sentence Transformers (`all-MiniLM-L6-v2`), MinHash/LSH, PageRank, DuckDB, Parquet
- **Recommendations & AI:** scikit-learn, MLxtend (FP-Growth), Ollama (Local LLM for RAG assistant)

---

## Team Members and Responsibilities

| Member | Module | Primary Responsibilities |
| :--- | :--- | :--- |
| **Poorna** | **Frontend Development** | React, Vite, Tailwind CSS, UI design, user authentication screens, discussions, library, search UI, assistant chat UI, and analytics dashboard. |
| **Mokshith** | **Database & Backend** | Python, FastAPI, PostgreSQL, MinIO, paper data harvesting (OpenAlex, arXiv), database schema, and core CRUD APIs. |
| **Suhas** | **Search & Analytics** | Keyword search (BM25), semantic search (embeddings), hybrid search, duplicate paper detection (MinHash/LSH), citation ranking (PageRank), and OLAP analytics (DuckDB). |
| **Siddharth** | **Recommendations & AI** | Paper and researcher recommendations, co-saved patterns (FP-Growth), trending topics (sliding window & Z-score), spam detection (Isolation Forest), and local RAG research assistant. |

---

## Folder Structure

```text
Research-Commons/
│
├── frontend/             # React + Vite + Tailwind CSS frontend application
│   └── README.md
│
├── backend/              # FastAPI application, data collection scripts, and API routes
│   └── README.md
│
├── search/               # BM25, semantic search, duplicate detection, and DuckDB analytics
│   └── README.md
│
├── recommendations/      # Recommendation algorithms, trending topics, and RAG assistant
│   └── README.md
│
├── data/                 # Datasets directory (large raw files ignored by Git)
│   ├── raw/              # Raw data collected from OpenAlex / arXiv (.gitkeep)
│   ├── processed/        # Cleaned and normalized datasets (.gitkeep)
│   ├── synthetic/        # Synthetic users, posts, and interaction data (.gitkeep)
│   └── ground_truth/     # Evaluation datasets and test cases (.gitkeep)
│
├── database/             # PostgreSQL schema, pgvector configs, and seed SQL scripts
│   └── README.md
│
├── evaluation/           # Benchmark scripts, test metrics, and accuracy evaluations
│   └── README.md
│
├── docs/                 # Architecture diagrams, API specifications, and notes
│   └── README.md
│
├── .gitignore            # Git ignore configuration
└── README.md             # Project overview and setup instructions
```

---

## Git Branches and Workflow

To allow all four members to work independently without merge conflicts, work is split across dedicated branches:

- **`main`**: The primary stable branch. Do not commit untested code directly here.
- **`frontend`**: Assigned to **Poorna** for developing the React user interface and UI components.
- **`data-backend`**: Assigned to **Mokshith** for database schemas, paper ingestion, and FastAPI endpoints.
- **`suhas-search`**: Assigned to **Suhas** for search engines, duplicate detection, and DuckDB analytics.
- **`siddharth-ai`**: Assigned to **Siddharth** for recommendation algorithms, trend/spam detection, and RAG assistant.

---

## Getting Started

### 1. Clone the Repository
```bash
git clone <repository-url>
cd research-commons
```

### 2. Switch to Your Assigned Working Branch
Run the checkout command for your assigned branch:

- **Poorna (Frontend):**
  ```bash
  git checkout frontend
  ```
- **Mokshith (Database & Backend):**
  ```bash
  git checkout data-backend
  ```
- **Suhas (Search & Analytics):**
  ```bash
  git checkout suhas-search
  ```
- **Siddharth (Recommendations & AI):**
  ```bash
  git checkout siddharth-ai
  ```

### 3. Check Status
```bash
git status
```
Each member can now develop their respective module independently inside their module folder.
