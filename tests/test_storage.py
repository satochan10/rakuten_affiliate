import sqlite3

from src.storage import init_db, upsert_items


def make_item(item_code="I001", price=1000):
    return {
        "item_code": item_code,
        "item_name": "テスト商品",
        "price": price,
        "item_url": "https://item.rakuten.co.jp/shop/I001/",
        "affiliate_url": "https://hb.afl.rakuten.co.jp/xxx",
        "shop_name": "テストショップ",
        "image_url": "https://image.rakuten.co.jp/shop/cabinet/I001.jpg",
        "source_keyword": "コーヒー豆",
        "source_type": "search",
    }


def test_init_db_creates_items_table(tmp_path):
    db_path = str(tmp_path / "products.db")
    conn = init_db(db_path)

    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='items'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_upsert_items_inserts_new_item(tmp_path):
    conn = init_db(str(tmp_path / "products.db"))

    result = upsert_items(conn, [make_item()])

    assert result == {"inserted": 1, "updated": 0}
    row = conn.execute(
        "SELECT item_code, price, posted_flag FROM items WHERE item_code = 'I001'"
    ).fetchone()
    assert row == ("I001", 1000, 0)
    conn.close()


def test_upsert_items_updates_existing_item_price(tmp_path):
    conn = init_db(str(tmp_path / "products.db"))
    upsert_items(conn, [make_item(price=1000)])

    result = upsert_items(conn, [make_item(price=1200)])

    assert result == {"inserted": 0, "updated": 1}
    row = conn.execute(
        "SELECT price FROM items WHERE item_code = 'I001'"
    ).fetchone()
    assert row == (1200,)
    conn.close()


def test_upsert_items_does_not_duplicate_rows(tmp_path):
    conn = init_db(str(tmp_path / "products.db"))
    upsert_items(conn, [make_item()])
    upsert_items(conn, [make_item()])

    count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    assert count == 1
    conn.close()
