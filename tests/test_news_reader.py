"""Тесты TelegramReader (мок Telethon-клиента, без сети)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bot.services.telegram_reader import TelegramReader, _normalize


def _msg(msg_id: int, text: str, date: datetime):
    return SimpleNamespace(id=msg_id, message=text, date=date)


class _FakeClient:
    """Минимальный async-клиент: iter_messages отдаёт заранее заданные сообщения."""

    def __init__(self, by_channel: dict[str, list]):
        self._by_channel = by_channel

    def iter_messages(self, channel, limit=None):
        messages = self._by_channel.get(channel, [])

        async def gen():
            for m in messages[:limit] if limit else messages:
                yield m

        return gen()


def test_normalize_variants():
    assert _normalize("https://t.me/durov") == "durov"
    assert _normalize("t.me/durov/") == "durov"
    assert _normalize("@durov") == "durov"
    assert _normalize("durov") == "durov"


async def test_fetch_filters_by_since_and_builds_url():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    msgs = [
        _msg(3, "свежий", now - timedelta(hours=1)),
        _msg(2, "вчерашний", now - timedelta(hours=10)),
        _msg(1, "старый", now - timedelta(hours=48)),  # за окном -> отсечь (и всё после)
    ]
    reader = TelegramReader(_FakeClient({"durov": msgs}))
    posts = await reader.fetch(["durov"], since=since, max_posts=100, max_post_chars=600)

    assert [p.msg_id for p in posts] == [3, 2]
    assert posts[0].url == "https://t.me/durov/3"


async def test_fetch_truncates_and_skips_empty():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    msgs = [
        _msg(5, "x" * 1000, now),
        _msg(4, "   ", now),  # пустой -> пропустить
        _msg(3, None, now),  # без текста -> пропустить
    ]
    reader = TelegramReader(_FakeClient({"durov": msgs}))
    posts = await reader.fetch(["durov"], since=since, max_posts=100, max_post_chars=50)

    assert len(posts) == 1
    assert len(posts[0].text) == 50


async def test_fetch_channel_error_does_not_break_others():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    class _BrokenClient(_FakeClient):
        def iter_messages(self, channel, limit=None):
            if channel == "broken":
                raise RuntimeError("boom")
            return super().iter_messages(channel, limit)

    client = _BrokenClient({"ok": [_msg(1, "пост", now)]})
    reader = TelegramReader(client)
    posts = await reader.fetch(["broken", "ok"], since=since, max_posts=100, max_post_chars=600)

    assert [p.channel for p in posts] == ["ok"]
