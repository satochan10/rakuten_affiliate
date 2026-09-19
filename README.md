# 楽天アフィリエイト商品データ収集システム

楽天市場APIから商品情報を定期取得し、SQLite(`products.db`)に蓄積するローカルPythonツール。

## できること

- **キーワード検索**: `keywords.yaml` に書いたキーワードで楽天市場の商品検索API(IchibaItem Search)を呼び出し、該当商品を取得する
- **ジャンル別ランキング取得**: `keywords.yaml` に書いたジャンルIDで人気ランキングAPI(IchibaItem Ranking)を呼び出し、そのジャンルの売れ筋商品を取得する
- **重複排除して蓄積**: 取得した商品は `item_code`(楽天の商品コード)をキーに SQLite へ UPSERT。既存商品は価格・最終取得日時などを更新し、新規商品のみ追加するので、毎日実行しても行が増殖しない
- **アフィリエイトリンク付きで保存**: 各商品のアフィリエイトURLもあわせて保存する
- **失敗に強い**: 1つのキーワード/ジャンルの取得に失敗しても(最大3回リトライ後)そのキーワードだけスキップして処理を継続する。1商品だけ必須フィールドが欠けている場合もその商品だけスキップする
- **ローカル/cronでの定期実行**: サーバーやクラウドを使わず、自分のPC上で手動実行、またはcronで定期実行できる

**含まないもの(今回のスコープ外)**: ブログ・SNS等への自動投稿。このツールは商品データの収集・蓄積までを担当し、投稿機能は投稿先が決まってから別途追加する想定。

## 構成

```
src/
├── config.py          # .env と keywords.yaml を読み込み、Configにまとめる
├── rakuten_client.py  # 楽天APIの呼び出し(検索・ランキング)とリトライ処理
├── storage.py          # SQLiteへのUPSERT(重複排除)処理
└── main.py             # 全体のオーケストレーション + ログ出力 + CLIエントリーポイント
```

各モジュールは他のモジュールの内部実装を知らずに使える設計になっている(例えば `storage.py` はAPIの存在を知らないし、`rakuten_client.py` はDBの存在を知らない)。

## データの流れ

1. `main.py` が `config.py` 経由で `.env`(APIキー類)と `keywords.yaml`(キーワード・ジャンルID一覧)を読み込む
2. キーワードごとに `rakuten_client.search()`、ジャンルIDごとに `rakuten_client.ranking()` を呼び出す(楽天APIのレート制限に配慮し、リクエスト間に約1秒あける)
3. 取得した商品データを `storage.upsert_items()` に渡し、`item_code` をキーに SQLite の `items` テーブルへ挿入/更新する
4. 実行結果(新規N件・更新N件・エラーN件)を標準出力と `app.log` に記録する

### `items` テーブルのカラム

| カラム | 内容 |
|---|---|
| `item_code` | 楽天の商品コード(一意キー) |
| `item_name` / `price` / `item_url` / `shop_name` / `image_url` | 商品情報 |
| `affiliate_url` | アフィリエイトリンク |
| `source_keyword` / `source_type` | どのキーワード/ジャンルIDから、検索(search)かランキング(ranking)かのどちらで取得したか |
| `first_seen_at` / `last_seen_at` | 初回取得日時・最終取得日時 |
| `posted_flag` | 投稿済みフラグ(今後、投稿機能を追加する際に使う予約カラム。現状は常に0) |

## セットアップ

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env を編集し、RAKUTEN_APPLICATION_ID / RAKUTEN_AFFILIATE_ID / RAKUTEN_ACCESS_KEY /
# RAKUTEN_ALLOWED_WEBSITE を設定する。
# いずれもRakuten Developers (https://webservice.rakuten.co.jp/) の
# 対象アプリの管理画面で確認できる。RAKUTEN_ALLOWED_WEBSITEは
# アプリ設定の「Allowed websites」に登録したドメイン(例: example.com)と
# 一致させること。一致しないとAPIから403 HTTP_REFERRER_NOT_ALLOWEDが返る。
```

`keywords.yaml` を編集し、検索したいキーワード・ジャンルIDを設定する。

## 実行

```bash
python -m src.main
```

実行するとログに `done inserted=N updated=N errors=N` が出力され、`products.db` に商品が蓄積される。

```bash
sqlite3 products.db "SELECT item_code, item_name, price FROM items LIMIT 10;"
```

## cronでの定期実行

`crontab -e` で以下のように登録する(例: 毎日9時に実行):

```
0 9 * * * cd /path/to/05_楽天アフィリエイト && /path/to/venv/bin/python -m src.main >> cron.log 2>&1
```

全キーワード/ジャンルの取得が失敗した場合はプロセスが非ゼロの終了コードで終わるため、cronのメール通知等で気づける。

## テスト

```bash
pytest
```
