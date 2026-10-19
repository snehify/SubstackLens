# SubstackLens — Hybrid Search Engine for Newsletter Discovery

SubstackLens is a newsletter discovery platform that indexes publicly available RSS/Atom feeds and helps users discover articles through **keyword search and semantic search**. Built with FastAPI, SQLite FTS5, and Next.js, it combines traditional full-text retrieval with meaning-based similarity search.

## Features

- **Keyword search:** Search indexed articles using SQLite FTS5.
- **Semantic search:** Discover conceptually related articles using text embeddings.
- **Publication filtering:** Narrow results to a selected publication.
- **Pagination:** Browse results in manageable pages.
- **RSS/Atom ingestion:** Register feeds and index available article metadata.
- **Feed management:** View registered feeds and ingestion status.
- **Automatic ingestion:** Refresh registered feeds on a configured schedule.
- **API documentation:** Explore endpoints using FastAPI Swagger UI.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript, CSS |
| Backend | Python, FastAPI |
| Keyword search | SQLite FTS5 |
| Semantic search | Sentence Transformers, text embeddings |
| Feed ingestion | feedparser |
| API documentation | Swagger UI / OpenAPI |
| Version control | Git, GitHub |

## Architecture

```text
Public RSS / Atom Feeds
          |
          v
    Feed Ingestion
          |
          v
   SQLite Database
     /         \
    v           v
FTS5 Index   Article Text
    |           |
    v           v
Keyword      Semantic
Search       Embeddings
    \           /
     v         v
      FastAPI
          |
          v
 Next.js Frontend
          |
          v
 Search Results, Filters,
 Pagination and Feed Status
```

## Getting Started

### Prerequisites

- Python version compatible with the project's dependencies
- Node.js 20 or later
- npm
- Internet connection for the initial semantic-model download

### 1. Clone the repository

```powershell
git clone https://github.com/snehify/SubstackLens.git
cd SubstackLens
```

### 2. Start the backend

Open PowerShell in the project directory:

```powershell
cd backend

py -3.14 -m venv .venv-semantic

& ".\.venv-semantic\Scripts\Activate.ps1"

python -m pip install --upgrade pip
pip install -r requirements.txt

python -m uvicorn app.main:app --reload --port 8000
```

If you already have a compatible virtual environment, activate it instead of creating another one.

Backend API: http://localhost:8000

Swagger UI: http://localhost:8000/docs

### 3. Start the frontend

Open a second terminal from the project directory:

```powershell
cd frontend

npm install
npm run dev -- --port 3000
```

Open the frontend at http://localhost:3000.

### 4. Register a feed

With the backend running, use PowerShell:

```powershell
$body = @{
    url = "https://importai.substack.com/feed"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8000/feeds" `
    -ContentType "application/json" `
    -Body $body
```

### 5. Ingest articles

Refresh registered feeds:

```powershell
Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8000/ingest"
```

Feed availability and the number of entries returned depend on each feed.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | API health and index statistics |
| GET | `/search` | Full-text keyword search |
| GET | `/semantic-search` | Meaning-based search |
| GET | `/publications` | List indexed publications |
| GET | `/feeds` | List registered feeds and their status |
| POST | `/feeds` | Register an RSS/Atom feed |
| POST | `/ingest` | Refresh registered feeds |

Example keyword query:

```text
GET /search?q=AI&limit=10&offset=0
```

Example semantic query:

```text
GET /semantic-search?q=how%20AI%20models%20learn&limit=10&offset=0
```

Both search modes support publication filtering and pagination.

## Search Approaches

**Keyword search** uses SQLite FTS5 to retrieve articles matching the query terms.

**Semantic search** converts article text and the user's query into numerical embeddings, then ranks articles using vector similarity. The embedding model may download the first time semantic search is used.

## Project Structure

```text
SubstackLens/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── ingest.py
│   │   └── semantic.py
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── package.json
│   └── package-lock.json
├── .gitignore
└── README.md
```

## Future Improvements

- Automated tests for search and ingestion
- Improved embedding storage and incremental indexing
- Search relevance evaluation
- Deployment with a public frontend and backend
- Authentication, rate limiting, and monitoring
- A scalable search index for larger collections

## Responsible Use

SubstackLens indexes publicly available feed content and metadata. It does not intentionally scrape paywalled articles. Respect applicable website terms, copyright, and feed rate limits.

---

*An independent newsletter discovery project; not affiliated with Substack.*
