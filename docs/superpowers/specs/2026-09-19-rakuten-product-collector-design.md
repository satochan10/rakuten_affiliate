# 楽天アフィリエイト 商品データ収集システム 設計書

- 日付: 2026-09-19
- ステータス: 承認待ち

## 目的

楽天ウェブサービスの Affiliate ID / Access Key / 楽天アフィリエイトID を用いて、
楽天市場の商品情報を定期的にサーチし、SQLiteデータベースへ蓄積する仕組みを構築する。

投稿先(WordPress、SNS等)は本フェーズのスコープ外とし、まずは商品データの収集・蓄積
に専念する。投稿機能は将来、本システムが蓄積したデータを参照する形で別途追加する。

## スコープ

**含む:**
- 楽天市場API(商品検索API `IchibaItem/Search`、ランキングAPI `IchibaItem/Ranking`)からの商品データ取得
- キーワード検索・ジャンル別ランキングの両方に対応
- 取得データのSQLiteへの保存(重複排除・UPSERT)
- アフィリエイトリンクの生成
- ローカルPC上での手動実行・cronによる定期実行
- エラー時のリトライ・スキップ処理とログ出力
- 単体テスト(APIクライアント・DB保存ロジック)

**含まない(将来フェーズ):**
- WordPress/SNS等への自動投稿機能そのもの
- 画像のダウンロード・加工
- Web UI・管理画面
- クラウド実行環境(GitHub Actions等)への移行

## 全体アーキテクチャ

3層構成のシンプルなPythonスクリプト群とする。

```
05_楽天アフィリエイト/
├── .env                  # APIキー類(gitignore対象)
├── .env.example          # サンプル
├── .gitignore
├── keywords.yaml         # 検索キーワード・ジャンルIDのリスト
├── products.db           # SQLite DB(gitignore対象、初回実行で自動生成)
├── requirements.txt
├── app.log               # 実行ログ(gitignore対象)
├── src/
│   ├── config.py         # .env / keywords.yaml の読み込み
│   ├── rakuten_client.py # 楽天API呼び出し(検索・ランキング、リトライ含む)
│   ├── storage.py        # SQLite UPSERT・重複排除ロジック
│   └── main.py           # エントリーポイント(全体のオーケストレーション)
└── tests/
    ├── test_rakuten_client.py
    └── test_storage.py
```

**設計判断の理由:** 単一の巨大スクリプトにすると将来の投稿機能追加時に書き直しが
発生しやすい。一方でSQLAlchemyのようなORMや非同期フレームワークは、単一テーブル・
少数キーワード(数件〜10件程度)・ローカルcron実行という規模に対して過剰。
標準ライブラリの `sqlite3` とシンプルなモジュール分割で十分と判断した。

## データ設計

`products.db` の `items` テーブル:

| カラム | 型 | 説明 |
|---|---|---|
| item_code | TEXT PRIMARY KEY | 楽天の商品コード(一意キー) |
| item_name | TEXT | 商品名 |
| price | INTEGER | 価格 |
| item_url | TEXT | 楽天商品ページURL |
| affiliate_url | TEXT | アフィリエイトリンク付きURL |
| shop_name | TEXT | 店舗名 |
| image_url | TEXT | 商品画像URL |
| source_keyword | TEXT | 取得元キーワード/ジャンルID |
| source_type | TEXT | "search" または "ranking" |
| first_seen_at | TEXT | 初回取得日時(ISO8601) |
| last_seen_at | TEXT | 最終取得日時(ISO8601、UPSERT時に更新) |
| posted_flag | INTEGER | 投稿済みフラグ(将来の投稿機能用、デフォルト0) |

## データフロー

1. `config.py` が `.env` からAPIキー(Application ID/Access Key, Affiliate ID)を、
   `keywords.yaml` から検索キーワードリストとジャンルIDリストを読み込む
2. `main.py` が各キーワードについて `rakuten_client.search()` を、各ジャンルIDに
   ついて `rakuten_client.ranking()` を呼び出す。楽天APIのレート制限に配慮し、
   リクエスト間に約1秒のウェイトを入れる
3. 取得した商品データを `storage.upsert_items()` に渡し、`item_code` をキーに
   INSERT OR UPDATE(新規は全カラム挿入、既存は price・last_seen_at 等のみ更新)
4. アフィリエイトリンクは楽天APIレスポンスの `affiliateUrl`(アフィリエイトID
   紐付け済みURLパラメータ経由で取得可能)をそのまま保存、または未取得の場合は
   Affiliate IDをURLパラメータとして付与して生成する
5. 実行結果(新規N件・更新N件・エラーN件)を標準出力と `app.log` に出力する

## エラー処理

- API呼び出し失敗(タイムアウト・レート制限エラー等)は指数バックオフで最大3回
  リトライし、それでも失敗した場合は該当キーワード/ジャンルをスキップして
  処理を継続する(1件のエラーで全体を止めない)
- `.env` にAPIキーが設定されていない等の致命的な設定エラーは起動時にバリデーション
  し、即座にエラーメッセージを出して終了する
- 個別商品データの必須フィールド欠損はその商品のみスキップしログに記録する

## テスト方針

- `rakuten_client.py`: 実APIレスポンスのサンプルJSONを使ったモックベースの単体テスト
  (正常系・エラー系・リトライ動作)
- `storage.py`: 一時SQLite DBを使ったUPSERT・重複排除ロジックの単体テスト
- 実APIとの結合確認は、少数キーワードでの手動実行により確認する(自動テストには含めない)

## 実行方法

- 手動実行: `python src/main.py`
- 定期実行: cron に `cd <project_dir> && python src/main.py` を登録(実行例をREADMEに記載)
- PC非起動時は実行されない前提(将来クラウド化する場合は別フェーズで検討)

## 将来の拡張ポイント(参考、本フェーズでは実装しない)

- `posted_flag` を使った投稿対象の絞り込み
- WordPress/SNS等への投稿モジュールの追加(`storage.py` が提供するデータを読むだけで
  完結するよう、今回のスキーマ設計時点で `posted_flag` を持たせている)
