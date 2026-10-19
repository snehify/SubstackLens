# Substack Search Engine — Keyword Search MVP

A small independent search engine for publicly available Substack posts. It indexes RSS feed entries into SQLite FTS5 and exposes a FastAPI search API. The Next.js UI searches the local index.

## Stack
- Frontend: Next.js App Router, TypeScript, CSS
- API: Python, FastAPI
- Search index / metadata store: SQLite FTS5
- Ingestion: RSS feeds via `feedparser`
- Deployment-ready next step: replace SQLite FTS5 with OpenSearch when the index grows.

## Requirements
- Python 3.10+
- Node.js 20+
- npm

## Run the API
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

## Add RSS feeds
In another terminal, activate the backend environment and run:
```bash
python -m app.ingest https://example.substack.com/feed
```
Use a real, public Substack RSS feed URL. Respect feed/site terms, robots guidance, rate limits, and copyright. This MVP indexes feed metadata and descriptions; it does not scrape paywalled articles.

## Run the frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:3000.

## API
- `GET /health`
- `GET /search?q=artificial%20intelligence&limit=20`
- `POST /feeds?url=https://publication.substack.com/feed`
- `POST /ingest` to refresh all registered feeds

## Notes
- The database is created automatically at `backend/search.db`.
- Empty index? Register and ingest a public RSS feed using the command above.
- Search is lexical keyword search, not semantic AI search.
- For production, add authentication/rate limiting, scheduled ingestion, deduplication monitoring, tests, Docker, and OpenSearch.
