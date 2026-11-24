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

## Getting Started (Planned)
1. Set up a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn psycopg2-binary sqlalchemy requests
   ```
3. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```
