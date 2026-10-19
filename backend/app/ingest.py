import sys
import html
import re
import feedparser
from .db import connect, init_db

def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()

def refresh_feed(url: str) -> int:
    parsed = feedparser.parse(url)
    if parsed.bozo and not parsed.entries:
        raise ValueError("Could not parse feed")
    publication = clean_text(parsed.feed.get("title", ""))
    inserted = 0
    with connect() as conn:
        for entry in parsed.entries:
            link = entry.get("link")
            title = clean_text(entry.get("title", ""))
            if not link or not title:
                continue
            summary = clean_text(entry.get("summary", entry.get("description", "")))[:5000]
            author = clean_text(entry.get("author", ""))
            published = entry.get("published", entry.get("updated", ""))
            cur = conn.execute("""
                INSERT INTO posts(url,title,author,publication,summary,published,feed_url)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(url) DO UPDATE SET
                  title=excluded.title, author=excluded.author,
                  publication=excluded.publication, summary=excluded.summary,
                  published=excluded.published, feed_url=excluded.feed_url
            """, (link, title, author, publication, summary, published, url))
            inserted += 1
    return inserted

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m app.ingest https://publication.substack.com/feed")
        raise SystemExit(2)
    init_db()
    url = sys.argv[1]
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO feeds(url) VALUES(?)", (url,))
    count = refresh_feed(url)
    print(f"Processed {count} feed entries from {url}")

if __name__ == "__main__":
    main()
