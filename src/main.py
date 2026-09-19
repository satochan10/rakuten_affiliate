import logging
import sys
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

    if result["errors"] > 0 and result["inserted"] == 0 and result["updated"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
