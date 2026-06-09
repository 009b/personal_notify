"""Тесты загрузки конфигурации."""
from __future__ import annotations

import pytest

import bot.config
from bot.config import ConfigError, load_app_config, load_settings
from bot.models.config import AppConfig


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    """Не давать тестам читать реальный .env проекта."""
    monkeypatch.setattr(bot.config, "load_dotenv", lambda *a, **k: False)


def test_load_app_config_missing_file_returns_defaults(tmp_path):
    cfg = load_app_config(tmp_path / "absent.yaml")
    assert isinstance(cfg, AppConfig)
    assert cfg.ollama.default_model == "qwen3:8b"
    assert cfg.weather.provider == "gismeteo"
    assert cfg.storage.backend == "sqlite"


def test_load_app_config_parses_values(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "ollama:\n"
        "  default_model: my-model\n"
        "  request_timeout: 42\n"
        "  options: {temperature: 0.1}\n"
        "  prompts: {notify: hi}\n"
        "weather:\n"
        "  provider: gismeteo\n"
        "  location: {city: Москва, latitude: 55.0, longitude: 37.0}\n"
        "storage:\n"
        "  backend: sqlite\n"
        "  path: /tmp/x.db\n",
        encoding="utf-8",
    )
    cfg = load_app_config(path)
    assert cfg.ollama.default_model == "my-model"
    assert cfg.ollama.request_timeout == 42
    assert cfg.ollama.options == {"temperature": 0.1}
    assert cfg.ollama.prompts == {"notify": "hi"}
    assert cfg.weather.location.city == "Москва"
    assert cfg.storage.path == "/tmp/x.db"


def test_load_news_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "news:\n"
        "  enabled: true\n"
        "  sources: [durov, meduzalive]\n"
        "  window_hours: 12\n"
        "  exclude_topics: [Трамп]\n"
        "  max_posts: 50\n"
        "  silent: false\n",
        encoding="utf-8",
    )
    cfg = load_app_config(path)
    assert cfg.news.enabled is True
    assert cfg.news.sources == ["durov", "meduzalive"]
    assert cfg.news.window_hours == 12
    assert cfg.news.exclude_topics == ["Трамп"]
    assert cfg.news.max_posts == 50
    assert cfg.news.silent is False


def test_news_config_defaults_when_absent(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("weather: {provider: gismeteo}\n", encoding="utf-8")
    cfg = load_app_config(path)
    assert cfg.news.enabled is False
    assert cfg.news.sources == []


def test_load_settings_reads_tg_credentials(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOWED_USER_ID", "1")
    monkeypatch.setenv("TG_API_ID", "12345")
    monkeypatch.setenv("TG_API_HASH", "abc")
    s = load_settings()
    assert s.tg_api_id == 12345
    assert s.tg_api_hash == "abc"


def test_ollama_base_url_env_override(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("ollama:\n  base_url: http://from-file:1\n", encoding="utf-8")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://from-env:2")
    cfg = load_app_config(path)
    assert cfg.ollama.base_url == "http://from-env:2"


def test_load_app_config_invalid_yaml_raises(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("ollama: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_app_config(path)


def test_load_settings_reads_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOWED_USER_ID", "777")
    monkeypatch.setenv("GISMETEO_TOKEN", "g")
    monkeypatch.setenv("DEBUG", "true")
    s = load_settings()
    assert s.bot_token == "token"
    assert s.allowed_user_id == 777
    assert s.gismeteo_token == "g"
    assert s.debug is True


def test_load_settings_missing_token_raises(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("ALLOWED_USER_ID", "1")
    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_non_integer_user_id_raises(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOWED_USER_ID", "not-int")
    with pytest.raises(ConfigError):
        load_settings()
