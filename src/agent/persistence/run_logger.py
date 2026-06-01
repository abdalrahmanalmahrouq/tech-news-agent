import sqlite3
import os
from datetime import datetime


def get_db_path():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, "data", "news_agent.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path


def init_run_logs():
    conn = sqlite3.connect(get_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS run_logs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT,
            completed_at TEXT,
            duration_ms INTEGER,
            articles_scraped INTEGER,
            articles_validated INTEGER,
            articles_rejected INTEGER,
            status TEXT,
            errors TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_run(run_meta: dict, raw_articles: list, validated: list):
    init_run_logs()

    started_at = run_meta.get("started_at")
    completed_at = datetime.utcnow().isoformat()

    duration_ms = None
    if started_at:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(completed_at)
        duration_ms = int((end - start).total_seconds() * 1000)

    rejected = run_meta.get("rejected", [])
    errors = run_meta.get("errors", [])

    conn = sqlite3.connect(get_db_path())
    conn.execute("""
        INSERT OR REPLACE INTO run_logs
        (run_id, started_at, completed_at, duration_ms, articles_scraped, articles_validated, articles_rejected, status, errors)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_meta.get("run_id"),
        started_at,
        completed_at,
        duration_ms,
        len(raw_articles),
        len(validated),
        len(rejected),
        run_meta.get("status", "completed"),
        str(errors) if errors else None,
    ))
    conn.commit()
    conn.close()

    print(f"\n📊 Run logged:")
    print(f"   Run ID:    {run_meta.get('run_id')}")
    print(f"   Duration:  {duration_ms}ms")
    print(f"   Scraped:   {len(raw_articles)}")
    print(f"   Validated: {len(validated)}")
    print(f"   Rejected:  {len(rejected)}")