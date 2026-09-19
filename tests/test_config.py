import os
import pytest
from src.config import load_config, ConfigError


def test_load_config_success(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "RAKUTEN_APPLICATION_ID=app123\n"
        "RAKUTEN_AFFILIATE_ID=aff456\n"
    )
    keywords_file = tmp_path / "keywords.yaml"
    keywords_file.write_text(
        "keywords:\n"
        "  - \"コーヒー豆\"\n"
        "genre_ids:\n"
        "  - \"100227\"\n"
    )

    config = load_config(env_path=str(env_file), keywords_path=str(keywords_file))

    assert config.application_id == "app123"
    assert config.affiliate_id == "aff456"
    assert config.keywords == ["コーヒー豆"]
    assert config.genre_ids == ["100227"]


def test_load_config_missing_application_id_raises(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("RAKUTEN_AFFILIATE_ID=aff456\n")
    keywords_file = tmp_path / "keywords.yaml"
    keywords_file.write_text("keywords: []\ngenre_ids: []\n")

    with pytest.raises(ConfigError, match="RAKUTEN_APPLICATION_ID"):
        load_config(env_path=str(env_file), keywords_path=str(keywords_file))
