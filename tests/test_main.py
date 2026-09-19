from src.config import Config
from src.main import run
from src.rakuten_client import RakutenAPIError
from src.storage import init_db


def make_item(item_code, keyword, source_type):
    return {
        "item_code": item_code,
        "item_name": "商品",
        "price": 1000,
        "item_url": "https://item.rakuten.co.jp/shop/x/",
        "affiliate_url": "https://hb.afl.rakuten.co.jp/x",
        "shop_name": "ショップ",
        "image_url": "https://image.rakuten.co.jp/x.jpg",
        "source_keyword": keyword,
        "source_type": source_type,
    }


def test_run_aggregates_search_and_ranking_results(tmp_path):
    config = Config(
        application_id="app",
        affiliate_id="aff",
        access_key="key",
        allowed_website="example.com",
        keywords=["コーヒー豆"],
        genre_ids=["100227"],
    )
    conn = init_db(str(tmp_path / "products.db"))

    def fake_search(application_id, affiliate_id, access_key, allowed_website, keyword):
        return [make_item("S001", keyword, "search")]

    def fake_ranking(application_id, affiliate_id, access_key, allowed_website, genre_id):
        return [make_item("R001", genre_id, "ranking")]

    result = run(
        config,
        conn,
        search_fn=fake_search,
        ranking_fn=fake_ranking,
        sleep_fn=lambda seconds: None,
    )

    assert result == {"inserted": 2, "updated": 0, "errors": 0}
    conn.close()


def test_run_continues_after_one_keyword_fails(tmp_path):
    config = Config(
        application_id="app",
        affiliate_id="aff",
        access_key="key",
        allowed_website="example.com",
        keywords=["失敗キーワード", "成功キーワード"],
        genre_ids=[],
    )
    conn = init_db(str(tmp_path / "products.db"))

    def fake_search(application_id, affiliate_id, access_key, allowed_website, keyword):
        if keyword == "失敗キーワード":
            raise RakutenAPIError("boom")
        return [make_item("S002", keyword, "search")]

    def fake_ranking(application_id, affiliate_id, access_key, allowed_website, genre_id):
        return []

    result = run(
        config,
        conn,
        search_fn=fake_search,
        ranking_fn=fake_ranking,
        sleep_fn=lambda seconds: None,
    )

    assert result == {"inserted": 1, "updated": 0, "errors": 1}
    conn.close()
