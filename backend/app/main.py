
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from .db import connect, init_db
from .ingest import refresh_feed as _refresh_feed
from .semantic import semantic_rank
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

# Refresh feeds every 30 minutes by default.
# Set INGEST_INTERVAL_SECONDS to change this; minimum is 60 seconds.
def utc_timestamp() -> str:
    """Return the current UTC time as an ISO timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_feed_status_table() -> None:
    """Create the feed status table and initialize existing feeds."""
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feed_status (
                url TEXT PRIMARY KEY,
                last_attempt_at TEXT NOT NULL DEFAULT '',
                last_success_at TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'never',
                processed_count INTEGER NOT NULL DEFAULT 0,
                error TEXT NOT NULL DEFAULT ''
            )
        """)

        # Existing registered feeds will receive a status record.
        conn.execute("""
            INSERT OR IGNORE INTO feed_status (url)
            SELECT url FROM feeds
        """)


def refresh_feed(url: str) -> int:
    """
    Refresh one feed while recording its ingestion status.

    The existing scheduler and manual ingestion route can continue
    calling refresh_feed(url) as before.
    """
    ensure_feed_status_table()
    attempted_at = utc_timestamp()

    with connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO feed_status (url)
            VALUES (?)
        """, (url,))

        conn.execute("""
            UPDATE feed_status
            SET last_attempt_at = ?,
                status = 'running',
                error = ''
            WHERE url = ?
        """, (attempted_at, url))

    try:
        # Call the original feed-processing function.
        processed = _refresh_feed(url)

    except Exception as exc:
        with connect() as conn:
            conn.execute("""
                UPDATE feed_status
                SET status = 'error',
                    error = ?
                WHERE url = ?
            """, (str(exc)[:1000], url))
        raise

    with connect() as conn:
        conn.execute("""
            UPDATE feed_status
            SET status = 'success',
                last_success_at = ?,
                processed_count = ?,
                error = ''
            WHERE url = ?
        """, (utc_timestamp(), processed, url))

    return processed
INGEST_INTERVAL_SECONDS = max(
    60, int(os.getenv("INGEST_INTERVAL_SECONDS", "1800"))
)


async def scheduled_ingestion():
    """Refresh all registered feeds periodically."""
    while True:
        await asyncio.sleep(INGEST_INTERVAL_SECONDS)

        try:
            with connect() as conn:
                urls = [
                    row["url"]
                    for row in conn.execute(
                        "SELECT url FROM feeds"
                    ).fetchall()
                ]

            for url in urls:
                try:
                    count = await asyncio.to_thread(refresh_feed, url)
                    logger.info(
                        "Scheduled refresh processed %s entries from %s",
                        count,
                        url,
                    )
                except Exception:
                    logger.exception(
                        "Scheduled ingestion failed for %s", url
                    )

        except Exception:
            logger.exception("Scheduled ingestion cycle failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(scheduled_ingestion())

    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Substack Search API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FeedRequest(BaseModel):
    url: HttpUrl

@app.get("/semantic-search")
def semantic_search(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    publication: str | None = Query(default=None, max_length=200),
):
    """Search articles by semantic similarity."""
    if not q.strip():
        raise HTTPException(
            status_code=422,
            detail="Enter a search query.",
        )

    with connect() as conn:
        rows = conn.execute("""
            SELECT
                id, url, title, author, publication, summary, published
            FROM posts
            ORDER BY id DESC
        """).fetchall()

    posts = [dict(row) for row in rows]

    try:
        ranked = semantic_rank(posts, q.strip())
    except Exception as exc:
        logger.exception("Semantic search failed")
        raise HTTPException(
            status_code=503,
            detail=(
                "Semantic search could not load or run its embedding model. "
                "Check the backend logs and internet connection."
            ),
        ) from exc

    # Apply the selected publication filter before pagination.
    if publication and publication.strip():
        selected = publication.strip()
        ranked = [
            post
            for post in ranked
            if post.get("publication") == selected
        ]

    total = len(ranked)
    results = ranked[offset:offset + limit]

    return {
        "query": q,
        "mode": "semantic",
        "count": len(results),
        "total": total,
        "limit": limit,
        "offset": offset,
        "publication": publication,
        "has_more": offset + len(results) < total,
        "results": results,
    }


@app.get("/feeds")
def list_feeds():
    """List registered feeds and their ingestion status."""
    ensure_feed_status_table()

    with connect() as conn:
        rows = conn.execute("""
            SELECT
                f.url,
                f.added_at,
                COUNT(p.id) AS indexed_posts,
                COALESCE(MAX(p.published), '') AS latest_published,
                COALESCE(s.status, 'never') AS status,
                COALESCE(s.last_attempt_at, '') AS last_attempt_at,
                COALESCE(s.last_success_at, '') AS last_success_at,
                COALESCE(s.processed_count, 0) AS last_processed_count,
                COALESCE(s.error, '') AS last_error
            FROM feeds f
            LEFT JOIN posts p
                ON p.feed_url = f.url
            LEFT JOIN feed_status s
                ON s.url = f.url
            GROUP BY
                f.url,
                f.added_at,
                s.status,
                s.last_attempt_at,
                s.last_success_at,
                s.processed_count,
                s.error
            ORDER BY f.added_at DESC, f.url
        """).fetchall()

    return {
        "count": len(rows),
        "feeds": [dict(row) for row in rows],
    }

@app.get("/health")
def health():
    with connect() as conn:
        post_count = conn.execute(
            "SELECT COUNT(*) FROM posts"
        ).fetchone()[0]
        feed_count = conn.execute(
            "SELECT COUNT(*) FROM feeds"
        ).fetchone()[0]

    return {
        "status": "ok",
        "api_version": app.version,
        "indexed_posts": post_count,
        "registered_feeds": feed_count,
        "ingestion_interval_seconds": INGEST_INTERVAL_SECONDS,
    }


@app.get("/publications")
def list_publications():
    """Return available publications for the frontend filter."""
    with connect() as conn:
        rows = conn.execute("""
            SELECT publication, COUNT(*) AS post_count
            FROM posts
            WHERE TRIM(publication) <> ''
            GROUP BY publication
            ORDER BY LOWER(publication)
        """).fetchall()

    return {
        "publications": [
            {
                "name": row["publication"],
                "post_count": row["post_count"],
            }
            for row in rows
        ]
    }


@app.get("/search")
def search(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    publication: str | None = Query(default=None, max_length=200),
):
    tokens = [
        token.replace('"', '""')
        for token in q.split()
        if token.strip()
    ]

    if not tokens:
        return {
            "query": q,
            "count": 0,
            "total": 0,
            "limit": limit,
            "offset": offset,
            "publication": publication,
            "results": [],
        }

    # Ordinary search words are quoted to avoid exposing raw FTS operators.
    match_query = " AND ".join(
        f'"{token}"' for token in tokens
    )

    base_sql = """
        FROM posts_fts
        JOIN posts p ON p.id = posts_fts.rowid
        WHERE posts_fts MATCH ?
    """
    params = [match_query]

    if publication and publication.strip():
        base_sql += " AND p.publication = ? COLLATE NOCASE"
        params.append(publication.strip())

    try:
        with connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) " + base_sql,
                params,
            ).fetchone()[0]

            rows = conn.execute(
                """
                SELECT p.id, p.url, p.title, p.author,
                       p.publication, p.summary, p.published,
                       bm25(posts_fts, 5.0, 2.0, 2.0, 1.0) AS score
                """
                + base_sql
                + " ORDER BY score ASC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()

    except Exception:
        logger.exception("Search failed for query %r", q)
        return {
            "query": q,
            "count": 0,
            "total": 0,
            "limit": limit,
            "offset": offset,
            "publication": publication,
            "results": [],
            "hint": "Try simpler keywords or check the publication filter.",
        }

    return {
        "query": q,
        "count": len(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
        "publication": publication,
        "has_more": offset + len(rows) < total,
        "results": [dict(row) for row in rows],
    }


@app.post("/feeds")
def add_feed(body: FeedRequest):
    url = str(body.url)

    if not url.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="Only HTTPS feed URLs are accepted.",
        )

    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO feeds(url) VALUES(?)",
            (url,),
        )

    return {"registered": True, "url": url}


@app.post("/ingest")
def ingest_all():
    """Manually refresh every registered feed."""
    with connect() as conn:
        urls = [
            row["url"]
            for row in conn.execute(
                "SELECT url FROM feeds"
            ).fetchall()
        ]

    results = []

    for url in urls:
        try:
            count = refresh_feed(url)
            results.append({"url": url, "indexed": count})
        except Exception as exc:
            logger.exception("Ingestion failed for %s", url)
            results.append({
                "url": url,
                "error": str(exc)[:200],
            })

    return {
        "feeds_processed": len(urls),
        "results": results,
    }
