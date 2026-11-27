# Backend Module

## Module Overview
This folder contains the core backend services, data ingestion pipelines, and REST APIs for **Research Commons**.

- **Assigned Team Member:** Mokshith
- **Primary Tech Stack:** Python, FastAPI, PostgreSQL, MinIO, Uvicorn

---

## Planned Responsibilities & Features
1. **Paper Data Collection:**
   - Scripts to harvest paper metadata, abstracts, and citations from sources like OpenAlex and arXiv (minimum 500 records).
   - Storage of raw harvested responses in MinIO / `data/raw/`.
2. **Database Integration & Models:**
   - Relational schemas and ORM models for users, profiles, papers, posts, comments, and collections.
   - Initial sample seed scripts for users, posts, and realistic activity logs.
3. **Core REST APIs:**
   - User authentication and profile management endpoints.
   - Posts, feeds, comments, and discussions endpoints.
   - Library, bookmarks, and paper collection management endpoints.
4. **Test & Ground Truth Datasets:**
   - Seed datasets with planted examples of duplicate papers, spam, and topic spikes (documented in `data/ground_truth/`).

---

## Local setup and data loading
1. Set up a Python virtual environment and install the backend dependencies:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   pip install -r backend/requirements.txt -r recommendations/requirements.txt
   ```
2. Start PostgreSQL with pgvector and MinIO:
   ```bash
   docker compose up -d postgres minio
   ```
3. Fetch papers from OpenAlex and arXiv, generate the synthetic community data, and load both into PostgreSQL:
   ```bash
   python backend/fetch_papers.py
   python backend/generate_synthetic.py
   python backend/load_to_db.py
   ```
   The generated raw, processed, and synthetic JSON files are local data outputs and are not committed to Git.

   To deliberately clear the database before loading, pass `--reset` to the loader. This truncates the existing application tables and resets their identity sequences:
   ```bash
   python backend/load_to_db.py --reset
   ```
4. Start the API from the repository root:
   ```bash
   uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

## Paper discussions and analytics

The API supports comments attached directly to a research paper or thesis through
`GET /api/papers/{paper_id}/comments` and `POST /api/papers/{paper_id}/comments`.
The `paper_comments` table is included in `database/schema.sql`; API startup also
creates this table and its index when connecting to an existing PostgreSQL database.
This migration only adds the table and does not alter existing records.

The analytics endpoints aggregate activity, departments, cross-department follows,
and paper concepts from PostgreSQL when connected. Admin anomaly scores are
automated review signals and should not be treated as proof of abusive behavior.
