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
