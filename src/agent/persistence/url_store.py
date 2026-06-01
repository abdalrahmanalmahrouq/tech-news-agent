import sqlite3
import os
from datetime import datetime, timedelta

def get_db_path():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, "data", "news_agent.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path


def init_url_store():
    conn = sqlite3.connect(get_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_urls (
            url TEXT PRIMARY KEY,
            seen_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def is_seen(url: str, days: int = 7) -> bool:
    conn = sqlite3.connect(get_db_path())
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    row = conn.execute(
        "SELECT url FROM seen_urls WHERE url = ? AND seen_at > ?",
        (url, cutoff)
    ).fetchone()
    conn.close()
    return row is not None

def mark_seen(urls: list[str]):
    conn = sqlite3.connect(get_db_path())
    seen_at = datetime.utcnow().isoformat()
    conn.executemany(
        "INSERT OR IGNORE INTO seen_urls (url, seen_at) VALUES (?, ?)",
        [(url, seen_at) for url in urls]
    )
    conn.commit()
    conn.close()