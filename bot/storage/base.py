"""Общий интерфейс хранилища.

Хранит состояние событий (дедупликация: какие события уже обработаны).
Реализации скрывают конкретный бэкенд — точку хранения легко сменить.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    def is_seen(self, key: str) -> bool:
        """Возвращает True, если событие с данным ключом уже было обработано."""
        raise NotImplementedError

    @abstractmethod
    def mark_seen(self, key: str) -> None:
        """Отмечает событие как обработанное."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Освобождает ресурсы хранилища."""
        raise NotImplementedError
