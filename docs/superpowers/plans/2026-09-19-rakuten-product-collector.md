# 楽天商品データ収集システム Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 楽天市場API(商品検索・ランキング)から商品データを定期取得し、SQLiteに重複排除して蓄積するローカルPythonツールを作る。

**Architecture:** `src/config.py`(設定読込)→ `src/rakuten_client.py`(API呼び出し)→ `src/storage.py`(SQLite UPSERT)を `src/main.py` がオーケストレーションする3層構成。投稿機能は含まない。

**Tech Stack:** Python 3.11+, `requests`, `PyYAML`, `python-dotenv`, `pytest`, `sqlite3`(標準ライブラリ)

**Spec:** `docs/superpowers/specs/2026-09-19-rakuten-product-collector-design.md`

## Global Constraints

- APIキー(Application ID, Affiliate ID)は `.env` に置き、コミットしない(`.gitignore` 対象)
- 楽天APIへのリクエスト間隔は約1秒あける(レート制限対策)
- API呼び出し失敗時は指数バックオフで最大3回リトライ、それでも失敗したら該当キーワード/ジャンルをスキップし処理継続(全体を止めない)
- `item_code` を一意キーとしてUPSERT(新規: 全カラム挿入、既存: price・last_seen_at等を更新)
- 実APIへの結合テストは自動テストに含めない(手動確認のみ)

---

### Task 1: プロジェクト scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `keywords.yaml`
- Create: `README.md`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: `keywords.yaml` のスキーマ(`keywords:` リストと `genre_ids:` リスト)を後続タスクが読み込む

- [ ] **Step 1: 依存ライブラリを定義**

`requirements.txt`:
```
requests>=2.31,<3
PyYAML>=6.0,<7
python-dotenv>=1.0,<2
pytest>=8.0,<9
```

- [ ] **Step 2: 環境変数サンプルを作成**

`.env.example`:
```
RAKUTEN_APPLICATION_ID=your_application_id_here
RAKUTEN_AFFILIATE_ID=your_affiliate_id_here
```

- [ ] **Step 3: .gitignore を作成**

`.gitignore`:
```
.env
products.db
app.log
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: キーワード設定ファイルを作成**

`keywords.yaml`:
```yaml
# 商品検索キーワード(IchibaItem/Search API)
keywords:
  - "コーヒー豆"
  - "ワイヤレスイヤホン"

# ジャンル別ランキング取得対象(IchibaItem/Ranking API)
# ジャンルIDは https://webservice.rakuten.co.jp/explorer/api/IchibaGenre/Search/ 等で調べられる
genre_ids:
  - "100227"  # 食品
  - "565571"  # 家電
```

- [ ] **Step 5: README にセットアップ・実行手順を記載**

`README.md`:
```markdown
# 楽天アフィリエイト商品データ収集システム

楽天市場APIから商品情報を定期取得し、SQLite(`products.db`)に蓄積するツール。

## セットアップ

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env を編集し、RAKUTEN_APPLICATION_ID / RAKUTEN_AFFILIATE_ID を設定
```

`keywords.yaml` を編集し、検索したいキーワード・ジャンルIDを設定する。

## 実行

```bash
python src/main.py
```

## cronでの定期実行

`crontab -e` で以下のように登録する(例: 毎日9時に実行):

```
0 9 * * * cd /path/to/05_楽天アフィリエイト && /path/to/venv/bin/python src/main.py >> cron.log 2>&1
```

## テスト

```bash
pytest
```
```

- [ ] **Step 6: 空の `__init__.py` を作成**

`src/__init__.py`: (空ファイル)
`tests/__init__.py`: (空ファイル)

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore keywords.yaml README.md src/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure"
```

---

### Task 2: config.py — 設定読み込み

**Files:**
- Create: `src/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `.env`(`RAKUTEN_APPLICATION_ID`, `RAKUTEN_AFFILIATE_ID`)、`keywords.yaml`(`keywords:`, `genre_ids:`)
- Produces:
  - `class Config`: フィールド `application_id: str`, `affiliate_id: str`, `keywords: list[str]`, `genre_ids: list[str]`
  - `class ConfigError(Exception)`
  - `def load_config(env_path: str = ".env", keywords_path: str = "keywords.yaml") -> Config`(必須値欠如時は `ConfigError` を送出)

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_config.py`:
```python
import os
import pytest
from src.config import load_config, ConfigError


def test_load_config_success(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "RAKUTEN_APPLICATION_ID=app123\n"
        "RAKUTEN_AFFILIATE_ID=aff456\n"
    )
    keywords_file = tmp_path / "keywords.yaml"
    keywords_file.write_text(
        "keywords:\n"
        "  - \"コーヒー豆\"\n"
        "genre_ids:\n"
        "  - \"100227\"\n"
    )

    config = load_config(env_path=str(env_file), keywords_path=str(keywords_file))

    assert config.application_id == "app123"
    assert config.affiliate_id == "aff456"
    assert config.keywords == ["コーヒー豆"]
    assert config.genre_ids == ["100227"]


