"""Обработка событий: дедупликация через Storage → отправка через Notifier."""
from __future__ import annotations

import logging

from bot.events.base import EventSource
from bot.services.notifier import Notifier
from bot.storage.base import Storage

logger = logging.getLogger(__name__)


class EventProcessor:
    """Принимает события из источника, пропускает уже виденные, отправляет новые."""

    def __init__(self, source: EventSource, storage: Storage, notifier: Notifier) -> None:
        self._source = source
        self._storage = storage
        self._notifier = notifier

    async def run_once(self) -> int:
        """Обрабатывает все доступные события источника. Возвращает число отправленных."""
        sent = 0
        async for event in self._source.poll():
            if self._storage.is_seen(event.key):
                continue
            await self._notifier.notify(event.text)
            self._storage.mark_seen(event.key)
            sent += 1
        return sent
