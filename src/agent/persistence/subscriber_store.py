import os
import sqlite3
from datetime import datetime


def get_db_path():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, "data", "news_agent.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return db_path


def init_subscribers():
    conn = sqlite3.connect(get_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            email      TEXT PRIMARY KEY,
            name       TEXT,
            active     INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_active_subscribers() -> list[dict]:
    conn = sqlite3.connect(get_db_path())
    rows = conn.execute(
        "SELECT email, name FROM subscribers WHERE active = 1"
    ).fetchall()
    conn.close()
    return [{"email": row[0], "name": row[1]} for row in rows]


def add_subscriber(email: str, name: str = "") -> None:
    init_subscribers()
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        "INSERT OR IGNORE INTO subscribers (email, name, active, created_at) VALUES (?, ?, 1, ?)",
        (email, name, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    print(f"✓ Subscriber added: {email} ({name})")


def deactivate_subscriber(email: str) -> None:
    conn = sqlite3.connect(get_db_path())
    conn.execute("UPDATE subscribers SET active = 0 WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    print(f"✓ Subscriber deactivated: {email}")


def list_subscribers() -> None:
    subs = get_active_subscribers()
    if not subs:
        print("  No active subscribers.")
        return
    for s in subs:
        print(f"  {s['email']}  ({s['name'] or '—'})")


# CLI for managing subscribers without writing code
# Usage:
#   uv run python -m agent.persistence.subscriber_store add email@x.com "Name"
#   uv run python -m agent.persistence.subscriber_store remove email@x.com
#   uv run python -m agent.persistence.subscriber_store list
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Commands: add <email> [name]  |  remove <email>  |  list")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "add" and len(sys.argv) >= 3:
        name = sys.argv[3] if len(sys.argv) > 3 else ""
        add_subscriber(sys.argv[2], name)
    elif cmd == "remove" and len(sys.argv) >= 3:
        deactivate_subscriber(sys.argv[2])
    elif cmd == "list":
        list_subscribers()
    else:
        print("Commands: add <email> [name]  |  remove <email>  |  list")