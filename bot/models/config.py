"""Типы конфигурации приложения.

Секреты приходят из `.env` (см. `Settings`), структурные настройки — из YAML-конфига
(см. `AppConfig`). Хранилище доступно через общий интерфейс — точку хранения легко сменить.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Settings:
    """Секреты и параметры окружения из `.env`."""

    bot_token: str
    allowed_user_id: int
    gismeteo_token: str | None = None
    log_level: str = "INFO"
    debug: bool = False


@dataclass
class OllamaConfig:
    """Настройки обвязки вокруг локальной Ollama."""

    base_url: str = "http://127.0.0.1:11434"
    default_model: str = "qwen3:8b"
    request_timeout: int = 180
    options: dict[str, Any] = field(default_factory=dict)
    prompts: dict[str, str] = field(default_factory=dict)


@dataclass
class WeatherLocation:
    city: str = "Moscow"
    latitude: float = 55.7558
    longitude: float = 37.6173


@dataclass
class WeatherConfig:
    provider: str = "gismeteo"
    location: WeatherLocation = field(default_factory=WeatherLocation)


@dataclass
class StorageConfig:
    backend: str = "sqlite"
    path: str = "data/notify.db"


@dataclass
class AppConfig:
    """Структурные настройки из YAML-конфига."""

    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