def test_load_config_missing_application_id_raises(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("RAKUTEN_AFFILIATE_ID=aff456\n")
    keywords_file = tmp_path / "keywords.yaml"
    keywords_file.write_text("keywords: []\ngenre_ids: []\n")

    with pytest.raises(ConfigError, match="RAKUTEN_APPLICATION_ID"):
        load_config(env_path=str(env_file), keywords_path=str(keywords_file))
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'src.config'` または import error)

- [ ] **Step 3: 実装を書く**

`src/config.py`:
```python
from dataclasses import dataclass

import yaml
from dotenv import dotenv_values


class ConfigError(Exception):
    pass


@dataclass
class Config:
    application_id: str
    affiliate_id: str
    keywords: list[str]
    genre_ids: list[str]


def load_config(env_path: str = ".env", keywords_path: str = "keywords.yaml") -> Config:
    env_values = dotenv_values(env_path)

    application_id = env_values.get("RAKUTEN_APPLICATION_ID")
    if not application_id:
        raise ConfigError("RAKUTEN_APPLICATION_ID is not set in .env")

    affiliate_id = env_values.get("RAKUTEN_AFFILIATE_ID")
    if not affiliate_id:
        raise ConfigError("RAKUTEN_AFFILIATE_ID is not set in .env")

    with open(keywords_path, "r", encoding="utf-8") as f:
        keywords_data = yaml.safe_load(f) or {}

    keywords = keywords_data.get("keywords") or []
    genre_ids = keywords_data.get("genre_ids") or []

    return Config(
        application_id=application_id,
        affiliate_id=affiliate_id,
        keywords=[str(k) for k in keywords],
        genre_ids=[str(g) for g in genre_ids],
    )
```

- [ ] **Step 4: テストが通ることを確認**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add config loading from .env and keywords.yaml"
```

---

### Task 3: storage.py — SQLite UPSERT

**Files:**
- Create: `src/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: なし(独立モジュール)
- Produces:
  - `def init_db(db_path: str) -> sqlite3.Connection`(`items` テーブルがなければ作成して接続を返す)
  - `def upsert_items(conn: sqlite3.Connection, items: list[dict]) -> dict`
    - 各 `item` dict は次のキーを持つ: `item_code`, `item_name`, `price`, `item_url`, `affiliate_url`, `shop_name`, `image_url`, `source_keyword`, `source_type`
    - 戻り値: `{"inserted": int, "updated": int}`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_storage.py`:
```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'src.storage'`)

- [ ] **Step 3: 実装を書く**

`src/storage.py`:
```python
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
```

