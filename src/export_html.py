import sqlite3
from html import escape

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>楽天商品一覧</title>
<style>
  body {{ font-family: sans-serif; margin: 2rem; color: #222; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; vertical-align: top; }}
  th {{ background: #f5f5f5; }}
  img {{ max-width: 80px; max-height: 80px; }}
  .price {{ text-align: right; white-space: nowrap; }}
</style>
</head>
<body>
<h1>楽天商品一覧（{count}件）</h1>
<table>
<thead>
<tr>
  <th>画像</th><th>商品名</th><th>価格</th><th>店舗</th><th>取得元</th><th>リンク</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</body>
</html>
"""

_ROW_TEMPLATE = """<tr>
  <td>{image}</td>
  <td>{item_name}</td>
  <td class="price">{price}</td>
  <td>{shop_name}</td>
  <td>{source_type}: {source_keyword}</td>
  <td><a href="{affiliate_url}" target="_blank" rel="noopener">購入ページ</a></td>
</tr>"""


def render_html(items: list[dict]) -> str:
    rows = []
    for item in items:
        image = (
            f'<img src="{escape(item["image_url"])}" alt="">'
            if item.get("image_url")
            else ""
        )
        rows.append(
            _ROW_TEMPLATE.format(
                image=image,
                item_name=escape(item["item_name"]),
                price=f'{item["price"]:,}円' if item.get("price") is not None else "",
                shop_name=escape(item.get("shop_name") or ""),
                source_type=escape(item.get("source_type") or ""),
                source_keyword=escape(item.get("source_keyword") or ""),
                affiliate_url=escape(item.get("affiliate_url") or item.get("item_url") or ""),
            )
        )
    return _PAGE_TEMPLATE.format(count=len(items), rows="\n".join(rows))


def export(db_path: str = "products.db", output_path: str = "products.html") -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM items ORDER BY source_type, source_keyword, price"
        ).fetchall()
    finally:
        conn.close()

    items = [dict(row) for row in rows]
    html = render_html(items)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    export()
