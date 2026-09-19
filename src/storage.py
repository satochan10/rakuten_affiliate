import sqlite3
from datetime import datetime, timezone

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    item_code TEXT PRIMARY KEY,
    item_name TEXT,
    price INTEGER,
    item_url TEXT,
    affiliate_url TEXT,
    shop_name TEXT,
    image_url TEXT,
    source_keyword TEXT,
    source_type TEXT,
    first_seen_at TEXT,
    last_seen_at TEXT,
    posted_flag INTEGER DEFAULT 0
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(_SCHEMA)
    conn.commit()
    return conn


def upsert_items(conn: sqlite3.Connection, items: list[dict]) -> dict:
    inserted = 0
    updated = 0
    now = datetime.now(timezone.utc).isoformat()

    for item in items:
        existing = conn.execute(
            "SELECT 1 FROM items WHERE item_code = ?", (item["item_code"],)
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO items (
                    item_code, item_name, price, item_url, affiliate_url,
                    shop_name, image_url, source_keyword, source_type,
                    first_seen_at, last_seen_at, posted_flag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    item["item_code"],
                    item["item_name"],
                    item["price"],
                    item["item_url"],
                    item["affiliate_url"],
                    item["shop_name"],
                    item["image_url"],
                    item["source_keyword"],
                    item["source_type"],
                    now,
                    now,
                ),
            )
            inserted += 1
        else:
            conn.execute(
                """
                UPDATE items
                SET item_name = ?, price = ?, item_url = ?, affiliate_url = ?,
                    shop_name = ?, image_url = ?, source_keyword = ?,
                    source_type = ?, last_seen_at = ?
                WHERE item_code = ?
                """,
                (
                    item["item_name"],
                    item["price"],
                    item["item_url"],
                    item["affiliate_url"],
                    item["shop_name"],
                    item["image_url"],
                    item["source_keyword"],
                    item["source_type"],
                    now,
                    item["item_code"],
                ),
            )
            updated += 1

    conn.commit()
    return {"inserted": inserted, "updated": updated}
