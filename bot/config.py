"""Загрузка конфигурации: `.env` (секреты) и YAML-конфиг (структурные настройки)."""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from bot.models.config import (
    AppConfig,
    OllamaConfig,
    Settings,
    StorageConfig,
    WeatherConfig,
    WeatherLocation,
)

CONFIG_PATH_ENV = "CONFIG_PATH"
DEFAULT_CONFIG_PATH = "config.yaml"


class ConfigError(RuntimeError):
    """Ошибка загрузки или валидации конфигурации."""


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"В .env отсутствует обязательная переменная {name}")
    return value


def load_settings() -> Settings:
    """Читает секреты из окружения (`.env` уже загружен через python-dotenv)."""
    load_dotenv()
    try:
        allowed_user_id = int(_require("ALLOWED_USER_ID"))
    except ValueError as exc:
        raise ConfigError("ALLOWED_USER_ID должен быть целым числом") from exc

    return Settings(
        bot_token=_require("BOT_TOKEN"),
        allowed_user_id=allowed_user_id,
        gismeteo_token=os.getenv("GISMETEO_TOKEN") or None,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        debug=os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes"},
    )


def load_app_config(path: str | os.PathLike[str] | None = None) -> AppConfig:
    """Читает структурные настройки из YAML. Отсутствующий файл → значения по умолчанию."""
    config_path = Path(path or os.getenv(CONFIG_PATH_ENV, DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        return AppConfig()

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Не удалось разобрать {config_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"Ожидался YAML-объект в {config_path}")

    return _build_app_config(raw)


def _build_app_config(raw: dict) -> AppConfig:
    ollama_raw = raw.get("ollama") or {}
    # base_url можно переопределить переменной окружения
    base_url = os.getenv("OLLAMA_BASE_URL") or ollama_raw.get("base_url", OllamaConfig.base_url)
    ollama = OllamaConfig(
        base_url=base_url,
        default_model=ollama_raw.get("default_model", OllamaConfig.default_model),
        request_timeout=ollama_raw.get("request_timeout", OllamaConfig.request_timeout),
        options=ollama_raw.get("options") or {},
        prompts=ollama_raw.get("prompts") or {},
    )

    weather_raw = raw.get("weather") or {}
    location_raw = weather_raw.get("location") or {}
    weather = WeatherConfig(
        provider=weather_raw.get("provider", WeatherConfig.provider),
        location=WeatherLocation(
            city=location_raw.get("city", WeatherLocation.city),
            latitude=location_raw.get("latitude", WeatherLocation.latitude),
            longitude=location_raw.get("longitude", WeatherLocation.longitude),
        ),
        silent=weather_raw.get("silent", WeatherConfig.silent),
    )

    storage_raw = raw.get("storage") or {}
    storage = StorageConfig(
        backend=storage_raw.get("backend", StorageConfig.backend),
        path=storage_raw.get("path", StorageConfig.path),
    )

    return AppConfig(ollama=ollama, weather=weather, storage=storage)
