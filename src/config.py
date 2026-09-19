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
