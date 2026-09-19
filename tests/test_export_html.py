from src.export_html import render_html, export
from src.storage import init_db, upsert_items


def make_item(item_code="I001"):
    return {
        "item_code": item_code,
        "item_name": "テスト<商品>",
        "price": 1500,
        "item_url": "https://item.rakuten.co.jp/shop/I001/",
        "affiliate_url": "https://hb.afl.rakuten.co.jp/xxx",
        "shop_name": "テストショップ",
        "image_url": "https://image.rakuten.co.jp/shop/cabinet/I001.jpg",
        "source_keyword": "コーヒー豆",
        "source_type": "search",
    }


def test_render_html_includes_item_details_and_escapes_html():
    html = render_html([make_item()])

    assert "テスト&lt;商品&gt;" in html
    assert "1,500円" in html
    assert "テストショップ" in html
    assert 'href="https://hb.afl.rakuten.co.jp/xxx"' in html
    assert "1件" in html


def test_render_html_handles_missing_image_url():
    item = make_item()
    item["image_url"] = ""

    html = render_html([item])

    assert "<img" not in html


def test_export_writes_html_file_from_db(tmp_path):
    db_path = str(tmp_path / "products.db")
    output_path = str(tmp_path / "products.html")
    conn = init_db(db_path)
    upsert_items(conn, [make_item()])
    conn.close()

    export(db_path=db_path, output_path=output_path)

    with open(output_path, encoding="utf-8") as f:
        content = f.read()
    assert "テスト&lt;商品&gt;" in content
