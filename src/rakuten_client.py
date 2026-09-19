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
