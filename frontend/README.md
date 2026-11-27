# Wiz-Search Sphere frontend

Wiz-Search Sphere is the React + Vite client for the Chanakya University research community. Its visual theme uses deep maroon, antique gold, and warm neutrals.

## Run locally

From the repository root, start the supporting services and API:

```powershell
docker compose up -d postgres minio
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
ollama pull qwen2.5:3b
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Install Ollama before pulling the model. Ollama must be running locally at `http://127.0.0.1:11434`; if its background service is not already running, start it with `ollama serve`. The selected model can be changed with `OLLAMA_MODEL` in `backend/.env`.

In another terminal, configure and start the frontend:

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm install
npm run dev
```

The frontend environment file should set `VITE_API_BASE_URL=http://localhost:8000`. Restart Vite after changing it. If the backend is unavailable, the UI remains usable with clearly marked sample data; the four **Demo** buttons provide one-click Student, Faculty, Researcher, and Admin access.

## Screens

- **Sign in / registration:** connects to the FastAPI login and registration endpoints. Account registration includes role and department.
- **Community feed:** browses posts, creates posts with tags, and adds comments.
- **Personal library:** saves papers, edits collection names and private notes, and surfaces unsaved recommendations to grow a reading list.
- **Research discussions:** comments attach directly to papers and theses, in addition to feed-post comments. In demo mode, comments remain in browser memory.
- **Unified search:** searches papers, library items, university members, and discussions across the data loaded by the API.
- **Research assistant:** sends questions and recent conversation turns to the local Ollama model through FastAPI. The backend ranks relevant paper abstracts as context and returns expandable citations. Demo Student and Faculty accounts can use it too; their sample papers are supplied as context. If Ollama is unavailable, the UI reports the error rather than showing a fabricated answer.
- **Admin console:** administrator-role accounts see campus totals and connected anomaly-review signals. Automated flags are review prompts, not proof of misconduct.
- **Research analytics:** interactive six-month activity, department, collaboration, topic, and top-paper views. In connected mode these charts use PostgreSQL aggregates; demo numbers are marked as illustrative.

The demo/offline records are illustrative and are not saved to the backend. Assistant prompts and selected paper abstracts are sent only to the local Ollama service; no external AI provider is used. In connected mode, search filters records returned by the API; it is not wired to the team's BM25/semantic unified-search endpoint.

## Session and security

After login or registration, the client stores the returned user profile in `localStorage` under `research_commons_user` and restores it on reload. Logging out removes that entry. This is client-side convenience only: browser storage can be edited and must not be treated as authentication or authorization.

The merged backend currently returns a placeholder access token and its data routes do not validate sessions or enforce user-scoped access. Registration also allows selecting Admin. Do not use this implementation as a private or production client portal until the backend provides secure password hashing, validated sessions, role-based authorization, and durable account storage.

## Stack

- React and Vite
- Tailwind CSS and custom application styles
- Recharts
- Lucide React icons
