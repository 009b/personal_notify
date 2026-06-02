"""Каркас источников событий.

Источник событий опрашивает/принимает события и отдаёт их в виде `Event`.
Конкретные источники (их список и способ приёма — webhook/polling) определяются позже;
здесь — только общий интерфейс и нормализованная модель события.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class Event:
    """Нормализованное событие.

    `key` — стабильный идентификатор для дедупликации (см. Storage).
    `text` — готовый текст оповещения.
    """

    key: str
    text: str


class EventSource(ABC):
    """Источник событий."""

    @abstractmethod
    def poll(self) -> AsyncIterator[Event]:
        """Возвращает асинхронный поток новых событий."""
        raise NotImplementedError