- [ ] **Step 4: テストが通ることを確認**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/storage.py tests/test_storage.py
git commit -m "feat: add SQLite storage with upsert dedup logic"
```

---

### Task 4: rakuten_client.py — 楽天API呼び出し

**Files:**
- Create: `src/rakuten_client.py`
- Test: `tests/test_rakuten_client.py`

**Interfaces:**
- Consumes: なし(独立モジュール、`requests` を使用)
- Produces:
  - `class RakutenAPIError(Exception)`
  - `def search(application_id: str, affiliate_id: str, keyword: str) -> list[dict]`
  - `def ranking(application_id: str, affiliate_id: str, genre_id: str) -> list[dict]`
  - どちらも `src/storage.py` の `upsert_items` が期待する item dict のリストを返す
    (`item_code`, `item_name`, `price`, `item_url`, `affiliate_url`, `shop_name`,
    `image_url`, `source_keyword`, `source_type` を含む)
  - 最大3回リトライ(指数バックオフ: 1秒, 2秒, 4秒)、全て失敗した場合は `RakutenAPIError` を送出

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_rakuten_client.py`:
```python
from unittest.mock import patch, MagicMock

import pytest
import requests

from src.rakuten_client import search, ranking, RakutenAPIError

SEARCH_RESPONSE = {
    "Items": [
        {
            "Item": {
                "itemCode": "shop:I001",
                "itemName": "テストコーヒー豆",
                "itemPrice": 1500,
                "itemUrl": "https://item.rakuten.co.jp/shop/I001/",
                "affiliateUrl": "https://hb.afl.rakuten.co.jp/xxx",
                "shopName": "テストショップ",
                "mediumImageUrls": [
                    {"imageUrl": "https://image.rakuten.co.jp/shop/cabinet/I001.jpg"}
                ],
            }
        }
    ]
}

RANKING_RESPONSE = {
    "Items": [
        {
            "Item": {
                "itemCode": "shop:R001",
                "itemName": "テストイヤホン",
                "itemPrice": 3000,
                "itemUrl": "https://item.rakuten.co.jp/shop/R001/",
                "affiliateUrl": "https://hb.afl.rakuten.co.jp/yyy",
                "shopName": "ランキングショップ",
                "mediumImageUrls": [
                    {"imageUrl": "https://image.rakuten.co.jp/shop/cabinet/R001.jpg"}
                ],
            }
        }
    ]
}


def _mock_response(json_data, status_code=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status.side_effect = (
        None if status_code == 200 else requests.HTTPError(f"status {status_code}")
    )
    return mock_resp


@patch("src.rakuten_client.requests.get")
def test_search_returns_parsed_items(mock_get):
    mock_get.return_value = _mock_response(SEARCH_RESPONSE)

    items = search("app123", "aff456", "コーヒー豆")

    assert len(items) == 1
    item = items[0]
    assert item["item_code"] == "shop:I001"
    assert item["item_name"] == "テストコーヒー豆"
    assert item["price"] == 1500
    assert item["item_url"] == "https://item.rakuten.co.jp/shop/I001/"
    assert item["affiliate_url"] == "https://hb.afl.rakuten.co.jp/xxx"
    assert item["shop_name"] == "テストショップ"
    assert item["image_url"] == "https://image.rakuten.co.jp/shop/cabinet/I001.jpg"
    assert item["source_keyword"] == "コーヒー豆"
    assert item["source_type"] == "search"


@patch("src.rakuten_client.requests.get")
def test_ranking_returns_parsed_items(mock_get):
    mock_get.return_value = _mock_response(RANKING_RESPONSE)

    items = ranking("app123", "aff456", "100227")

    assert len(items) == 1
    item = items[0]
    assert item["item_code"] == "shop:R001"
    assert item["source_keyword"] == "100227"
    assert item["source_type"] == "ranking"


@patch("src.rakuten_client.time.sleep", return_value=None)
@patch("src.rakuten_client.requests.get")
def test_search_retries_then_raises_on_persistent_failure(mock_get, mock_sleep):
    mock_get.side_effect = requests.ConnectionError("boom")

    with pytest.raises(RakutenAPIError):
        search("app123", "aff456", "コーヒー豆")

    assert mock_get.call_count == 3


@patch("src.rakuten_client.time.sleep", return_value=None)
@patch("src.rakuten_client.requests.get")
def test_search_retries_then_succeeds(mock_get, mock_sleep):
    mock_get.side_effect = [
        requests.ConnectionError("boom"),
        _mock_response(SEARCH_RESPONSE),
    ]

    items = search("app123", "aff456", "コーヒー豆")

    assert len(items) == 1
    assert mock_get.call_count == 2
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `pytest tests/test_rakuten_client.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'src.rakuten_client'`)

- [ ] **Step 3: 実装を書く**

`src/rakuten_client.py`:
```python
import time

import requests

SEARCH_ENDPOINT = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
RANKING_ENDPOINT = "https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20220601"

MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1


class RakutenAPIError(Exception):
    pass


def _parse_item(raw_item: dict, source_keyword: str, source_type: str) -> dict:
    item = raw_item["Item"]
    image_urls = item.get("mediumImageUrls") or []
    image_url = image_urls[0]["imageUrl"] if image_urls else ""

    return {
        "item_code": item["itemCode"],
        "item_name": item["itemName"],
        "price": item["itemPrice"],
        "item_url": item["itemUrl"],
        "affiliate_url": item.get("affiliateUrl") or item["itemUrl"],
        "shop_name": item.get("shopName", ""),
        "image_url": image_url,
        "source_keyword": source_keyword,
        "source_type": source_type,
    }


def _request_with_retry(endpoint: str, params: dict) -> dict:
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))

    raise RakutenAPIError(f"Rakuten API request failed after {MAX_RETRIES} attempts: {last_error}")


def search(application_id: str, affiliate_id: str, keyword: str) -> list[dict]:
    params = {
        "applicationId": application_id,
        "affiliateId": affiliate_id,
        "keyword": keyword,
        "format": "json",
        "hits": 30,
    }
    data = _request_with_retry(SEARCH_ENDPOINT, params)
    raw_items = data.get("Items", [])
    return [_parse_item(raw, keyword, "search") for raw in raw_items]


def ranking(application_id: str, affiliate_id: str, genre_id: str) -> list[dict]:
    params = {
        "applicationId": application_id,
        "affiliateId": affiliate_id,
        "genreId": genre_id,
        "format": "json",
    }
    data = _request_with_retry(RANKING_ENDPOINT, params)
    raw_items = data.get("Items", [])
    return [_parse_item(raw, genre_id, "ranking") for raw in raw_items]
