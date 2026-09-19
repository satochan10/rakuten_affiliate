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

    items = search("app123", "aff456", "accesskey789", "example.com", "コーヒー豆")

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

    items = ranking("app123", "aff456", "accesskey789", "example.com", "100227")

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
        search("app123", "aff456", "accesskey789", "example.com", "コーヒー豆")

    assert mock_get.call_count == 3


@patch("src.rakuten_client.time.sleep", return_value=None)
@patch("src.rakuten_client.requests.get")
def test_search_retries_then_succeeds(mock_get, mock_sleep):
    mock_get.side_effect = [
        requests.ConnectionError("boom"),
        _mock_response(SEARCH_RESPONSE),
    ]

    items = search("app123", "aff456", "accesskey789", "example.com", "コーヒー豆")

    assert len(items) == 1
    assert mock_get.call_count == 2


@patch("src.rakuten_client.requests.get")
def test_search_skips_item_with_missing_field_but_keeps_others(mock_get):
    response = {
        "Items": [
            {
                "Item": {
                    # itemName is missing - this item should be skipped
                    "itemCode": "shop:BAD001",
                    "itemPrice": 999,
                    "itemUrl": "https://item.rakuten.co.jp/shop/BAD001/",
                    "affiliateUrl": "https://hb.afl.rakuten.co.jp/bad",
                    "shopName": "壊れたショップ",
                }
            },
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
            },
        ]
    }
    mock_get.return_value = _mock_response(response)

    items = search("app123", "aff456", "accesskey789", "example.com", "コーヒー豆")

    assert len(items) == 1
    assert items[0]["item_code"] == "shop:I001"


@patch("src.rakuten_client.time.sleep", return_value=None)
@patch("src.rakuten_client.requests.get")
def test_request_error_message_redacts_credentials(mock_get, mock_sleep):
    mock_get.side_effect = requests.ConnectionError(
        "connection failed for https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
        "?applicationId=SECRET123&accessKey=KEYSECRET789&affiliateId=AFFSECRET456&keyword=coffee"
    )

    with pytest.raises(RakutenAPIError) as exc_info:
        search("app123", "aff456", "accesskey789", "example.com", "コーヒー豆")

    message = str(exc_info.value)
    assert "SECRET123" not in message
    assert "AFFSECRET456" not in message
    assert "KEYSECRET789" not in message
