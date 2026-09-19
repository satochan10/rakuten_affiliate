# 楽天アフィリエイト商品データ収集システム

楽天市場APIから商品情報を定期取得し、SQLite(`products.db`)に蓄積するツール。

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

## cronでの定期実行

`crontab -e` で以下のように登録する(例: 毎日9時に実行):

```
0 9 * * * cd /path/to/05_楽天アフィリエイト && /path/to/venv/bin/python -m src.main >> cron.log 2>&1
```

## テスト

```bash
pytest
```
