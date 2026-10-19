import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "search.db"

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                author TEXT DEFAULT '',
                publication TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                published TEXT DEFAULT '',
                feed_url TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
                title, author, publication, summary, content='posts', content_rowid='id'
            )
        """)
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
              INSERT INTO posts_fts(rowid,title,author,publication,summary)
              VALUES(new.id,new.title,new.author,new.publication,new.summary);
            END;
            CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
              INSERT INTO posts_fts(posts_fts,rowid,title,author,publication,summary)
              VALUES('delete',old.id,old.title,old.author,old.publication,old.summary);
            END;
            CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
              INSERT INTO posts_fts(posts_fts,rowid,title,author,publication,summary)
              VALUES('delete',old.id,old.title,old.author,old.publication,old.summary);
              INSERT INTO posts_fts(rowid,title,author,publication,summary)
              VALUES(new.id,new.title,new.author,new.publication,new.summary);
            END;
            CREATE TABLE IF NOT EXISTS feeds (
                url TEXT PRIMARY KEY,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
