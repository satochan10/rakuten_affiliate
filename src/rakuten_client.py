import logging
import re
import time

import requests

logger = logging.getLogger(__name__)

_APPLICATION_ID_RE = re.compile(r"applicationId=[^&\s]+", re.IGNORECASE)
_AFFILIATE_ID_RE = re.compile(r"affiliateId=[^&\s]+", re.IGNORECASE)
_ACCESS_KEY_RE = re.compile(r"accessKey=[^&\s]+", re.IGNORECASE)

SEARCH_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
RANKING_ENDPOINT = "https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601"

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


def _redact_credentials(text: str) -> str:
    text = _APPLICATION_ID_RE.sub("applicationId=***", text)
    text = _AFFILIATE_ID_RE.sub("affiliateId=***", text)
    text = _ACCESS_KEY_RE.sub("accessKey=***", text)
    return text


def _referrer_headers(allowed_website: str) -> dict:
    origin = f"https://{allowed_website}"
    return {"Referer": f"{origin}/", "Origin": origin}


def _request_with_retry(endpoint: str, params: dict, headers: dict) -> dict:
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(endpoint, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))

    redacted_error = _redact_credentials(str(last_error))
    raise RakutenAPIError(f"Rakuten API request failed after {MAX_RETRIES} attempts: {redacted_error}")


def _parse_items(raw_items: list, source_keyword: str, source_type: str) -> list[dict]:
    items = []
    for raw in raw_items:
        try:
            items.append(_parse_item(raw, source_keyword, source_type))
        except (KeyError, TypeError) as e:
            logger.warning(
                "skipping item with missing/invalid field source=%s type=%s error=%s",
                source_keyword, source_type, e,
            )
    return items


def search(
    application_id: str,
    affiliate_id: str,
    access_key: str,
    allowed_website: str,
    keyword: str,
) -> list[dict]:
    params = {
        "applicationId": application_id,
        "accessKey": access_key,
        "affiliateId": affiliate_id,
        "keyword": keyword,
        "format": "json",
        "hits": 30,
    }
    data = _request_with_retry(SEARCH_ENDPOINT, params, _referrer_headers(allowed_website))
    raw_items = data.get("Items", [])
    return _parse_items(raw_items, keyword, "search")


def ranking(
    application_id: str,
    affiliate_id: str,
    access_key: str,
    allowed_website: str,
    genre_id: str,
) -> list[dict]:
    params = {
        "applicationId": application_id,
        "accessKey": access_key,
        "affiliateId": affiliate_id,
        "genreId": genre_id,
        "format": "json",
    }
    data = _request_with_retry(RANKING_ENDPOINT, params, _referrer_headers(allowed_website))
    raw_items = data.get("Items", [])
    return _parse_items(raw_items, genre_id, "ranking")
