"""Тесты каркаса событий и обработчика."""
from __future__ import annotations

from collections.abc import AsyncIterator

from bot.events import Event, EventProcessor, EventSource
from bot.storage import SqliteStorage


class _FakeSource(EventSource):
    def __init__(self, events: list[Event]) -> None:
        self._events = events

    async def poll(self) -> AsyncIterator[Event]:
        for e in self._events:
            yield e


class _FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def notify(self, text: str) -> None:
        self.sent.append(text)


async def test_processor_sends_new_events():
    source = _FakeSource([Event("a", "событие A"), Event("b", "событие B")])
    storage = SqliteStorage(":memory:")
    notifier = _FakeNotifier()
    try:
        sent = await EventProcessor(source, storage, notifier).run_once()
        assert sent == 2
        assert notifier.sent == ["событие A", "событие B"]
    finally:
        storage.close()


async def test_processor_skips_seen_events():
    storage = SqliteStorage(":memory:")
    storage.mark_seen("a")
    notifier = _FakeNotifier()
    source = _FakeSource([Event("a", "A"), Event("b", "B")])
    try:
        sent = await EventProcessor(source, storage, notifier).run_once()
        assert sent == 1
        assert notifier.sent == ["B"]
    finally:
        storage.close()


async def test_processor_marks_after_send():
    storage = SqliteStorage(":memory:")
    notifier = _FakeNotifier()
    try:
        await EventProcessor(_FakeSource([Event("a", "A")]), storage, notifier).run_once()
        # повторный прогон того же события не отправляет заново
        sent = await EventProcessor(_FakeSource([Event("a", "A")]), storage, notifier).run_once()
        assert sent == 0
        assert notifier.sent == ["A"]
    finally:
        storage.close()
