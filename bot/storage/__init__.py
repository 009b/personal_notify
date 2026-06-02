"""Хранилище: общий интерфейс и реализации."""
from bot.models.config import StorageConfig
from bot.storage.base import Storage
from bot.storage.sqlite import SqliteStorage

__all__ = ["Storage", "SqliteStorage", "build_storage"]


def build_storage(config: StorageConfig) -> Storage:
    """Фабрика хранилища по конфигу — точку хранения легко сменить."""
    if config.backend == "sqlite":
        return SqliteStorage(config.path)
    raise ValueError(f"Неизвестный бэкенд хранилища: {config.backend}")