```

- [ ] **Step 4: テストが通ることを確認**

Run: `pytest tests/test_rakuten_client.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/rakuten_client.py tests/test_rakuten_client.py
git commit -m "feat: add Rakuten API client with retry logic"
```

---

### Task 5: main.py — オーケストレーションとログ出力

**Files:**
- Create: `src/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes:
  - `src.config.load_config() -> Config`
  - `src.rakuten_client.search(application_id, affiliate_id, keyword) -> list[dict]`
  - `src.rakuten_client.ranking(application_id, affiliate_id, genre_id) -> list[dict]`
  - `src.rakuten_client.RakutenAPIError`
  - `src.storage.init_db(db_path) -> sqlite3.Connection`
  - `src.storage.upsert_items(conn, items) -> dict`
- Produces: `def run(config, conn, search_fn=search, ranking_fn=ranking, sleep_fn=time.sleep) -> dict`
  (戻り値 `{"inserted": int, "updated": int, "errors": int}`)。`main()` はCLIエントリーポイントとして `run()` を実行し、ログをファイル・標準出力に出す。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_main.py`:
```python
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
        keywords=["コーヒー豆"],
        genre_ids=["100227"],
    )
    conn = init_db(str(tmp_path / "products.db"))

    def fake_search(application_id, affiliate_id, keyword):
        return [make_item("S001", keyword, "search")]

    def fake_ranking(application_id, affiliate_id, genre_id):
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
        keywords=["失敗キーワード", "成功キーワード"],
        genre_ids=[],
    )
    conn = init_db(str(tmp_path / "products.db"))

    def fake_search(application_id, affiliate_id, keyword):
        if keyword == "失敗キーワード":
            raise RakutenAPIError("boom")
        return [make_item("S002", keyword, "search")]

    def fake_ranking(application_id, affiliate_id, genre_id):
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
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `pytest tests/test_main.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'src.main'`)

- [ ] **Step 3: 実装を書く**

`src/main.py`:
```python
import logging
import time

from src.config import load_config
from src.rakuten_client import search, ranking, RakutenAPIError
from src.storage import init_db, upsert_items

DB_PATH = "products.db"
REQUEST_INTERVAL_SECONDS = 1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def run(config, conn, search_fn=search, ranking_fn=ranking, sleep_fn=time.sleep) -> dict:
    all_items = []
    errors = 0

    for keyword in config.keywords:
        try:
            items = search_fn(config.application_id, config.affiliate_id, keyword)
            all_items.extend(items)
            logger.info("search keyword=%s items=%d", keyword, len(items))
        except RakutenAPIError as e:
            errors += 1
            logger.error("search failed keyword=%s error=%s", keyword, e)
        sleep_fn(REQUEST_INTERVAL_SECONDS)

    for genre_id in config.genre_ids:
        try:
            items = ranking_fn(config.application_id, config.affiliate_id, genre_id)
            all_items.extend(items)
            logger.info("ranking genre_id=%s items=%d", genre_id, len(items))
        except RakutenAPIError as e:
            errors += 1
            logger.error("ranking failed genre_id=%s error=%s", genre_id, e)
        sleep_fn(REQUEST_INTERVAL_SECONDS)

    result = upsert_items(conn, all_items)
    result["errors"] = errors
    return result


def main():
    config = load_config()
    conn = init_db(DB_PATH)
    try:
        result = run(config, conn)
        logger.info(
            "done inserted=%d updated=%d errors=%d",
            result["inserted"], result["updated"], result["errors"],
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストが通ることを確認**

Run: `pytest tests/test_main.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add main orchestration with error isolation and logging"
```

---

### Task 6: 全体テストと手動結合確認

**Files:**
- Modify: なし(確認のみ)

**Interfaces:**
- Consumes: Task 1〜5 の全モジュール
- Produces: なし(検証タスク)

- [ ] **Step 1: 全自動テストを実行**

Run: `pytest -v`
Expected: 全テストPASS(Task 2〜5で作成した計12テスト)

- [ ] **Step 2: `.env` を実際の値で設定**

`.env` を作成し(`.env.example` をコピー)、ユーザーが取得済みの
Affiliate ID / Access Key(`RAKUTEN_APPLICATION_ID`)を設定する。

- [ ] **Step 3: `keywords.yaml` を少数のキーワードに絞って手動実行**

Run: `python src/main.py`
Expected: 標準出力とログに `done inserted=N updated=N errors=0` が出力される
(エラーが出る場合はAPIキー・キーワード内容を確認)

- [ ] **Step 4: SQLiteの中身を確認**

Run: `sqlite3 products.db "SELECT item_code, item_name, price FROM items LIMIT 5;"`
Expected: 取得した商品が表示される

- [ ] **Step 5: 再実行して重複が増えないことを確認**

Run: `python src/main.py` を再度実行し、
`sqlite3 products.db "SELECT COUNT(*) FROM items;"` の件数が
不当に増えていない(新規商品分のみ増加)ことを確認する
